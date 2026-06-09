"""Verify software CLI OIDC authentication with role-based access control."""

import os
import time

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_config import LabConfig
from config.security.objects.security_config import SecurityConfig
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.cloud_platform.upgrade.objects.software_oidc_command_result import SoftwareOidcCommandResult
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.software_oidc_keywords import SoftwareOidcKeywords
from keywords.cloud_platform.upgrade.software_show_keywords import SoftwareShowKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.deployments.kubectl_scale_deployements_keywords import KubectlScaleDeploymentsKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords
from testcases.cloud_platform.regression.security.test_oidc_fm_commands import setup_oidc_environment as fm_setup_oidc_environment


def setup_oidc_environment(ssh_connection: SSHConnection, security_config: SecurityConfig, lab_config: LabConfig) -> None:
    """Set up the OIDC environment with local LDAP for software commands tests.

    Always applies both dex and oidc-client overrides with local LDAP connector,
    regardless of current app state. This ensures the test is self-contained
    and works after any previous OIDC test (WAD, Keycloak, cert).

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
        lab_config (LabConfig): Lab configuration object.
    """
    fm_setup_oidc_environment(ssh_connection, security_config, lab_config)


def wait_for_rolebindings_file(ssh_connection: SSHConnection, timeout_sec: int = 60) -> None:
    """Wait for /etc/platform/.rolebindings.conf to be created by puppet.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        timeout_sec (int): Maximum seconds to wait.
    """

    def check_rolebindings() -> bool:
        """Check if rolebindings file exists and has content.

        Returns:
            bool: True if file exists and has content.
        """
        output = ssh_connection.send(source_openrc("cat /etc/platform/.rolebindings.conf 2>&1"))
        raw = "\n".join(output) if isinstance(output, list) else output
        return "No such file" not in raw and raw.strip() != ""

    validate_equals_with_retry(
        function_to_execute=check_rolebindings,
        expected_value=True,
        validation_description="Wait for /etc/platform/.rolebindings.conf to be created",
        timeout=timeout_sec,
        polling_sleep_time=5,
    )


def setup_role_bindings(ssh_connection: SSHConnection, request: FixtureRequest, group_name: str, role: str) -> None:
    """Add identity stx role-bindings and register teardown.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        request (FixtureRequest): Pytest request for teardown registration.
        group_name (str): LDAP group name.
        role (str): STX role (admin, reader, operator, configurator).
    """
    service = "identity"
    section = "stx"
    param_name = "role-bindings"

    role_bindings_map = {
        "admin": f"%{group_name}:admin;%{group_name}:member;%{group_name}:reader",
        "configurator": f"%{group_name}:configurator;%{group_name}:reader",
        "operator": f"%{group_name}:operator;%{group_name}:reader",
        "reader": f"%{group_name}:reader",
    }
    param_value = role_bindings_map[role]

    svc_param_kw = SystemServiceParameterKeywords(ssh_connection)

    existing = svc_param_kw.list_service_parameters(service=service, section=section)
    for param in existing.get_parameters():
        if param.get_name() == param_name:
            svc_param_kw.delete_service_parameter(param.get_uuid())
            svc_param_kw.apply_service_parameters(service, section=section)
            break

    svc_param_kw.add_service_parameter(service, section, param_name, param_value)
    svc_param_kw.apply_service_parameters(service, section=section)
    wait_for_rolebindings_file(ssh_connection)

    def teardown() -> None:
        """Remove role-bindings service parameter."""
        current = svc_param_kw.list_service_parameters(service=service, section=section)
        for p in current.get_parameters():
            if p.get_name() == param_name:
                svc_param_kw.delete_service_parameter(p.get_uuid())
                svc_param_kw.apply_service_parameters(service, section=section)
                break

    request.addfinalizer(teardown)


def setup_ldap_user(ssh_connection: SSHConnection, username: str, password: str, group_name: str) -> None:
    """Create LDAP user and group, add user to group.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        username (str): LDAP username to create.
        password (str): Password for the LDAP user.
        group_name (str): LDAP group to create and add user to.
    """
    ldap_kw = LdapKeywords(ssh_connection, password)
    ldap_kw.create_user(username, password)
    ldap_kw.create_group(group_name)
    ldap_kw.add_user_to_group(username, group_name)


