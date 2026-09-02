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
    application stays applied and the token issuer stays running, so that API
    tests can be run against them afterwards. Any automated run of this test
    must therefore be configured not to release or reclaim the target system on
    success. A run that tears the system down when all tests pass destroys the
    very environment this test exists to produce, and the certificates left on
    the runner become useless.

Markers:
    - @mark.p2: priority tier
"""

import os

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than, validate_str_contains
from keywords.cloud_platform.applications.o_ran_o2_keywords import OranO2Keywords
from keywords.cloud_platform.security.keycloak.keycloak_cli_keywords import KeycloakCliKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.docker.container.docker_container_keywords import DockerContainerKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.rollout.kubectl_rollout_restart_keywords import KubectlRolloutRestartKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "oran-o2"
APP_NAMESPACE = "oran-o2"
APP_CHART_GLOB = "/usr/local/share/applications/helm/*oran*"
O2_POD_PREFIX = "o2api"

# The OAuth2 provider runs as a container in the host network namespace. Port
# 28080 is used because the platform already serves on 8080, and published-port
# mapping does not take effect on all hosts.
OAUTH2_CONTAINER_NAME = "o2ims-oauth2-provider"
OAUTH2_IMAGE = "quay.io/keycloak/keycloak:26.7.0"
OAUTH2_PORT = 28080
OAUTH2_REALM = "master"
OAUTH2_CLIENT_ID = "o2ims-test-client"
# Set to a fixed value so the client is reproducible across runs. Consumers are
# still expected to read the secret from the provider at their own setup rather
# than storing it, since the provider remains the authority on its current value.
OAUTH2_CLIENT_SECRET = "o2ims-test-secret"
OAUTH2_ADMIN_USER = "admin"
OAUTH2_ADMIN_PASSWORD = "admin"
# Long enough that a full suite run does not expire the token mid-run.
OAUTH2_TOKEN_LIFESPAN_SECONDS = 3600

SMO_SERVICE_ACCOUNT = "smo1"
SMO_SECRET = "smo1-secret"

# Client certificates are written to a stable location so that API tests run
# later, in a separate pytest session, can find them. Deriving this from the
# logging configuration would place them in a per-run directory.
LOCAL_CERTIFICATE_DIRECTORY = os.path.expanduser("~/o2ims_certificates")


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
        - Start and configure the OAuth2 provider
        - Upload the oran-o2 application

    Test Steps:
        1. Create the SMO service account and secret
        2. Generate the CA, server and client certificates
        3. Create the application configuration with the OAuth2 public key
        4. Apply the helm override with the client-validation CA
        5. Restart the deployment so the new configuration takes effect
        6. Verify the O2 API pod is running with all containers ready
        7. Verify the deployed configuration carries resolved credentials
        8. Download the client certificates to the test runner
        9. Verify an OAuth2 token can be issued

    Teardown:
        - None. The deployment and its token issuer are left in place for
          subsequent API tests.
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_info(f"Connected to: {ssh_connection.get_name()}")

    oran_o2_keywords = OranO2Keywords(ssh_connection)
    container_keywords = DockerContainerKeywords(ssh_connection)
    oauth2_url = f"http://localhost:{OAUTH2_PORT}"
    keycloak_keywords = KeycloakCliKeywords(ssh_connection, OAUTH2_CONTAINER_NAME, oauth2_url)

    # A pre-existing provider is removed rather than reused: its realm signing
    # key would not match the key this run deploys into the application.
    get_logger().log_setup_step("Start the OAuth2 provider container")
    container_keywords.cleanup_container(OAUTH2_CONTAINER_NAME)
    container_keywords.run_container(
        image=OAUTH2_IMAGE,
        container_name=OAUTH2_CONTAINER_NAME,
        use_host_network=True,
        environment={
            "KC_HTTP_PORT": str(OAUTH2_PORT),
            "KC_BOOTSTRAP_ADMIN_USERNAME": OAUTH2_ADMIN_USER,
            "KC_BOOTSTRAP_ADMIN_PASSWORD": OAUTH2_ADMIN_PASSWORD,
        },
        command="start-dev",
    )
    container_keywords.wait_for_container_running(OAUTH2_CONTAINER_NAME)
    keycloak_keywords.wait_for_keycloak_ready(realm=OAUTH2_REALM)

    get_logger().log_setup_step("Configure the OAuth2 realm and client")
    keycloak_keywords.login_as_admin(OAUTH2_ADMIN_USER, OAUTH2_ADMIN_PASSWORD, realm=OAUTH2_REALM)
    keycloak_keywords.update_realm(realm=OAUTH2_REALM, ssl_required="NONE", access_token_lifespan=OAUTH2_TOKEN_LIFESPAN_SECONDS)
    client_uuid = keycloak_keywords.create_confidential_client(OAUTH2_CLIENT_ID, realm=OAUTH2_REALM, client_secret=OAUTH2_CLIENT_SECRET)
    # Read the secret back from the provider rather than reusing the value just
    # set. This is the same path a consumer must use, and a successful token
    # request later in the run proves the value is the one the provider accepts.
    client_secret = keycloak_keywords.get_client_secret(client_uuid, realm=OAUTH2_REALM)
    # Only readable once the realm is serving, so this must follow wait_for_keycloak_ready.
    realm_public_key = keycloak_keywords.get_realm_public_key(realm=OAUTH2_REALM)

    get_logger().log_setup_step("Upload the oran-o2 application")
    upload_keywords = SystemApplicationUploadKeywords(ssh_connection)
    if not upload_keywords.is_already_uploaded(APP_NAME):
        tar_file_path = LsKeywords(ssh_connection).get_first_matching_file(APP_CHART_GLOB)
        get_logger().log_info(f"Uploading from: {tar_file_path}")
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(APP_NAME)
        upload_input.set_tar_file_path(tar_file_path)
        upload_input.set_force(True)
        upload_keywords.system_application_upload(upload_input)
    else:
        get_logger().log_info(f"Application '{APP_NAME}' already uploaded")

    get_logger().log_test_case_step("Create the SMO service account and secret")
    oran_o2_keywords.create_smo_service_account(SMO_SERVICE_ACCOUNT)
    smo_token = oran_o2_keywords.create_smo_secret(SMO_SECRET, SMO_SERVICE_ACCOUNT)
    validate_greater_than(len(smo_token), 0, "SMO service account token populated")

    get_logger().log_test_case_step("Generate the CA, server and client certificates")
    oran_o2_keywords.create_certificates()

    # Every value must be fully resolved here: the configuration is mounted into
    # the pod verbatim and nothing expands shell-style placeholders.
    get_logger().log_test_case_step("Create the application configuration with the OAuth2 public key")
    oran_o2_keywords.create_app_config_file(
        smo_register_url="http://127.0.0.1",
        smo_token_data=smo_token,
        oauth2_public_key=realm_public_key,
    )

    # tls=True supplies the client-validation CA. Without it the API server
    # rejects every client during the TLS handshake.
    get_logger().log_test_case_step("Apply the helm override with the client-validation CA")
    oran_o2_keywords.apply_helm_override(tls=True)

    get_logger().log_test_case_step("Restart the deployment so the new configuration takes effect")
    KubectlRolloutRestartKeywords(ssh_connection).rollout_restart_deployment(APP_NAMESPACE)

    get_logger().log_test_case_step("Verify the O2 API pod is running with all containers ready")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status=["Running", "Completed"], namespace=APP_NAMESPACE)
    o2_pods = kubectl_pods.get_pods(namespace=APP_NAMESPACE).get_pods_start_with(O2_POD_PREFIX)
    validate_greater_than(len(o2_pods), 0, f"O2 API pod present in namespace '{APP_NAMESPACE}'")
    for pod in o2_pods:
        validate_equals(pod.get_status(), "Running", f"Pod {pod.get_name()} is Running")
        validate_equals(pod.is_ready(), True, f"Pod {pod.get_name()} has all containers ready")
        get_logger().log_info(f"O2 API pod: {pod.get_name()}, ready: {pod.get_ready()}")

    get_logger().log_test_case_step("Verify the deployed configuration carries resolved credentials")
    deployed_config = oran_o2_keywords.get_deployed_app_config(o2_pods[0].get_name(), namespace=APP_NAMESPACE)
    validate_equals("${" in deployed_config, False, "Deployed configuration contains no unresolved placeholders")
    validate_str_contains(deployed_config, "[OAUTH2]", "Deployed configuration contains the OAUTH2 section")

    get_logger().log_test_case_step("Download the client certificates to the test runner")
    oran_o2_keywords.download_client_certificates(LOCAL_CERTIFICATE_DIRECTORY)
    for file_name in ("client-cert.pem", "client-key.pem", "my-root-ca-cert.pem"):
        validate_equals(os.path.isfile(f"{LOCAL_CERTIFICATE_DIRECTORY}/{file_name}"), True, f"'{file_name}' present on the test runner")

    get_logger().log_test_case_step("Verify an OAuth2 token can be issued")
    token = keycloak_keywords.get_token(OAUTH2_CLIENT_ID, client_secret, realm=OAUTH2_REALM)
    validate_greater_than(len(token), 0, "OAuth2 access token issued")

    get_logger().log_info(f"Bring-up complete. Client certificates in {LOCAL_CERTIFICATE_DIRECTORY}, OAuth2 client '{OAUTH2_CLIENT_ID}' on {oauth2_url}")
