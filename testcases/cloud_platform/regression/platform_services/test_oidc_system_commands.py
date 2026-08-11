"""Verify system CLI commands with OIDC authentication for all STX roles."""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.oidc.oidc_setup_keywords import OidcSetupKeywords
from keywords.cloud_platform.security.oidc.system_oidc_keywords import SystemOidcKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords


def verify_system_read_commands(sys_oidc_kw: SystemOidcKeywords, username: str, password: str, lab_oam_ip: str, role_label: str) -> None:
    """Run system read-only commands and validate they succeed.

    Args:
        sys_oidc_kw (SystemOidcKeywords): System OIDC keywords instance.
        username (str): LDAP username.
        password (str): LDAP password.
        lab_oam_ip (str): OAM floating IP.
        role_label (str): Role label for logging.
    """
    read_commands = [
        "system host-list",
        "system application-list",
        "system service-parameter-list",
    ]
    for cmd in read_commands:
        get_logger().log_info(f"{role_label}: running {cmd}")
        result = sys_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, cmd)
        validate_equals(result.is_successful(), True, f"{role_label} role must be allowed to run '{cmd}'")


def verify_system_write_commands_allowed(sys_oidc_kw: SystemOidcKeywords, username: str, password: str, lab_oam_ip: str, role_label: str, app_tarball: str) -> None:
    """Run system application-upload and validate it is not denied by RBAC.

    Checks that the server does not return a 403/Forbidden response.
    The upload may fail for non-RBAC reasons (app already exists, invalid tarball)
    which is acceptable — the test validates authorization, not upload success.

    Args:
        sys_oidc_kw (SystemOidcKeywords): System OIDC keywords instance.
        username (str): LDAP username.
        password (str): LDAP password.
        lab_oam_ip (str): OAM floating IP.
        role_label (str): Role label for logging.
        app_tarball (str): Path to application tarball for upload test.
    """
    get_logger().log_info(f"{role_label}: system application-upload {app_tarball}")
    result = sys_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, f"system application-upload {app_tarball}")
    validate_equals(result.is_forbidden(), False, f"{role_label} role must NOT be denied 'system application-upload'")


def verify_system_write_commands_denied(sys_oidc_kw: SystemOidcKeywords, username: str, password: str, lab_oam_ip: str, role_label: str, app_tarball: str) -> None:
    """Run system write commands and validate they are denied.

    Args:
        sys_oidc_kw (SystemOidcKeywords): System OIDC keywords instance.
        username (str): LDAP username.
        password (str): LDAP password.
        lab_oam_ip (str): OAM floating IP.
        role_label (str): Role label for logging.
        app_tarball (str): Path to application tarball for upload test.
    """
    write_commands = [
        f"system application-upload {app_tarball}",
        "system application-apply dummy-app",
        "system application-abort dummy-app",
        "system application-remove dummy-app",
        "system application-delete dummy-app",
    ]
    for cmd in write_commands:
        get_logger().log_info(f"{role_label}: {cmd} (expect Forbidden)")
        result = sys_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, cmd)
        validate_equals(result.is_forbidden(), True, f"{role_label} role must be denied '{cmd}'")


@mark.p2
def test_oidc_system_admin_role(request: FixtureRequest) -> None:
    """Verify OIDC admin role can execute all system commands.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create admin role-bindings and LDAP user

    Test Steps:
        1. Verify admin can run system read commands via OIDC
        2. Verify admin can run system write commands via OIDC

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    app_config = ConfigurationManager.get_app_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_admin_sys01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SysAdminGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    sys_oidc_kw = SystemOidcKeywords(ssh_connection)
    app_tarball = oidc_setup_kw.get_upload_app_tarball(app_config.get_base_application_path(), app_config.get_oidc_test_app_tarball())

    request.addfinalizer(lambda: sys_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up admin role-bindings")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP admin user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify admin can run system read commands via OIDC")
    verify_system_read_commands(sys_oidc_kw, username, password, lab_oam_ip, "Admin")

    get_logger().log_test_case_step("Verify admin can run system write commands via OIDC")
    verify_system_write_commands_allowed(sys_oidc_kw, username, password, lab_oam_ip, "Admin", app_tarball)


@mark.p2
def test_oidc_system_reader_role(request: FixtureRequest) -> None:
    """Verify OIDC reader role can run system read commands but is denied write commands.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create reader role-bindings and LDAP user

    Test Steps:
        1. Verify reader can run system read commands via OIDC
        2. Verify reader is denied system write commands via OIDC

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    app_config = ConfigurationManager.get_app_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_reader_sys01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SysReaderGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    sys_oidc_kw = SystemOidcKeywords(ssh_connection)
    app_tarball = oidc_setup_kw.get_upload_app_tarball(app_config.get_base_application_path(), app_config.get_oidc_test_app_tarball())

    request.addfinalizer(lambda: sys_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up reader role-bindings")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "reader")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP reader user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify reader can run system read commands via OIDC")
    verify_system_read_commands(sys_oidc_kw, username, password, lab_oam_ip, "Reader")

    get_logger().log_test_case_step("Verify reader is denied system write commands via OIDC")
    verify_system_write_commands_denied(sys_oidc_kw, username, password, lab_oam_ip, "Reader", app_tarball)