def cleanup_ldap_user(ssh_connection: SSHConnection, username: str, password: str, group_name: str, sw_oidc_kw: SoftwareOidcKeywords = None) -> None:
    """Delete LDAP user and group, close OIDC session, restore oidc-username-claim.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        username (str): LDAP username to delete.
        password (str): Sysadmin password for ansible playbook.
        group_name (str): LDAP group to delete.
        sw_oidc_kw (SoftwareOidcKeywords): Optional keywords instance to close session.
    """
    get_logger().log_info(f"Cleaning up LDAP user {username} and group {group_name}")
    if sw_oidc_kw:
        sw_oidc_kw.close_session()
    ldap_kw = LdapKeywords(ssh_connection, password)
    ldap_kw.delete_user(username)
    ldap_kw.delete_group(group_name)


def cleanup_stale_releases(ssh_connection: SSHConnection) -> None:
    """Remove any non-deployed releases that may have been uploaded during testing.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
    """
    software_list = SoftwareListKeywords(ssh_connection).get_software_list(sudo=True)
    for release in software_list.get_software_lists():
        if release.get_state() == "available":
            get_logger().log_info(f"Cleaning stale release: {release.get_release()}")
            USMKeywords(ssh_connection).software_delete(release.get_release(), sudo=True)


@mark.p2
def test_oidc_software_reader_denied_write(request: FixtureRequest) -> None:
    """Verify OIDC reader role can run software read commands but is denied write operations.

    Steps:
        - Set up OIDC environment and reader role-bindings
        - Create LDAP reader user and group
        - Verify reader can run software list and software show
        - Verify reader is denied software upload
        - Verify reader is denied software delete
        - Verify reader is denied software deploy precheck
        - Verify reader is denied software deploy start
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_reader_sw01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwReaderGroup"
    dummy_iso = "/tmp/test_oidc.iso"
    dummy_sig = "/tmp/test_oidc.sig"

    sw_oidc_kw = SoftwareOidcKeywords(ssh_connection)
    file_kw = FileKeywords(ssh_connection)

    request.addfinalizer(lambda: cleanup_stale_releases(ssh_connection))
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, username, password, group_name, sw_oidc_kw))
    request.addfinalizer(lambda: file_kw.delete_file(dummy_iso))
    request.addfinalizer(lambda: file_kw.delete_file(dummy_sig))

    get_logger().log_test_case_step("Step 1: Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Step 2: Create LDAP reader user")
    setup_ldap_user(ssh_connection, username, password, group_name)

    get_logger().log_test_case_step("Step 3: Set up reader role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "reader")

    get_logger().log_test_case_step("Step 4: Verify reader can run 'software list' via OIDC")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "Reader role must be allowed to run 'software list'")

    get_logger().log_test_case_step("Step 5: Verify reader can run 'software show' via OIDC")
    sw_list = SoftwareListKeywords(ssh_connection).get_software_list()
    release_id = sw_list.get_software_lists()[0].get_release()
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, f"software show {release_id}")
    validate_equals(result.is_successful(), True, "Reader role must be allowed to run 'software show'")

    get_logger().log_test_case_step("Step 6: Verify reader is denied 'software upload'")
    # CLI validates file existence and extension before reaching server RBAC.
    # Create dummy files with correct extensions to bypass client-side checks.
    file_kw.create_file_with_echo(dummy_iso, "")
    file_kw.create_file_with_echo(dummy_sig, "")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, f"software upload {dummy_iso} {dummy_sig}")
    validate_equals(result.is_forbidden(), True, "Reader role must be denied 'software upload'")

    get_logger().log_test_case_step("Step 7: Verify reader is denied 'software delete'")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, f"software delete {release_id}")
    validate_equals(result.is_forbidden(), True, "Reader role must be denied 'software delete'")

    get_logger().log_test_case_step("Step 8: Verify reader is denied 'software deploy precheck'")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, f"software deploy precheck {release_id}")
    validate_equals(result.is_forbidden(), True, "Reader role must be denied 'software deploy precheck'")

    get_logger().log_test_case_step("Step 9: Verify reader is denied 'software deploy start'")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, f"software deploy start {release_id}")
    validate_equals(result.is_forbidden(), True, "Reader role must be denied 'software deploy start'")


@mark.p2
def test_oidc_software_admin_allowed_all(request: FixtureRequest) -> None:
    """Verify OIDC admin role can run all software commands including write operations.

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP admin user and group
        - Verify admin can run software list and software show
        - Verify admin is NOT denied software upload
        - Verify admin is NOT denied software delete
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    usm_config = ConfigurationManager.get_usm_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_admin_sw01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwAdminGroup"
    dummy_iso = "/tmp/test_oidc_admin.iso"
    dummy_sig = "/tmp/test_oidc_admin.sig"
    patch_path = usm_config.get_patch_path()
    dest_dir = usm_config.get_dest_dir()
    patch_filename = os.path.basename(patch_path) if patch_path else ""
    patch_local_path = os.path.join(dest_dir, patch_filename) if patch_path else ""

    sw_oidc_kw = SoftwareOidcKeywords(ssh_connection)
    file_kw = FileKeywords(ssh_connection)

    request.addfinalizer(lambda: cleanup_stale_releases(ssh_connection))
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, username, password, group_name, sw_oidc_kw))
    request.addfinalizer(lambda: file_kw.delete_file(dummy_iso))
    request.addfinalizer(lambda: file_kw.delete_file(dummy_sig))
    if patch_local_path:
        request.addfinalizer(lambda: file_kw.delete_file(patch_local_path))

    get_logger().log_test_case_step("Step 1: Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Step 2: Create LDAP admin user")
    setup_ldap_user(ssh_connection, username, password, group_name)

    get_logger().log_test_case_step("Step 3: Set up admin role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "admin")

    get_logger().log_test_case_step("Step 4: Verify admin can run 'software list' via OIDC")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "Admin role must be allowed to run 'software list'")

    get_logger().log_test_case_step("Step 5: Verify admin can run 'software show' via OIDC")
    sw_list = SoftwareListKeywords(ssh_connection).get_software_list()
    release_id = sw_list.get_software_lists()[0].get_release()
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, f"software show {release_id}")
    validate_equals(result.is_successful(), True, "Admin role must be allowed to run 'software show'")

    get_logger().log_test_case_step("Step 6: Verify admin is NOT denied 'software upload' (dummy file)")
    # Admin passes authorization — server may reject the file content but must not return 403.
    file_kw.create_file_with_echo(dummy_iso, "")
    file_kw.create_file_with_echo(dummy_sig, "")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, f"software upload {dummy_iso} {dummy_sig}")
    validate_equals(result.is_forbidden(), False, "Admin role must NOT be denied 'software upload'")

    get_logger().log_test_case_step("Step 7: Verify admin can upload a real patch file")
    # Copy real patch from build server and upload via OIDC
    if usm_config.get_copy_from_remote():
        file_kw.create_directory(dest_dir)
        file_kw.rsync_from_remote_server(
            remote_server=usm_config.get_remote_server(),
            remote_user=usm_config.get_remote_username(),
            remote_password=usm_config.get_remote_password(),
            remote_path=patch_path,
            local_dest_path=patch_local_path,
        )
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, f"software upload {patch_local_path}")
    validate_equals(result.is_forbidden(), False, "Admin role must NOT be denied real patch upload")
    validate_equals(result.is_successful(), True, "Admin real patch upload must succeed")

    get_logger().log_test_case_step("Step 8: Verify admin can delete the uploaded release")
    uploaded_release_id = usm_config.get_to_release_ids()[0]
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, f"software delete {uploaded_release_id}")
    validate_equals(result.is_forbidden(), False, "Admin role must NOT be denied 'software delete'")


