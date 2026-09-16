"""O-RAN O2 bring-up for API testing.

Deploys the oran-o2 application configured so its O2 IMS API can actually be
called: mutual TLS with a usable client certificate, and OAuth2 Bearer
authentication backed by a containerized token issuer.

A default oran-o2 deployment cannot serve API requests. The server runs with
mutual TLS required and rejects every client unless it is given the CA that
signed the client certificate, and once TLS succeeds every endpoint returns 401
unless the application is configured with a token issuer's public key.

Prerequisites:
    - Target system accessible (--lab_config_file)
    - oran-o2 application package present on the load under
      /usr/local/share/applications/helm/
    - Container runtime available on the target host
    - Target host able to pull the OAuth2 provider image from an external registry

Run with:
    pytest starlingx/testcases/cloud_platform/apps_setup/o_ran_o2/test_o_ran_o2_bring_up.py \
        --lab_config_file=<LAB_CONFIG> -v

Outputs:
    The client certificate, client key and CA certificate are written to
    ~/o2ims_certificates on the test runner, readable only by the user that ran
    the test. API tests running in a later session read them from there.

Retention:
    This test deliberately leaves a configured environment behind: the
    application stays applied and the token issuer stays running, so API tests
    can be run against them afterwards without standing the environment up
    again. Any automated run of this test should therefore be configured not to
    release or reclaim the target system on success, since reclaiming it discards
    the deployment and leaves the certificates on the runner useless.

    The API tests check the environment is standing before they run, via
    O2EnvironmentKeywords.verify_environment_ready, which reports the missing
    part rather than letting the gap surface as a connection error.

Markers:
    - @mark.p2: priority tier
"""

import os

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than, validate_str_contains
from keywords.cloud_platform.applications.o_ran_o2_keywords import APP_NAMESPACE, O2_POD_PREFIX, SMO_SECRET, OranO2Keywords
from keywords.cloud_platform.rest.oran_o2.o2_token_keywords import O2TokenKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


@mark.p2
def test_o_ran_o2_bring_up():
    """Deploy oran-o2 with mutual TLS and OAuth2 so its API can be called.

    Brings the application to a state where an external client holding the
    generated client certificate and an OAuth2 Bearer token receives data from
    the O2 IMS API. Leaves the application applied and the OAuth2 provider
    running so API tests can be run against it. Does not itself call the O2 IMS
    API.

    The OAuth2 provider is deliberately not torn down. The O2 API validates
    Bearer tokens on every request, so removing the token issuer would leave a
    deployment that no client can authenticate against. Removing it would also
    invalidate the deployed public key, since a fresh provider generates a new
    realm signing key.

    Preconditions:
        - oran-o2 package present on the load
        - Container runtime available on the target host
        - External registry reachable for the OAuth2 provider image

    Setup:
        - Establish SSH connection to the active controller
        - Deploy the O2 IMS environment: OAuth2 provider, application upload, SMO
          service account and secret, certificates, application configuration,
          helm override and deployment restart

    Test Steps:
        1. Verify the SMO service account token is populated
        2. Verify the O2 API pod is running with all containers ready
        3. Verify the deployed configuration carries resolved credentials
        4. Verify the client certificates reached the test runner
        5. Verify an OAuth2 token can be issued

    Teardown:
        - None. The deployment and its token issuer are left in place for
          subsequent API tests.
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_info(f"Connected to: {ssh_connection.get_name()}")

    # Client certificates are written to a stable location so that API tests run
    # later, in a separate pytest session, can find them. ConfigurationManager is
    # read here rather than at import time, when it is not yet initialized.
    local_certificate_directory = os.path.expanduser(ConfigurationManager.get_o2ims_config().get_cert_dir())

    oran_o2_keywords = OranO2Keywords(ssh_connection)

    get_logger().log_setup_step("Deploy the O2 IMS environment")
    oran_o2_keywords.deploy_o2_environment(local_certificate_directory)

    get_logger().log_test_case_step("Verify the SMO service account token is populated")
    validate_greater_than(len(oran_o2_keywords.get_smo_token(SMO_SECRET)), 0, "SMO service account token populated")

    get_logger().log_test_case_step("Verify the O2 API pod is running with all containers ready")
    o2_pods = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=APP_NAMESPACE).get_pods_start_with(O2_POD_PREFIX)
    validate_greater_than(len(o2_pods), 0, f"O2 API pod present in namespace '{APP_NAMESPACE}'")
    for pod in o2_pods:
        validate_equals(pod.get_status(), "Running", f"Pod {pod.get_name()} is Running")
        validate_equals(pod.is_ready(), True, f"Pod {pod.get_name()} has all containers ready")
        get_logger().log_info(f"O2 API pod: {pod.get_name()}, ready: {pod.get_ready()}")

    get_logger().log_test_case_step("Verify the deployed configuration carries resolved credentials")
    deployed_config = oran_o2_keywords.get_deployed_app_config(o2_pods[0].get_name(), namespace=APP_NAMESPACE)
    validate_equals("${" in deployed_config, False, "Deployed configuration contains no unresolved placeholders")
    validate_str_contains(deployed_config, "[OAUTH2]", "Deployed configuration contains the OAUTH2 section")

    get_logger().log_test_case_step("Verify the client certificates reached the test runner")
    for file_name in ("client-cert.pem", "client-key.pem", "my-root-ca-cert.pem"):
        validate_equals(os.path.isfile(f"{local_certificate_directory}/{file_name}"), True, f"'{file_name}' present on the test runner")

    get_logger().log_test_case_step("Verify an OAuth2 token can be issued")
    validate_greater_than(len(O2TokenKeywords(ssh_connection).get_token()), 0, "OAuth2 access token issued")

    get_logger().log_info(f"Bring-up complete. Client certificates in {local_certificate_directory}")
