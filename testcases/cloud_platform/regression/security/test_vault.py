"""Vault application regression tests."""

import time

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.vault.vault_keywords import VaultKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "vault"
CHART_PATH = "/usr/local/share/applications/helm/vault-[0-9]*"
NAMESPACE = "vault"
TEST_NAMESPACE = "pvtest"
SECRET_PATH = "basic-secret/helloworld"


def setup_vault_environment(ssh_connection: object) -> None:
    """Upload, apply vault, wait for unseal, and run setup script.

    Args:
        ssh_connection (object): SSH connection to active controller.
    """
    app_list = SystemApplicationListKeywords(ssh_connection)
    validate_equals(
        app_list.is_app_present("platform-integ-apps"),
        True,
        "platform-integ-apps must be present for vault PVC",
    )

    if not app_list.is_app_present(APP_NAME):
        get_logger().log_info(f"Uploading {APP_NAME} application")
        ls_keywords = LsKeywords(ssh_connection)
        actual_chart = ls_keywords.get_first_matching_file(CHART_PATH)
        upload_input = SystemApplicationUploadInput()
        upload_input.set_tar_file_path(actual_chart)
        upload_input.set_app_name(APP_NAME)
        SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)

    app_apply = SystemApplicationApplyKeywords(ssh_connection)
    if not app_apply.is_already_applied(APP_NAME):
        get_logger().log_info(f"Applying {APP_NAME} application")
        app_apply.system_application_apply(APP_NAME)

    get_logger().log_info("Waiting for vault pods to be running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status("Running", namespace=NAMESPACE, timeout=600)

    get_logger().log_info("Waiting for vault to be unsealed (all pods Ready)")
    security_config = ConfigurationManager.get_security_config()
    vault_keywords = VaultKeywords(ssh_connection, security_config.get_ssh_user_home())
    unsealed = vault_keywords.wait_for_unseal(timeout=300)
    validate_equals(unsealed, True, "Vault should be unsealed after apply")

    get_logger().log_info("Running vault setup script")
    local_script = get_stx_resource_path("resources/cloud_platform/security/vault/setup_vault.sh")
    vault_keywords.run_setup_script(local_script)


def cleanup_vault_environment(ssh_connection: object) -> None:
    """Clean up vault test resources.

    Args:
        ssh_connection (object): SSH connection to active controller.
    """
    get_logger().log_info("Cleaning up vault test resources")

    KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(TEST_NAMESPACE)

    vault_keywords = VaultKeywords(ssh_connection)
    vault_keywords.delete_clusterrolebinding("pvtest-user-clusterrolebinding")

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
def test_vault_secret_injection(request):
    """Test vault secret injection into a pod via vault agent injector.

    Deploys vault, configures kubernetes auth and KV v2 secret engine,
    creates a secret, deploys a test application with vault agent-inject
    annotations, and verifies the secret is injected into the pod.

    Test Steps:
        - Upload and apply vault application
        - Wait for vault to be unsealed
        - Run setup script (configure K8s auth, policy, role, KV v2 engine)
        - Get root token from kubernetes secret
        - Create a test secret in vault
        - Verify the secret exists in vault via REST API
        - Verify vault-server-tls certificate is Ready
        - Copy vault-ca and registry secrets to test namespace
        - Deploy helloworld test app with vault agent-inject annotations
        - Wait for test pod to be running
        - Verify the secret is injected into the pod at /vault/secrets/helloworld
    """
    get_logger().log_info("Starting vault secret injection test")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    def cleanup():
        cleanup_vault_environment(ssh_connection)

    request.addfinalizer(cleanup)

    setup_vault_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    vault_keywords = VaultKeywords(ssh_connection, security_config.get_ssh_user_home())

    get_logger().log_info("Retrieving vault root token")
    root_token = vault_keywords.get_root_token()
    get_logger().log_info(f"Root token retrieved (length: {len(root_token)})")

    secret_data = {
        "password": security_config.get_vault_test_secret_password(),
        "username": security_config.get_vault_test_secret_username(),
    }

    get_logger().log_info(f"Creating secret at path: {SECRET_PATH}")
    vault_keywords.create_secret(SECRET_PATH, secret_data, root_token)

    get_logger().log_info(f"Verifying secret at path: {SECRET_PATH}")
    response = vault_keywords.read_secret(SECRET_PATH, root_token)
    validate_equals("errors" not in response, True, "Vault secret should not have errors")
    validate_equals(response["data"]["data"], secret_data, "Vault secret data should match")

    get_logger().log_info("Verifying vault-server-tls certificate is Ready")
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)
    cert_keywords.wait_for_certs_status("vault-server-tls", True, namespace=NAMESPACE, timeout=120)

    get_logger().log_info("Deploying helloworld test app")
    file_keywords = FileKeywords(ssh_connection)
    local_app = get_stx_resource_path("resources/cloud_platform/security/vault/helloworld.yaml")
    remote_app = "/home/sysadmin/helloworld.yaml"
    file_keywords.upload_file(local_app, remote_app, overwrite=True)

    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_app)

    get_logger().log_info("Waiting for helloworld test pod to be running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status("Running", namespace=TEST_NAMESPACE, timeout=300)

    time.sleep(15)

    get_logger().log_info("Verifying secret injection into test pod")
    pod_name = vault_keywords.get_first_pod_name(TEST_NAMESPACE)
    injected_secret = vault_keywords.get_injected_secret(pod_name, TEST_NAMESPACE)

    validate_equals(
        injected_secret["username"],
        security_config.get_vault_test_secret_username(),
        "Injected username should match",
    )
    validate_equals(
        injected_secret["password"],
        security_config.get_vault_test_secret_password(),
        "Injected password should match",
    )

    get_logger().log_info("Vault secret injection test complete")


@mark.p1
def test_vault_app_lifecycle(request):
    """Test vault application lifecycle: upload, apply, remove, delete.

    Verifies the complete application lifecycle works correctly and that
    vault pods reach running state after apply.

    Test Steps:
        - Upload vault application
        - Verify app is present
        - Apply vault application
        - Verify app is applied
        - Verify all vault pods are running
        - Verify vault-server-tls certificate is Ready
        - Remove vault application
        - Delete vault application
        - Verify app is no longer present
    """
    get_logger().log_info("Starting vault app lifecycle test")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    def cleanup():
        cleanup_vault_environment(ssh_connection)

    request.addfinalizer(cleanup)

    app_list = SystemApplicationListKeywords(ssh_connection)

    get_logger().log_info("Uploading vault application")
    ls_keywords = LsKeywords(ssh_connection)
    actual_chart = ls_keywords.get_first_matching_file(CHART_PATH)
    upload_input = SystemApplicationUploadInput()
    upload_input.set_tar_file_path(actual_chart)
    upload_input.set_app_name(APP_NAME)
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)
    validate_equals(app_list.is_app_present(APP_NAME), True, "Vault should be present after upload")

    get_logger().log_info("Applying vault application")
    app_apply = SystemApplicationApplyKeywords(ssh_connection)
    app_apply.system_application_apply(APP_NAME)
    validate_equals(app_apply.is_already_applied(APP_NAME), True, "Vault should be applied")

    get_logger().log_info("Verifying vault pods are running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status("Running", namespace=NAMESPACE, timeout=600)
    pods_output = kubectl_pods.get_pods(NAMESPACE)
    running_pods = pods_output.get_pods_with_status("Running")
    validate_equals(len(running_pods) > 0, True, "At least one vault pod should be running")

    get_logger().log_info("Verifying vault-server-tls certificate")
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)
    cert_keywords.wait_for_certs_status("vault-server-tls", True, namespace=NAMESPACE, timeout=120)

    get_logger().log_info("Removing vault application")
    remove_input = SystemApplicationRemoveInput()
    remove_input.set_app_name(APP_NAME)
    SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(remove_input)

    get_logger().log_info("Deleting vault application")
    delete_input = SystemApplicationDeleteInput()
    delete_input.set_app_name(APP_NAME)
    delete_input.set_force_deletion(True)
    SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(delete_input)
    validate_equals(app_list.is_app_present(APP_NAME), False, "Vault should not be present after delete")

    get_logger().log_info("Vault app lifecycle test complete")