@mark.p2
def test_oidc_software_invalid_token(request: FixtureRequest) -> None:
    """Verify software commands fail with a corrupted OIDC token.

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP user and verify software list works (baseline)
        - Corrupt the OIDC token in kubeconfig
        - Verify software list fails with authentication error
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_invtoken_sw01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwInvTokenGroup"

    sw_oidc_kw = SoftwareOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, username, password, group_name, sw_oidc_kw))

    get_logger().log_test_case_step("Step 1: Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Step 2: Create LDAP user")
    setup_ldap_user(ssh_connection, username, password, group_name)

    get_logger().log_test_case_step("Step 3: Set up admin role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "admin")

    get_logger().log_test_case_step("Step 4: Verify software list works (baseline)")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "Baseline: software list must succeed with valid token")

    get_logger().log_test_case_step("Step 5: Corrupt OIDC token in kubeconfig")
    # Close existing session and create a new one with corrupted token
    ldap_ssh = sw_oidc_kw.get_ldap_ssh()
    ldap_ssh.send("sed -i 's/token:.*/token: INVALID_TOKEN_CORRUPTED/' $HOME/.kube/config")

    get_logger().log_test_case_step("Step 6: Verify software list fails with invalid token")
    combined = sw_oidc_kw.build_software_command("software list")
    output = ldap_ssh.send(combined, command_timeout=60)
    raw_output = "\n".join(output) if isinstance(output, list) else output
    result = SoftwareOidcCommandResult("software list", raw_output)
    validate_equals(result.is_successful(), False, "Software command must fail with corrupted OIDC token")


@mark.p2
def test_oidc_software_keystone_default(request: FixtureRequest) -> None:
    """Verify software commands work with default Keystone auth when STX_AUTH_TYPE is unset.

    Steps:
        - Run software list via Keystone (source openrc, no STX_AUTH_TYPE)
        - Run software show via Keystone
        - Confirm no regression in default authentication
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Step 1: Verify 'software list' works with default Keystone auth")
    sw_list = SoftwareListKeywords(ssh_connection).get_software_list()
    releases = sw_list.get_software_lists()
    validate_equals(len(releases) > 0, True, "software list must return at least one release via Keystone")

    get_logger().log_test_case_step("Step 2: Verify 'software show' works with default Keystone auth")
    release_id = releases[0].get_release()
    show_output = SoftwareShowKeywords(ssh_connection).get_software_show(release_id)
    validate_equals(show_output is not None, True, "software show must return release details via Keystone")