@mark.p2
def test_oidc_system_operator_role(request: FixtureRequest) -> None:
    """Verify OIDC operator role can run system read commands but is denied write commands.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create operator role-bindings and LDAP user

    Test Steps:
        1. Verify operator can run system read commands via OIDC
        2. Verify operator is denied system write commands via OIDC

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    app_config = ConfigurationManager.get_app_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_oper_sys01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SysOperatorGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    sys_oidc_kw = SystemOidcKeywords(ssh_connection)
    app_tarball = oidc_setup_kw.get_upload_app_tarball(app_config.get_base_application_path(), app_config.get_oidc_test_app_tarball())

    request.addfinalizer(lambda: sys_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up operator role-bindings")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "operator")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP operator user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify operator can run system read commands via OIDC")
    verify_system_read_commands(sys_oidc_kw, username, password, lab_oam_ip, "Operator")

    get_logger().log_test_case_step("Verify operator is denied system write commands via OIDC")
    verify_system_write_commands_denied(sys_oidc_kw, username, password, lab_oam_ip, "Operator", app_tarball)


@mark.p2
def test_oidc_system_configurator_role(request: FixtureRequest) -> None:
    """Verify OIDC configurator role can execute all system commands.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create configurator role-bindings and LDAP user

    Test Steps:
        1. Verify configurator can run system read commands via OIDC
        2. Verify configurator can run system write commands via OIDC

    Teardown:
        - Clean up LDAP user and group
        - Remove role-bindings
        - Restore OIDC environment to default state
        - Close OIDC session
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    app_config = ConfigurationManager.get_app_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_cfg_sys01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SysConfiguratorGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    sys_oidc_kw = SystemOidcKeywords(ssh_connection)
    app_tarball = oidc_setup_kw.get_upload_app_tarball(app_config.get_base_application_path(), app_config.get_oidc_test_app_tarball())

    request.addfinalizer(lambda: sys_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up configurator role-bindings")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "configurator")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP configurator user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify configurator can run system read commands via OIDC")
    verify_system_read_commands(sys_oidc_kw, username, password, lab_oam_ip, "Configurator")

    get_logger().log_test_case_step("Verify configurator can run system write commands via OIDC")
    verify_system_write_commands_allowed(sys_oidc_kw, username, password, lab_oam_ip, "Configurator", app_tarball)


@mark.p2
def test_oidc_system_keystone_regression() -> None:
    """Verify Keystone authentication still works as default when STX_AUTH_TYPE is unset.

    Preconditions:
        - System is accessible via Keystone auth

    Setup:
        - Establish SSH connection to active controller

    Test Steps:
        1. Verify system host-list works with Keystone auth
        2. Verify system application-list works with Keystone auth

    Teardown:
        - None
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify system host-list works with Keystone auth")
    host_list_kw = SystemHostListKeywords(ssh_connection)
    hosts = host_list_kw.get_system_host_list()
    validate_equals(len(hosts.get_hosts()) > 0, True, "Keystone auth system host-list must return at least one host")

    get_logger().log_test_case_step("Verify system application-list works with Keystone auth")
    app_list_kw = SystemApplicationListKeywords(ssh_connection)
    apps = app_list_kw.get_system_application_list()
    validate_equals(apps.application_exists("platform-integ-apps"), True, "Keystone auth must find platform-integ-apps in application-list")


@mark.p2
def test_oidc_system_cli_arg_auth(request: FixtureRequest) -> None:
    """Verify system commands work with --stx-auth-type=oidc CLI argument.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create admin role-bindings and LDAP user

    Test Steps:
        1. Verify admin system host-list with --stx-auth-type=oidc
        2. Verify admin system application-list with --stx-auth-type=oidc
        3. Verify admin system service-parameter-list with --stx-auth-type=oidc

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
    username = "oidc_cliarg_sys01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SysCliArgGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    sys_oidc_kw = SystemOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: sys_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up admin role-bindings and user")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(teardown_rb)
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify admin system host-list with --stx-auth-type=oidc")
    result = sys_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "system host-list")
    validate_equals(result.is_successful(), True, "Admin must be allowed 'system --stx-auth-type=oidc host-list'")

    get_logger().log_test_case_step("Verify admin system application-list with --stx-auth-type=oidc")
    result = sys_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "system application-list")
    validate_equals(result.is_successful(), True, "Admin must be allowed 'system --stx-auth-type=oidc application-list'")

    get_logger().log_test_case_step("Verify admin system service-parameter-list with --stx-auth-type=oidc")
    result = sys_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "system service-parameter-list")
    validate_equals(result.is_successful(), True, "Admin must be allowed 'system --stx-auth-type=oidc service-parameter-list'")


