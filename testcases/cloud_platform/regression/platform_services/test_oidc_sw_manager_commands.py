"""Verify sw-manager CLI commands with OIDC authentication for all STX roles."""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.oidc.oidc_setup_keywords import OidcSetupKeywords
from keywords.cloud_platform.security.oidc.sw_manager_oidc_keywords import SwManagerOidcKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords


from keywords.cloud_platform.command_wrappers import source_openrc
def verify_swm_read_commands(swm_oidc_kw: SwManagerOidcKeywords, username: str, password: str, lab_oam_ip: str, role_label: str) -> None:
    """Run sw-manager read-only commands and validate they are not denied.

    Args:
        swm_oidc_kw (SwManagerOidcKeywords): sw-manager OIDC keywords instance.
        username (str): LDAP username.
        password (str): LDAP password.
        lab_oam_ip (str): OAM floating IP.
        role_label (str): Role label for logging.
    """
    read_commands = [
        "sw-manager sw-deploy-strategy show",
    ]
    for cmd in read_commands:
        get_logger().log_info(f"{role_label}: running {cmd}")
        result = swm_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, cmd)
        validate_equals(result.is_forbidden(), False, f"{role_label} role must NOT be denied '{cmd}'")


def verify_swm_write_commands_denied(swm_oidc_kw: SwManagerOidcKeywords, username: str, password: str, lab_oam_ip: str, role_label: str) -> None:
    """Run sw-manager write commands and validate they are denied.

    Args:
        swm_oidc_kw (SwManagerOidcKeywords): sw-manager OIDC keywords instance.
        username (str): LDAP username.
        password (str): LDAP password.
        lab_oam_ip (str): OAM floating IP.
        role_label (str): Role label for logging.
    """
    dummy_release = "starlingx-99.99.0"
    write_commands = [
        f"sw-manager sw-deploy-strategy create {dummy_release}",
        "sw-manager sw-deploy-strategy delete",
    ]
    for cmd in write_commands:
        get_logger().log_info(f"{role_label}: {cmd} (expect Forbidden)")
        result = swm_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, cmd)
        validate_equals(result.is_forbidden(), True, f"{role_label} role must be denied '{cmd}'")


def verify_swm_write_commands_allowed(swm_oidc_kw: SwManagerOidcKeywords, username: str, password: str, lab_oam_ip: str, role_label: str) -> None:
    """Run sw-manager write commands and validate they are not denied by RBAC.

    Checks that the server does not return a 403/Forbidden response.
    The commands may fail for non-RBAC reasons (no active deploy, strategy already exists)
    which is acceptable — the test validates authorization, not operational success.

    Args:
        swm_oidc_kw (SwManagerOidcKeywords): sw-manager OIDC keywords instance.
        username (str): LDAP username.
        password (str): LDAP password.
        lab_oam_ip (str): OAM floating IP.
        role_label (str): Role label for logging.
    """
    dummy_release = "starlingx-99.99.0"
    get_logger().log_info(f"{role_label}: sw-manager sw-deploy-strategy create {dummy_release}")
    result = swm_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, f"sw-manager sw-deploy-strategy create {dummy_release}")
    validate_equals(result.is_forbidden(), False, f"{role_label} role must NOT be denied 'sw-manager sw-deploy-strategy create'")

    get_logger().log_info(f"{role_label}: sw-manager sw-deploy-strategy delete")
    result = swm_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "sw-manager sw-deploy-strategy delete")
    validate_equals(result.is_forbidden(), False, f"{role_label} role must NOT be denied 'sw-manager sw-deploy-strategy delete'")


@mark.p2
def test_oidc_sw_manager_admin_role(request: FixtureRequest) -> None:
    """Verify OIDC admin role can execute all sw-manager commands.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create admin role-bindings and LDAP user

    Test Steps:
        1. Verify admin can run sw-manager read commands via OIDC
        2. Verify admin can run sw-manager write commands via OIDC

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_admin_swm01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwmAdminGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    swm_oidc_kw = SwManagerOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: swm_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up admin role-bindings")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP admin user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify admin can run sw-manager read commands via OIDC")
    verify_swm_read_commands(swm_oidc_kw, username, password, lab_oam_ip, "Admin")

    get_logger().log_test_case_step("Verify admin can run sw-manager write commands via OIDC")
    verify_swm_write_commands_allowed(swm_oidc_kw, username, password, lab_oam_ip, "Admin")


@mark.p2
def test_oidc_sw_manager_reader_role(request: FixtureRequest) -> None:
    """Verify OIDC reader role can run sw-manager read commands but is denied write commands.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create reader role-bindings and LDAP user

    Test Steps:
        1. Verify reader can run sw-manager read commands via OIDC
        2. Verify reader is denied sw-manager write commands via OIDC

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_reader_swm01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwmReaderGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    swm_oidc_kw = SwManagerOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: swm_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up reader role-bindings")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "reader")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP reader user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify reader can run sw-manager read commands via OIDC")
    verify_swm_read_commands(swm_oidc_kw, username, password, lab_oam_ip, "Reader")

    get_logger().log_test_case_step("Verify reader is denied sw-manager write commands via OIDC")
    verify_swm_write_commands_denied(swm_oidc_kw, username, password, lab_oam_ip, "Reader")