@mark.p2
def test_oidc_software_missing_kubeconfig(request: FixtureRequest) -> None:
    """Verify software CLI fails with clear error when KUBECONFIG file is missing.

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP user and verify baseline works
        - Remove ~/.kube/config
        - Verify software list fails with authentication error
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_mkcfg_sw01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwMkCfgGroup"

    sw_oidc_kw = SoftwareOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, username, password, group_name, sw_oidc_kw))

    get_logger().log_test_case_step("Step 1: Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Step 2: Create LDAP user")
    setup_ldap_user(ssh_connection, username, password, group_name)

    get_logger().log_test_case_step("Step 3: Set up admin role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "admin")

    get_logger().log_test_case_step("Step 4: Verify software list works (baseline)")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "Baseline: software list must succeed")

    get_logger().log_test_case_step("Step 5: Remove ~/.kube/config and verify failure")
    ldap_ssh = sw_oidc_kw.get_ldap_ssh()
    # Backup and remove kubeconfig
    ldap_ssh.send("cp $HOME/.kube/config $HOME/.kube/config.bak")
    ldap_ssh.send("rm -f $HOME/.kube/config")

    # Run software command — should fail due to missing kubeconfig
    combined = sw_oidc_kw.build_software_command("software list")
    output = ldap_ssh.send(combined, command_timeout=60)
    raw_output = "\n".join(output) if isinstance(output, list) else output
    result = SoftwareOidcCommandResult("software list", raw_output)
    validate_equals(result.is_successful(), False, "Software command must fail when KUBECONFIG is missing")

    # Restore kubeconfig for clean teardown
    ldap_ssh.send("cp $HOME/.kube/config.bak $HOME/.kube/config")


@mark.p2
@mark.lab_has_standby_controller
def test_oidc_software_survives_swact(request: FixtureRequest) -> None:
    """Verify OIDC software authentication continues to work after controller SWACT.

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP user, verify software list works via OIDC (baseline)
        - Perform controller SWACT
        - Re-authenticate and verify software list works on new active controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_swact_sw01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwSwactGroup"

    sw_oidc_kw = SoftwareOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, username, password, group_name, sw_oidc_kw))

    get_logger().log_test_case_step("Step 1: Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Step 2: Create LDAP user")
    setup_ldap_user(ssh_connection, username, password, group_name)

    get_logger().log_test_case_step("Step 3: Set up admin role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "admin")

    get_logger().log_test_case_step("Step 4: Verify software list works via OIDC (pre-SWACT)")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "software list must succeed before SWACT")

    get_logger().log_test_case_step("Step 5: Perform controller SWACT")
    # Close OIDC session before SWACT — it will be on the old controller
    sw_oidc_kw.close_session()
    swact_kw = SystemHostSwactKeywords(ssh_connection)
    swact_kw.host_swact()
    get_logger().log_info("SWACT completed successfully")

    get_logger().log_test_case_step("Step 6: Verify software list works via OIDC (post-SWACT)")
    # Re-authenticate on the new active controller
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "software list must succeed after SWACT")

    get_logger().log_test_case_step("Step 7: SWACT back to restore original state")
    sw_oidc_kw.close_session()
    swact_kw.host_swact()
    get_logger().log_info("SWACT-back completed, original active controller restored")