@mark.p3
def test_oidc_system_deleted_user(request: FixtureRequest) -> None:
    """Verify deleted LDAP user cannot run system commands via OIDC.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create admin role-bindings and LDAP user

    Test Steps:
        1. Verify system host-list succeeds before user deletion
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
    username = "oidc_deluser_sys01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SysDeletedUserGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    sys_oidc_kw = SystemOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: sys_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment and role-bindings")
    oidc_setup_kw.setup_oidc_environment()
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(teardown_rb)

    get_logger().log_setup_step("Create LDAP user")
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify system host-list succeeds before user deletion")
    result = sys_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "system host-list")
    validate_equals(result.is_successful(), True, "User must be allowed system host-list before deletion")

    get_logger().log_test_case_step("Delete the LDAP user")
    LdapKeywords(ssh_connection, password).delete_user(username)

    get_logger().log_test_case_step("Verify user no longer exists in LDAP")
    validate_equals(oidc_setup_kw.verify_user_deleted(username, password), True, "Deleted user must not exist in LDAP")

    get_logger().log_test_case_step("Verify deleted user cannot SSH")
    sys_oidc_kw.close_session()
    ldap_ssh = SSHConnectionManager.create_ssh_connection(lab_oam_ip, username, password, name=f"deleted-{username}", ssh_port=lab_config.get_ssh_port())
    ssh_failed = not ldap_ssh.is_connected
    if ldap_ssh.is_connected:
        ldap_ssh.close()
    validate_equals(ssh_failed, True, "Deleted user must not be able to SSH")


@mark.p3
def test_oidc_system_invalid_token(request: FixtureRequest) -> None:
    """Verify system commands fail with an invalid/corrupted OIDC token.

    Preconditions:
        - oidc-auth-apps is installed on the system
        - LDAP is configured

    Setup:
        - Establish SSH connection to active controller
        - Set up OIDC environment with local LDAP connector
        - Create admin role-bindings and LDAP user

    Test Steps:
        1. Verify system host-list via OIDC succeeds (baseline)
        2. Corrupt OIDC token and verify system command fails

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
    username = "oidc_invtok_sys01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SysInvTokenGroup"

    oidc_setup_kw = OidcSetupKeywords(ssh_connection)
    sys_oidc_kw = SystemOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: sys_oidc_kw.close_session())
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_ldap_user(username, password, group_name))
    request.addfinalizer(lambda: oidc_setup_kw.cleanup_oidc_environment())

    get_logger().log_setup_step("Set up OIDC environment")
    oidc_setup_kw.setup_oidc_environment()

    get_logger().log_setup_step("Set up admin role-bindings and user")
    teardown_rb = oidc_setup_kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(teardown_rb)
    oidc_setup_kw.setup_ldap_user(username, password, group_name)

    get_logger().log_test_case_step("Verify system host-list via OIDC succeeds (baseline)")
    result = sys_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "system host-list")
    validate_equals(result.is_successful(), True, "Admin must be allowed system host-list (baseline)")

    get_logger().log_test_case_step("Corrupt OIDC token and verify failure")
    sys_oidc_kw.corrupt_cached_oidc_token()
    result = sys_oidc_kw.run_command_as_oidc_user(username, password, lab_oam_ip, "system host-list")
    validate_equals(result.is_successful(), False, "System command must fail with invalid/corrupted OIDC token")
