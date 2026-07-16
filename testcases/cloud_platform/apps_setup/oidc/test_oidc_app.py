"""OIDC DEX connector pre/post upgrade, rollback, and B&R validation.

Validates that OIDC settings (dex overrides, oidc-username-claim,
service parameters) are preserved unchanged across upgrade, rollback,
and backup-restore operations, and that E2E OIDC access continues to work.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords


def _load_dex_config() -> dict:
    """Load DEX connector config from JSON5.

    Returns:
        dict: Configuration dictionary.
    """
    return ConfigurationManager.get_security_config().get_dex_connector_config()


def _verify_oidc_app_healthy(ssh_connection: SSHConnection) -> None:
    """Verify oidc-auth-apps is applied and pods are ready.

    Args:
        ssh_connection (SSHConnection): Active controller SSH.
    """
    app_keywords = SystemApplicationListKeywords(ssh_connection)
    app_list = app_keywords.get_system_application_list()
    app = app_list.get_application("oidc-auth-apps")
    validate_equals(app.get_status(), "applied", "oidc-auth-apps should be applied")
    kubectl_wait = KubectlWaitPodKeywords(ssh_connection)
    kubectl_wait.wait_for_pods_ready("app=dex", "kube-system")


def _verify_oidc_settings_preserved(ssh_connection: SSHConnection, config: dict) -> None:
    """Verify dex overrides and oidc-username-claim are unchanged.

    Args:
        ssh_connection (SSHConnection): Active controller SSH.
        config (dict): Expected DEX connector configuration.
    """
    dex_keywords = DexConnectorKeywords(ssh_connection)

    get_logger().log_info("Verifying oidc-username-claim preserved")
    current_claim = dex_keywords.get_oidc_username_claim()
    validate_equals(current_claim, config["oidc_username_claim"]["default"], "oidc-username-claim should be preserved")

    get_logger().log_info("Verifying dex helm overrides preserved")
    dex_keywords.helm_override_keywords.verify_helm_user_override(config["local_ldap"]["email_attr"], config["oidc_app_name"], "dex", config["namespace"])


def _verify_oidc_access_works(ssh_connection: SSHConnection) -> None:
    """Verify basic OIDC platform access still works.

    Args:
        ssh_connection (SSHConnection): Active controller SSH.
    """
    get_logger().log_info("Verifying STX platform access via system host-list")
    ssh_connection.send(source_openrc("system host-list"))
    rc = ssh_connection.get_return_code()
    validate_equals(rc, 0, "system host-list should succeed post-operation")


@mark.p0
@mark.lab_has_standby_controller
def test_oidc_pre_upgrade():
    """Verify OIDC is healthy and record settings before upgrade.

    Test Steps:
        - Verify oidc-auth-apps is applied and pods running
        - Verify oidc-username-claim value
        - Verify dex helm overrides are present
        - Verify system host-list access
    """
    config = _load_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify oidc-auth-apps healthy")
    _verify_oidc_app_healthy(ssh_connection)

    get_logger().log_test_case_step("Verify OIDC settings")
    _verify_oidc_settings_preserved(ssh_connection, config)

    get_logger().log_test_case_step("Verify platform access")
    _verify_oidc_access_works(ssh_connection)


@mark.p0
@mark.lab_has_standby_controller
def test_oidc_post_upgrade():
    """Verify OIDC settings preserved and access works after upgrade.

    Test Steps:
        - Verify oidc-auth-apps is applied and pods running
        - Verify oidc-username-claim unchanged
        - Verify dex helm overrides unchanged
        - Verify system host-list access still works
    """
    config = _load_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify oidc-auth-apps healthy post-upgrade")
    _verify_oidc_app_healthy(ssh_connection)

    get_logger().log_test_case_step("Verify OIDC settings preserved post-upgrade")
    _verify_oidc_settings_preserved(ssh_connection, config)

    get_logger().log_test_case_step("Verify platform access post-upgrade")
    _verify_oidc_access_works(ssh_connection)


@mark.p0
@mark.lab_has_standby_controller
def test_oidc_post_rollback():
    """Verify OIDC settings preserved and access works after rollback.

    Test Steps:
        - Verify oidc-auth-apps is applied and pods running
        - Verify oidc-username-claim unchanged
        - Verify dex helm overrides unchanged
        - Verify system host-list access still works
    """
    config = _load_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify oidc-auth-apps healthy post-rollback")
    _verify_oidc_app_healthy(ssh_connection)

    get_logger().log_test_case_step("Verify OIDC settings preserved post-rollback")
    _verify_oidc_settings_preserved(ssh_connection, config)

    get_logger().log_test_case_step("Verify platform access post-rollback")
    _verify_oidc_access_works(ssh_connection)


@mark.p0
@mark.lab_has_standby_controller
def test_oidc_post_backup_restore():
    """Verify OIDC settings preserved and access works after backup & restore.

    Test Steps:
        - Verify oidc-auth-apps is applied and pods running
        - Verify oidc-username-claim unchanged
        - Verify dex helm overrides unchanged
        - Verify system host-list access still works
    """
    config = _load_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify oidc-auth-apps healthy post-B&R")
    _verify_oidc_app_healthy(ssh_connection)

    get_logger().log_test_case_step("Verify OIDC settings preserved post-B&R")
    _verify_oidc_settings_preserved(ssh_connection, config)

    get_logger().log_test_case_step("Verify platform access post-B&R")
    _verify_oidc_access_works(ssh_connection)