@mark.p2
def test_oidc_software_token_tampering(request: FixtureRequest) -> None:
    """Verify server rejects OIDC tokens with tampered signatures.

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP user, verify software list works (baseline)
        - Tamper with the token signature in kubeconfig (flip last chars)
        - Verify software command fails with authentication error
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_tamper_sw01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwTamperGroup"

    sw_oidc_kw = SoftwareOidcKeywords(ssh_connection)

    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, username, password, group_name, sw_oidc_kw))

    get_logger().log_test_case_step("Step 1: Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Step 2: Create LDAP user")
    setup_ldap_user(ssh_connection, username, password, group_name)

    get_logger().log_test_case_step("Step 3: Set up admin role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "admin")

    get_logger().log_test_case_step("Step 4: Verify software list works (baseline)")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "Baseline: software list must succeed with valid token")

    get_logger().log_test_case_step("Step 5: Tamper with token signature in kubeconfig")
    ldap_ssh = sw_oidc_kw.get_ldap_ssh()
    # Modify the token value — append garbage to corrupt the signature portion
    # This simulates an attacker modifying the JWT signature
    ldap_ssh.send("sed -i 's/\\(token: .*\\)/\\1TAMPERED/' $HOME/.kube/config")

    get_logger().log_test_case_step("Step 6: Verify software command fails with tampered token")
    combined = sw_oidc_kw.build_software_command("software list")
    output = ldap_ssh.send(combined, command_timeout=60)
    raw_output = "\n".join(output) if isinstance(output, list) else output
    result = SoftwareOidcCommandResult("software list", raw_output)
    validate_equals(result.is_successful(), False, "Software command must fail with tampered OIDC token signature")


@mark.p2
def test_oidc_software_token_caching_idp_offline(request: FixtureRequest) -> None:
    """Verify server-side cached OIDC token works when IDP (DEX) is temporarily offline.

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP user, verify software list works (baseline)
        - Scale DEX deployment to 0 (IDP offline)
        - Verify software list still works using cached token validation
        - Scale DEX back to 1 (restore IDP)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_cache_sw01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwCacheGroup"
    dex_namespace = "kube-system"
    dex_deployment = "oidc-dex"

    sw_oidc_kw = SoftwareOidcKeywords(ssh_connection)
    scale_kw = KubectlScaleDeploymentsKeywords(ssh_connection)

    def restore_dex() -> None:
        """Restore DEX to 1 replica."""
        get_logger().log_info("Restoring DEX deployment to 1 replica")
        scale_kw.scale_deployment(dex_deployment, 1, dex_namespace)

    request.addfinalizer(restore_dex)
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, username, password, group_name, sw_oidc_kw))

    get_logger().log_test_case_step("Step 1: Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Step 2: Create LDAP user")
    setup_ldap_user(ssh_connection, username, password, group_name)

    get_logger().log_test_case_step("Step 3: Set up admin role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "admin")

    get_logger().log_test_case_step("Step 4: Verify software list works (baseline with IDP online)")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "Baseline: software list must succeed with IDP online")

    get_logger().log_test_case_step("Step 5: Scale DEX to 0 replicas (IDP offline)")
    scale_kw.scale_deployment(dex_deployment, 0, dex_namespace)
    get_logger().log_info("DEX scaled to 0 — IDP is now offline")

    get_logger().log_test_case_step("Step 6: Verify software list still works with cached token")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "software list must succeed with cached token when IDP is offline")

    get_logger().log_test_case_step("Step 7: Restore DEX to 1 replica")
    scale_kw.scale_deployment(dex_deployment, 1, dex_namespace)
    get_logger().log_info("DEX restored to 1 replica")


