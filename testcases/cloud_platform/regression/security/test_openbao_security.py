"""OpenBao application security tests.

Covers the OpenBao application (container) security scenarios that validate the
server over its Kubernetes service endpoint:
    - server TLS: trusted-CA client succeeds, no-CA client is rejected, the
      server certificate verifies against the OpenBao CA
    - RBAC: a read-only policy/role allows reads but denies writes
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.openbao.openbao_keywords import OpenBaoKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "openbao"
CHART_PATH = "/usr/local/share/applications/helm/openbao-[0-9]*"
NAMESPACE = "openbao"
TEST_NAMESPACE = "pvtest"
POLICY_NAME = "basic-secret-policy"
ROLE_NAME = "basic-secret-role"
SERVICE_ACCOUNT = "basic-secret"
POLICY_HCL = 'path "secret/data/basic-secret/*" { capabilities = ["read"] }'


def setup_openbao_environment(ssh_connection: object) -> None:
    """Upload and apply OpenBao, wait for unseal, and configure KV v2 + k8s auth.

    Args:
        ssh_connection (object): SSH connection to active controller.
    """
    app_list = SystemApplicationListKeywords(ssh_connection)
    validate_equals(app_list.is_app_present("platform-integ-apps"), True, "platform-integ-apps must be present for OpenBao PVC")

    if not app_list.is_app_present(APP_NAME):
        get_logger().log_info(f"Uploading {APP_NAME} application")
        actual_chart = LsKeywords(ssh_connection).get_first_matching_file(CHART_PATH)
        upload_input = SystemApplicationUploadInput()
        upload_input.set_tar_file_path(actual_chart)
        upload_input.set_app_name(APP_NAME)
        SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)

    app_apply = SystemApplicationApplyKeywords(ssh_connection)
    if not app_apply.is_already_applied(APP_NAME):
        get_logger().log_info(f"Applying {APP_NAME} application")
        app_apply.system_application_apply(APP_NAME)

    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status("Running", namespace=NAMESPACE, timeout=600)

    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    unsealed = openbao.wait_for_unseal(timeout=300)
    validate_equals(unsealed, True, "OpenBao should be unsealed after apply")

    openbao.extract_ca_cert()

    root_token = openbao.get_root_token()
    openbao.enable_kv_v2(root_token)
    openbao.enable_kubernetes_auth(root_token)
    openbao.write_policy(POLICY_NAME, POLICY_HCL, root_token)
    openbao.write_kubernetes_role(ROLE_NAME, SERVICE_ACCOUNT, TEST_NAMESPACE, POLICY_NAME, root_token)


def cleanup_openbao_environment(ssh_connection: object) -> None:
    """Clean up OpenBao security test resources and remove the application.

    Args:
        ssh_connection (object): SSH connection to active controller.
    """
    get_logger().log_teardown_step("Cleaning up OpenBao security test resources")

    KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(TEST_NAMESPACE)

    app_list = SystemApplicationListKeywords(ssh_connection)
    if app_list.is_app_present(APP_NAME):
        app_apply = SystemApplicationApplyKeywords(ssh_connection)
        if app_apply.is_already_applied(APP_NAME):
            remove_input = SystemApplicationRemoveInput()
            remove_input.set_app_name(APP_NAME)
            SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(remove_input)

        delete_input = SystemApplicationDeleteInput()
        delete_input.set_app_name(APP_NAME)
        delete_input.set_force_deletion(True)
        SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(delete_input)


@mark.p1
def test_openbao_server_tls_verify(request: FixtureRequest):
    """Test that the OpenBao application server enforces TLS with a CA-issued cert.

    A client trusting the OpenBao CA can reach the server health endpoint over
    TLS, a client with no trusted CA is rejected, and the server certificate
    verifies against the OpenBao CA.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - query the health endpoint trusting the CA and confirm it is reachable
        - query the health endpoint with no trusted CA and confirm rejection
        - verify the server certificate against the OpenBao CA
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Querying the health endpoint over TLS while trusting the OpenBao CA")
    validate_equals(openbao.rest_health_trusts_ca(), True, "Health endpoint must be reachable over TLS trusting the OpenBao CA")

    get_logger().log_test_case_step("Querying the health endpoint with no trusted CA and confirming rejection")
    validate_equals(openbao.rest_health_no_ca_rejected(), True, "Health request without a trusted CA must be rejected by TLS verification")

    get_logger().log_test_case_step("Verifying the server certificate validates against the OpenBao CA")
    validate_equals(openbao.app_server_cert_verifies(), True, "Server certificate must verify against the OpenBao CA")


@mark.p1
def test_openbao_rbac_read_only_policy(request: FixtureRequest):
    """Test that the read-only RBAC policy allows reads but denies writes.

    A kubernetes-auth role bound to a read-only policy on the bound secret path
    can read the secret but is denied writes to the bound path and to an
    out-of-policy path.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - seed the bound secret and the RBAC test service account
        - log in via the kubernetes role to obtain a scoped token
        - read the bound path and confirm it is allowed
        - write the bound path and confirm it is denied
        - write an out-of-policy path and confirm it is denied
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Seeding the bound secret and the RBAC test service account")
    root_token = openbao.get_root_token()
    openbao.create_secret_rest("basic-secret/helloworld", {"username": security_config.get_openbao_test_secret_username(), "password": security_config.get_openbao_test_secret_password()}, root_token)
    openbao.ensure_rbac_test_subject(TEST_NAMESPACE, SERVICE_ACCOUNT)

    get_logger().log_test_case_step("Logging in via the kubernetes role to obtain a scoped token")
    role_token = openbao.k8s_role_login_token(ROLE_NAME, SERVICE_ACCOUNT, TEST_NAMESPACE)
    validate_not_equals(role_token, "", "Kubernetes role login must return a scoped client token")

    get_logger().log_test_case_step("Reading the bound path and confirming the read is allowed")
    validate_equals(openbao.rest_status_code("basic-secret/helloworld", role_token), "200", "Read-only role must be allowed to read the bound path")

    get_logger().log_test_case_step("Writing the bound path and confirming the write is denied")
    validate_equals(openbao.rest_write_status_code("basic-secret/helloworld", role_token), "403", "Read-only role must be denied writes to the bound path")

    get_logger().log_test_case_step("Writing an out-of-policy path and confirming the write is denied")
    validate_equals(openbao.rest_write_status_code("out-of-policy/secret", role_token), "403", "Read-only role must be denied writes to an out-of-policy path")