@mark.p2
def test_oidc_sw_manager_operator_role(request: FixtureRequest) -> None:
    """Verify OIDC operator role can run sw-manager read commands but is denied write commands.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create operator role-bindings and LDAP user

    Test Steps:
        1. Verify operator can run sw-manager read commands via OIDC
        2. Verify operator is denied sw-manager write commands via OIDC

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_oper_swm01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwmOperatorGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    swm_oidc_kw = SwManagerOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: swm_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up operator role-bindings")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "operator")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP operator user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify operator can run sw-manager read commands via OIDC")
    verify_swm_read_commands(swm_oidc_kw, username, password, lab_oam_ip, "Operator")

    get_logger().log_test_case_step("Verify operator is denied sw-manager write commands via OIDC")
    verify_swm_write_commands_denied(swm_oidc_kw, username, password, lab_oam_ip, "Operator")


@mark.p2
def test_oidc_sw_manager_configurator_role(request: FixtureRequest) -> None:
    """Verify OIDC configurator role can execute all sw-manager commands.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create configurator role-bindings and LDAP user

    Test Steps:
        1. Verify configurator can run sw-manager read commands via OIDC
        2. Verify configurator can run sw-manager write commands via OIDC

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_cfg_swm01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwmConfiguratorGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    swm_oidc_kw = SwManagerOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: swm_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up configurator role-bindings")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "configurator")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP configurator user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify configurator can run sw-manager read commands via OIDC")
    verify_swm_read_commands(swm_oidc_kw, username, password, lab_oam_ip, "Configurator")

    get_logger().log_test_case_step("Verify configurator can run sw-manager write commands via OIDC")
    verify_swm_write_commands_allowed(swm_oidc_kw, username, password, lab_oam_ip, "Configurator")


@mark.p2
def test_oidc_sw_manager_keystone_regression() -> None:
    """Verify sw-manager commands work with default Keystone auth when STX_AUTH_TYPE is unset.

    Preconditions:
        - System is accessible via Keystone auth

    Setup:
        - Establish SSH connection to active controller

    Test Steps:
        1. Verify sw-manager sw-deploy-strategy show works with Keystone auth

    Teardown:
        - None
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify sw-manager sw-deploy-strategy show works with Keystone auth")

    output = ssh_connection.send(source_openrc("sw-manager sw-deploy-strategy show"))
    raw = "\n".join(output) if isinstance(output, list) else output
    validate_equals("Authorization failed" not in raw, True, "Keystone auth sw-manager show must not return authorization error")


@mark.p3
def test_oidc_sw_manager_deleted_user(request: FixtureRequest) -> None:
    """Verify deleted LDAP user cannot run sw-manager commands via OIDC.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create admin role-bindings and LDAP user

    Test Steps:
        1. Verify sw-manager show succeeds before user deletion
        2. Delete the LDAP user
        3. Verify user no longer exists in LDAP
        4. Verify deleted user cannot SSH

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_del_swm01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwmDeletedUserGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    swm_oidc_kw = SwManagerOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: swm_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment and role-bindings")
    oidc_setup_kw.setup_oidc_environment()
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify sw-manager show succeeds before user deletion")
    result = swm_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(result.is_forbidden(), False, "User must NOT be denied sw-manager show before deletion")

    get_logger().log_test_case_step("Delete the LDAP user")
    LdapKeywords(ssh_connection, password).delete_user(username)

    get_logger().log_test_case_step("Verify user no longer exists in LDAP")
    validate_equals(oidc_setup_kw.verify_user_deleted(username, password), True, "Deleted user must not exist in LDAP")

    get_logger().log_test_case_step("Verify deleted user cannot SSH")
    swm_oidc_kw.close_session()
    ldap_ssh = SSHConnectionManager.create_ssh_connection(lab_oam_ip, username, password, name=f"deleted-{username}", ssh_port=lab_config.get_ssh_port())
    ssh_failed = not ldap_ssh.is_connected
    if ldap_ssh.is_connected:
        ldap_ssh.close()
    validate_equals(ssh_failed, True, "Deleted user must not be able to SSH")


@mark.p3
def test_oidc_sw_manager_invalid_token(request: FixtureRequest) -> None:
    """Verify sw-manager commands fail with an invalid/corrupted OIDC token.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create admin role-bindings and LDAP user

    Test Steps:
        1. Verify sw-manager show via OIDC succeeds (baseline)
        2. Corrupt OIDC token and verify sw-manager command fails

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_invtok_swm01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwmInvTokenGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    swm_oidc_kw = SwManagerOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: swm_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up admin role-bindings and user")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(teardown_rb)
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify sw-manager show via OIDC succeeds (baseline)")
    result = swm_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(result.is_forbidden(), False, "Admin must NOT be denied sw-manager show (baseline)")

    get_logger().log_test_case_step("Corrupt OIDC token and verify failure")
    swm_oidc_kw.corrupt_cached_oidc_token()
    result = swm_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(result.is_successful(), False, "sw-manager command must fail with invalid/corrupted OIDC token")