@mark.p2
def test_oidc_software_refresh_token(request: FixtureRequest) -> None:
    """Verify client auto-refreshes expired ID token using refresh token.

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Update DEX token expiry to 2 minutes
        - Create LDAP user, authenticate and run software list (baseline)
        - Wait for ID token to expire (2+ minutes)
        - Run software list again — client should auto-refresh using refresh token
        - Restore original token expiry (24h)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_refresh_sw01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "SwRefreshGroup"
    app_name = "oidc-auth-apps"
    chart_name = "dex"
    namespace = "kube-system"
    short_expiry = "config.expiry.idTokens=2m"
    original_expiry = "config.expiry.idTokens=24h"

    sw_oidc_kw = SoftwareOidcKeywords(ssh_connection)
    helm_kw = SystemHelmOverrideKeywords(ssh_connection)
    app_apply_kw = SystemApplicationApplyKeywords(ssh_connection)

    def restore_expiry() -> None:
        """Restore token expiry to 24h and reapply."""
        get_logger().log_info("Restoring token expiry to 24h")
        helm_kw.helm_override_update_with_list_of_values(app_name, chart_name, namespace, True, [original_expiry])
        app_apply_kw.system_application_apply(app_name, timeout=900)

    request.addfinalizer(restore_expiry)
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, username, password, group_name, sw_oidc_kw))

    get_logger().log_test_case_step("Step 1: Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Step 2: Create LDAP user")
    setup_ldap_user(ssh_connection, username, password, group_name)

    get_logger().log_test_case_step("Step 3: Set up admin role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "admin")

    get_logger().log_test_case_step("Step 4: Set token expiry to 2 minutes and reapply")
    helm_kw.helm_override_update_with_list_of_values(app_name, chart_name, namespace, True, [short_expiry])
    app_apply_kw.system_application_apply(app_name, timeout=900)
    # Wait for DEX pod to be fully ready after reapply
    get_logger().log_info("Waiting for DEX pod to stabilize after reapply")

    def check_dex_pod_running() -> bool:
        """Check if DEX pod phase is Running.

        Returns:
            bool: True if pod is Running.
        """
        cmd = "kubectl --kubeconfig=/etc/kubernetes/admin.conf get pods -n kube-system" " -l app=dex -o jsonpath='{.items[0].status.phase}'"
        output = ssh_connection.send(source_openrc(cmd))
        raw = "\n".join(output) if isinstance(output, list) else output
        return "Running" in raw

    def check_dex_pod_ready() -> bool:
        """Check if DEX pod is 1/1 Ready.

        Returns:
            bool: True if pod shows 1/1.
        """
        cmd = "kubectl --kubeconfig=/etc/kubernetes/admin.conf get pods -n kube-system" " -l app=dex --no-headers"
        output = ssh_connection.send(source_openrc(cmd))
        raw = "\n".join(output) if isinstance(output, list) else output
        return "1/1" in raw

    validate_equals_with_retry(
        function_to_execute=check_dex_pod_running,
        expected_value=True,
        validation_description="Wait for DEX pod to be Running",
        timeout=120,
        polling_sleep_time=10,
    )
    # Additional wait for DEX to be fully serving (readiness probe)
    validate_equals_with_retry(
        function_to_execute=check_dex_pod_ready,
        expected_value=True,
        validation_description="Wait for DEX pod to be 1/1 Ready",
        timeout=120,
        polling_sleep_time=10,
    )

    get_logger().log_test_case_step("Step 5: Authenticate and verify software list works (baseline)")
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "Baseline: software list must succeed with fresh token")

    get_logger().log_test_case_step("Step 6: Wait for ID token to expire (2+ minutes)")
    get_logger().log_info("Waiting 150 seconds for ID token expiry...")
    wait_start = time.time()
    validate_equals_with_retry(
        function_to_execute=lambda: time.time() - wait_start >= 150,
        expected_value=True,
        validation_description="Waiting 150s for token expiry",
        timeout=180,
        polling_sleep_time=30,
    )

    get_logger().log_test_case_step("Step 7: Verify software list succeeds via refresh token")
    # Client should auto-refresh the expired ID token using the refresh token
    result = sw_oidc_kw.run_software_command_as_oidc_user(username, password, lab_oam_ip, "software list")
    validate_equals(result.is_successful(), True, "software list must succeed after token refresh")

    get_logger().log_test_case_step("Step 8: Restore token expiry to 24h")
    helm_kw.helm_override_update_with_list_of_values(app_name, chart_name, namespace, True, [original_expiry])
    app_apply_kw.system_application_apply(app_name, timeout=900)
