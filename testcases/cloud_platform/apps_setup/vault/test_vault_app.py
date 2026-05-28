"""Vault application pre/post upgrade tests."""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.vault.vault_keywords import VaultKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "vault"
CHART_PATH = "/usr/local/share/applications/helm/vault-[0-9]*"
NAMESPACE = "vault"
SECRET_PATH = "basic-secret/helloworld"


@mark.p1
def test_vault_pre_upgrade():
    """Verify vault is applied and secrets work before upgrade.

    Runs before both platform upgrades and kubernetes upgrades to establish
    that vault is functional. Leaves the application applied so the
    upgrade proceeds with vault in place.

    Test Steps:
        - Ensure vault application is uploaded and applied
        - Wait for vault pods to be running and unsealed
        - Run setup script to configure K8s auth and KV engine
        - Create a test secret and verify it exists
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()

    get_logger().log_test_case_step("Ensure vault application is applied")
    app_list = SystemApplicationListKeywords(ssh_connection)
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

    get_logger().log_test_case_step("Verify vault pods are running and unsealed")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status("Running", namespace=NAMESPACE, timeout=600)
    vault_keywords = VaultKeywords(ssh_connection, security_config.get_ssh_user_home())
    unsealed = vault_keywords.wait_for_unseal(timeout=300)
    validate_equals(unsealed, True, "Vault should be unsealed before upgrade")

    get_logger().log_test_case_step("Run vault setup script")
    local_script = get_stx_resource_path("resources/cloud_platform/security/vault/setup_vault.sh")
    vault_keywords.run_setup_script(local_script)

    get_logger().log_test_case_step("Create and verify test secret")
    root_token = vault_keywords.get_root_token()
    secret_data = {
        "password": security_config.get_vault_test_secret_password(),
        "username": security_config.get_vault_test_secret_username(),
    }
    vault_keywords.create_secret(SECRET_PATH, secret_data, root_token)
    response = vault_keywords.read_secret(SECRET_PATH, root_token)
    validate_equals("errors" not in response, True, "Secret should be created before upgrade")

    get_logger().log_info("Vault pre-upgrade validation complete — app left applied for upgrade")


@mark.p1
def test_vault_post_upgrade():
    """Verify vault survived upgrade: app applied, pods running, secrets accessible.

    Runs after both platform upgrades and kubernetes upgrades to confirm
    vault is still functional.

    Test Steps:
        - Validate vault application is present and in applied state
        - Verify vault pods are running and unsealed
        - Verify secret created before upgrade is still accessible
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()

    get_logger().log_test_case_step("Validate vault app is still applied after upgrade")
    app_list = SystemApplicationListKeywords(ssh_connection)
    validate_equals(app_list.is_app_present(APP_NAME), True, "Vault should be present after upgrade")
    app_apply = SystemApplicationApplyKeywords(ssh_connection)
    validate_equals(app_apply.is_already_applied(APP_NAME), True, "Vault should be applied after upgrade")

    get_logger().log_test_case_step("Verify vault pods are running and unsealed after upgrade")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status("Running", namespace=NAMESPACE, timeout=600)
    vault_keywords = VaultKeywords(ssh_connection, security_config.get_ssh_user_home())
    unsealed = vault_keywords.wait_for_unseal(timeout=300)
    validate_equals(unsealed, True, "Vault should be unsealed after upgrade")

    get_logger().log_test_case_step("Verify secret accessible after upgrade")
    root_token = vault_keywords.get_root_token()
    secret_data = {
        "password": security_config.get_vault_test_secret_password(),
        "username": security_config.get_vault_test_secret_username(),
    }
    response = vault_keywords.read_secret(SECRET_PATH, root_token)
    validate_equals("errors" not in response, True, "Secret should be accessible after upgrade")
    validate_equals(response["data"]["data"], secret_data, "Secret data should match after upgrade")

    get_logger().log_info("Vault post-upgrade validation complete — app functional after upgrade")
