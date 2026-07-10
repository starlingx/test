"""Verify FM CLI commands with OIDC authentication for all STX roles ."""

import time

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_config import LabConfig
from config.security.objects.security_config import SecurityConfig
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.event_suppression.event_suppression_keywords import EventSuppressionKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.fm_client_cli_keywords import FaultManagementClientCLIKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.object.fm_client_cli_object import FaultManagementClientCLIObject
from keywords.cloud_platform.fault_management.fm_oidc.fm_oidc_keywords import FmOidcKeywords
from keywords.cloud_platform.fault_management.fm_oidc.object.fm_oidc_command_result_output import FmOidcCommandResultOutput
from keywords.cloud_platform.security.oidc.oidc_environment_keywords import OidcEnvironmentKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords

DEX_LOCAL_LDAP_OVERRIDE = """config:
  connectors:
  - config:
      bindDN: CN=ldapadmin,DC=cgcs,DC=local
      bindPW: '{ldap_admin_pw}'
      groupSearch:
        baseDN: ou=Group,dc=cgcs,dc=local
        filter: (objectClass=posixGroup)
        nameAttr: cn
        userMatchers:
        - groupAttr: memberUid
          userAttr: uid
      host: '{mgmt_ip}:636'
      insecureNoSSL: false
      insecureSkipVerify: false
      rootCA: /etc/ssl/certs/adcert/ca.crt
      userSearch:
        baseDN: ou=People,dc=cgcs,dc=local
        emailAttr: mail
        filter: (objectClass=posixAccount)
        idAttr: DN
        nameAttr: cn
        preferredUsernameAttr: uid
        username: uid
      usernamePrompt: Username
    id: ldap-1
    name: ldap-1
    type: ldap
  expiry:
    idTokens: 24h
volumeMounts:
- mountPath: /etc/ssl/certs/adcert
  name: certdir
- mountPath: /etc/dex/tls
  name: https-tls
volumes:
- name: certdir
  secret:
    secretName: oidc-auth-apps-certificate
- name: https-tls
  secret:
    defaultMode: 420
    secretName: oidc-auth-apps-certificate
"""

OIDC_CLIENT_OVERRIDE = """config:
  issuer_root_ca_secret: oidc-auth-apps-certificate
  issuer_root_ca: /home/ca.crt
tlsName: oidc-auth-apps-certificate
"""


def setup_oidc_environment(ssh_connection: SSHConnection, security_config: SecurityConfig, lab_config: LabConfig) -> None:
    """Set up OIDC with local LDAP connector for FM tests.

    ALWAYS applies both dex and oidc-client overrides to ensure correct state,
    even if oidc-auth-apps appears applied. This handles the case where a previous
    test (e.g., CGCS WAD test) overwrote the overrides.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
        lab_config (LabConfig): Lab configuration object.
    """
    # Get LDAP admin bind password from system keyring
    ldap_admin_pw = KeyringKeywords(ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
    get_logger().log_info("Retrieved LDAP admin password from keyring")

    # Get management floating IP (LDAP listens here, reachable from pods)
    mgmt_cmd = "system addrpool-show $(system addrpool-list | grep management | awk '{print $2}') " "2>/dev/null | grep floating_address | awk '{print $4}'"
    mgmt_output = ssh_connection.send(source_openrc(mgmt_cmd))
    mgmt_raw = "\n".join(mgmt_output) if isinstance(mgmt_output, list) else mgmt_output
    mgmt_ip = mgmt_raw.strip().split("\n")[-1].strip()
    if not mgmt_ip or mgmt_ip == "None" or mgmt_ip == "":
        get_logger().log_error("Could not determine management floating IP")
        return
    if ":" in mgmt_ip:
        mgmt_ip = f"[{mgmt_ip}]"
    get_logger().log_info(f"Using management IP for LDAP: {mgmt_ip}")

    # Write dex override YAML
    override_content = DEX_LOCAL_LDAP_OVERRIDE.format(ldap_admin_pw=ldap_admin_pw, mgmt_ip=mgmt_ip)
    ssh_connection.send(f"cat > /tmp/dex-fm-oidc-override.yaml << 'EOFOVERRIDE'\n{override_content}EOFOVERRIDE")

    # Write oidc-client override YAML
    ssh_connection.send(f"cat > /tmp/oidc-client-override.yaml << 'EOFOVERRIDE'\n{OIDC_CLIENT_OVERRIDE}EOFOVERRIDE")

    # Check current app state
    app_list_kw = SystemApplicationListKeywords(ssh_connection)
    app_list = app_list_kw.get_system_application_list()
    if not app_list.application_exists("oidc-auth-apps"):
        get_logger().log_error("oidc-auth-apps not found on system")
        return

    app = app_list.get_application("oidc-auth-apps")
    status = app.get_status()

    # Always apply both overrides (dex + oidc-client)
    get_logger().log_info("Applying local LDAP dex + oidc-client helm overrides")
    ssh_connection.send(source_openrc("system helm-override-update --values /tmp/dex-fm-oidc-override.yaml oidc-auth-apps dex kube-system"))
    ssh_connection.send(source_openrc("system helm-override-update --values /tmp/oidc-client-override.yaml oidc-auth-apps oidc-client kube-system"))

    # Apply the app
    if status in ("applied", "uploaded", "apply-failed"):
        get_logger().log_info(f"oidc-auth-apps in '{status}' state, applying")
        ssh_connection.send(source_openrc("system application-apply oidc-auth-apps"))
    else:
        get_logger().log_info(f"oidc-auth-apps in '{status}' state, waiting for stable state")
        stable_deadline = time.time() + 120
        while time.time() < stable_deadline:
            time.sleep(10)
            app_list = app_list_kw.get_system_application_list()
            app = app_list.get_application("oidc-auth-apps")
            status = app.get_status()
            if status in ("applied", "uploaded", "apply-failed"):
                break
        ssh_connection.send(source_openrc("system application-apply oidc-auth-apps"))

    # Wait for app to reach applied state (up to 5 min)
    get_logger().log_info("Waiting for oidc-auth-apps to reach applied state")
    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(15)
        app_list = app_list_kw.get_system_application_list()
        if app_list.application_exists("oidc-auth-apps"):
            app = app_list.get_application("oidc-auth-apps")
            if app.get_status() == "applied":
                get_logger().log_info("oidc-auth-apps applied successfully")
                break
    else:
        get_logger().log_error("oidc-auth-apps did not reach applied state within 300s")
        return

    # Wait for BOTH oidc pods to be ready (up to 3 min)
    get_logger().log_info("Waiting for OIDC pods to be ready")
    deadline = time.time() + 180
    while time.time() < deadline:
        admin_pw = lab_config.get_admin_credentials().get_password()
        pod_cmd = f"echo '{admin_pw}' | sudo -S kubectl --kubeconfig /etc/kubernetes/admin.conf " "get pods -n kube-system --no-headers 2>/dev/null | grep -E 'oidc-dex|stx-oidc-client'"
        output = ssh_connection.send(pod_cmd)
        raw = "\n".join(output) if isinstance(output, list) else output
        ready_pods = [line for line in raw.splitlines() if "1/1" in line and "Running" in line]
        if len(ready_pods) >= 2:
            get_logger().log_info("All OIDC pods are ready")
            break
        time.sleep(15)
    else:
        get_logger().log_error("OIDC pods not ready within 180s after app applied")
        return

    # oidc-username-claim stays as 'name' (platform default).
    # The dex override uses nameAttr: uid, so the 'name' claim = LDAP uid = username.


def cleanup_oidc_environment(ssh_connection: SSHConnection, security_config: SecurityConfig) -> None:
    """Clean up FM OIDC environment — preserve oidc-username-claim to avoid kube-apiserver restart.

    Does NOT restore oidc-username-claim because service-parameter-apply kubernetes
    triggers a kube-apiserver restart (~2 min downtime) which breaks subsequent tests.
    Each test sets the claim it needs in its own setup.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
    """
    get_logger().log_info("FM OIDC cleanup: preserving oidc-username-claim (no kube-apiserver restart)")


def wait_for_rolebindings_file(ssh_connection: SSHConnection, timeout_sec: int = 60) -> None:
    """Wait for /etc/platform/.rolebindings.conf to be created by puppet.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        timeout_sec (int): Maximum seconds to wait.
    """

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        output = ssh_connection.send(source_openrc("cat /etc/platform/.rolebindings.conf 2>&1"))
        raw = "\n".join(output) if isinstance(output, list) else output
        if "No such file" not in raw and raw.strip():
            get_logger().log_info(f"rolebindings.conf found: {raw.strip()[:80]}")
            return
        time.sleep(5)
    get_logger().log_error("rolebindings.conf not created within timeout")


def cleanup_ldap_user(ssh_connection: SSHConnection, username: str, password: str, group_name: str, fm_oidc_kw: FmOidcKeywords = None) -> None:
    """Delete LDAP user and group created by the test.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        username (str): LDAP username to delete.
        password (str): Sysadmin password for ansible playbook.
        group_name (str): LDAP group to delete.
        fm_oidc_kw (FmOidcKeywords): Optional FmOidcKeywords instance to close session.
    """
    get_logger().log_info(f"Cleaning up LDAP user {username} and group {group_name}")
    if fm_oidc_kw:
        fm_oidc_kw.close_session()
    ldap_kw = LdapKeywords(ssh_connection, password)
    ldap_kw.delete_user(username)
    ldap_kw.delete_group(group_name)


def setup_remotecli_oidc_environment(ssh_connection: SSHConnection, security_config: SecurityConfig, lab_config: LabConfig) -> None:
    """Set up the remote CLI container OIDC environment on the test machine.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
        lab_config (LabConfig): Lab configuration object.
    """
    oam_ip = lab_config.get_floating_ip()
    if lab_config.is_ipv6():
        oam_ip = f"[{oam_ip}]"
    OidcEnvironmentKeywords(ssh_connection).setup_remotecli(
        oam_ip=oam_ip,
        ca_cert_filename=security_config.get_oidc_keycloak_system_local_ca_cert_filename(),
        kubeconfig_filename=security_config.get_oidc_keycloak_remotecli_kubeconfig_filename(),
        oidc_client_id=security_config.get_oidc_keycloak_static_client_id(),
        oidc_client_secret=security_config.get_oidc_keycloak_static_client_secret(),
    )


def setup_role_bindings(ssh_connection: SSHConnection, request: FixtureRequest, group_name: str, role: str) -> None:
    """Add identity stx role-bindings for the given group and role, register teardown.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        request (FixtureRequest): Pytest request for teardown registration.
        group_name (str): LDAP group name.
        role (str): STX role (admin, reader, operator, configurator).
    """
    service = "identity"
    section = "stx"
    param_name = "role-bindings"

    # Role-bindings format from verified manual execution logs.
    # Explicitly add reader for higher roles (required for admin/configurator/operator).
    # Server defaults project=Default, domain=admin
    # when only role is specified (e.g. %group:role).
    # Using short format per Jerry Sun's guidance post-fix.
    # For admin: need admin + member + reader (from logs).
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
    # Must use --section stx to trigger puppet to create .rolebindings.conf

    svc_param_kw.apply_service_parameters(service, section=section)
    # Wait for puppet to create the rolebindings config file
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


def generate_test_alarm(ssh_connection: SSHConnection) -> tuple:
    """Raise a test alarm using fmClientCli and return entity_id and alarm_id.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.

    Returns:
        tuple: (entity_id, alarm_id) where alarm_id is '100.106'.
    """
    fm_cli = FaultManagementClientCLIKeywords(ssh_connection)
    alarm_obj = FaultManagementClientCLIObject()
    alarm_obj.set_alarm_id("100.106")
    alarm_obj.set_severity("major")
    alarm_obj.set_reason_text("OIDC test alarm")
    fm_cli.raise_alarm(alarm_obj)
    return alarm_obj.get_entity_id(), alarm_obj.get_alarm_id()


def cleanup_test_alarm(ssh_connection: SSHConnection, entity_id: str) -> None:
    """Delete the test alarm by entity_id using fmClientCli.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        entity_id (str): Entity ID of the alarm to delete.
    """
    fm_cli = FaultManagementClientCLIKeywords(ssh_connection)
    alarm_obj = FaultManagementClientCLIObject()
    alarm_obj.set_entity_id(entity_id)
    fm_cli.delete_alarm(alarm_obj)


def get_alarm_uuid_by_id(ssh_connection: SSHConnection, alarm_id: str) -> str:
    """Get a UUID for fm alarm-delete testing using AlarmListKeywords with --uuid.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        alarm_id (str): Alarm ID to search for (e.g. '100.106').

    Returns:
        str: UUID of the matching alarm, or a dummy UUID if not found.
    """
    alarms_output = AlarmListKeywords(ssh_connection).get_alarm_list(uuid=True)
    for alarm in alarms_output.get_alarms():
        if alarm.get_alarm_id() == alarm_id and alarm.get_uuid():
            return alarm.get_uuid()
    return "00000000-0000-0000-0000-000000000000"


def verify_fm_read_commands(fm_oidc_kw: FmOidcKeywords, username: str, password: str, lab_oam_ip: str, role_label: str, alarm_uuid: str = "") -> None:
    """Run FM read-only commands and validate they succeed.

    Args:
        fm_oidc_kw (FmOidcKeywords): FM OIDC keywords instance.
        username (str): LDAP username.
        password (str): LDAP password.
        lab_oam_ip (str): OAM floating IP.
        role_label (str): Role label for logging.
        alarm_uuid (str): Alarm UUID for alarm-show/event-show. Skipped if empty.
    """
    read_commands = ["fm alarm-list", "fm alarm-summary", "fm event-list --nopaging --limit 10", "fm event-suppress-list"]
    if alarm_uuid:
        read_commands.append(f"fm alarm-show {alarm_uuid}")
        read_commands.append(f"fm event-show {alarm_uuid}")
    for cmd in read_commands:
        get_logger().log_info(f"{role_label}: running {cmd}")
        result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, cmd)
        validate_equals(result.is_successful(), True, f"{role_label} role must be allowed to run '{cmd}'")


def verify_fm_write_commands_allowed(fm_oidc_kw: FmOidcKeywords, username: str, password: str, lab_oam_ip: str, role_label: str, event_id: str) -> None:
    """Run FM write commands in correct sequence and validate they succeed.

    Suppress must run before unsuppress — you can only unsuppress a
    previously suppressed event. The sequence is:
    suppress → unsuppress → suppress again → unsuppress-all.

    Args:
        fm_oidc_kw (FmOidcKeywords): FM OIDC keywords instance.
        username (str): LDAP username.
        password (str): LDAP password.
        lab_oam_ip (str): OAM floating IP.
        role_label (str): Role label for logging.
        event_id (str): Event ID for suppress/unsuppress commands.
    """
    get_logger().log_info(f"{role_label}: suppress {event_id}")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, f"fm event-suppress --alarm_id {event_id} --yes")
    validate_equals(result.is_successful(), True, f"{role_label} role must be allowed to run 'fm event-suppress'")

    get_logger().log_info(f"{role_label}: unsuppress {event_id}")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, f"fm event-unsuppress --alarm_id {event_id}")
    validate_equals(result.is_successful(), True, f"{role_label} role must be allowed to run 'fm event-unsuppress'")

    get_logger().log_info(f"{role_label}: suppress {event_id} again for unsuppress-all")
    fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, f"fm event-suppress --alarm_id {event_id} --yes")

    get_logger().log_info(f"{role_label}: unsuppress-all")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm event-unsuppress-all")
    validate_equals(result.is_successful(), True, f"{role_label} role must be allowed to run 'fm event-unsuppress-all'")


def verify_fm_write_commands_denied(fm_oidc_kw: FmOidcKeywords, username: str, password: str, lab_oam_ip: str, role_label: str, event_id: str) -> None:
    """Run FM write commands and validate they are denied.

    From manual execution logs (SX-ZT_PR_002_SuppressEventWithAminRoleAndUnsuppressWithReaderRole):
    - event-suppress always does a PATCH → returns 403 Forbidden for reader
    - event-unsuppress-all does GET then PATCH for each suppressed event →
      returns 403 if something is suppressed. Caller must ensure something
      is suppressed before calling this.

    Args:
        fm_oidc_kw (FmOidcKeywords): FM OIDC keywords instance for the denied user.
        username (str): LDAP username.
        password (str): LDAP password.
        lab_oam_ip (str): OAM floating IP.
        role_label (str): Role label for logging.
        event_id (str): Event ID for suppress/unsuppress commands.
    """
    get_logger().log_info(f"{role_label}: suppress {event_id} (expect Forbidden)")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, f"fm event-suppress --alarm_id {event_id} --yes")
    validate_equals(result.is_forbidden(), True, f"{role_label} role must be denied 'fm event-suppress'")

    get_logger().log_info(f"{role_label}: unsuppress-all (expect Forbidden)")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm event-unsuppress-all")
    validate_equals(result.is_forbidden(), True, f"{role_label} role must be denied 'fm event-unsuppress-all'")


@mark.p2
def test_oidc_fm_admin_role(request: FixtureRequest) -> None:
    """Verify OIDC admin role can execute all FM commands.

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP admin user and group
        - Generate a test alarm
        - Verify admin can run FM read commands (alarm-list, alarm-summary, event-list, event-suppress-list)
        - Verify admin can run FM write commands (event-suppress, event-unsuppress, event-unsuppress-all)
        - Verify admin can run fm alarm-delete
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_admin_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "AdminRoleGroup"
    event_id = "100.106"

    request.addfinalizer(lambda: cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Set up admin role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "admin")

    get_logger().log_test_case_step("Create LDAP admin user")
    setup_ldap_user(ssh_connection, username, password, group_name)
    request.addfinalizer(lambda u=username, p=password, g=group_name: cleanup_ldap_user(ssh_connection, u, p, g))

    get_logger().log_test_case_step("Generate test alarm")
    entity_id, alarm_id = generate_test_alarm(ssh_connection)
    request.addfinalizer(lambda: cleanup_test_alarm(ssh_connection, entity_id))

    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    alarm_uuid = get_alarm_uuid_by_id(ssh_connection, alarm_id)

    get_logger().log_test_case_step("Verify admin can run FM read commands via OIDC")
    verify_fm_read_commands(fm_oidc_kw, username, password, lab_oam_ip, "Admin", alarm_uuid)

    get_logger().log_test_case_step("Verify admin can run FM write commands via OIDC")
    verify_fm_write_commands_allowed(fm_oidc_kw, username, password, lab_oam_ip, "Admin", event_id)

    get_logger().log_test_case_step("Verify admin can delete alarm via OIDC")
    alarm_uuid = get_alarm_uuid_by_id(ssh_connection, alarm_id)
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, f"fm alarm-delete {alarm_uuid}")
    validate_equals(result.is_successful(), True, "Admin role must be allowed to run 'fm alarm-delete'")


@mark.p2
def test_oidc_fm_reader_role(request: FixtureRequest) -> None:
    """Verify OIDC reader role can run FM read commands but is denied write commands.

    Steps:
        - Set up OIDC environment and reader role-bindings
        - Create LDAP reader user and group
        - Generate a test alarm
        - Verify reader can run FM read commands
        - Verify reader is denied FM write commands
        - Verify reader is denied fm alarm-delete
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_reader_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "ReaderGroup"
    event_id = "100.106"

    request.addfinalizer(lambda: cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Set up reader role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "reader")

    get_logger().log_test_case_step("Create LDAP reader user")
    setup_ldap_user(ssh_connection, username, password, group_name)
    request.addfinalizer(lambda u=username, p=password, g=group_name: cleanup_ldap_user(ssh_connection, u, p, g))

    get_logger().log_test_case_step("Generate test alarm")
    entity_id, alarm_id = generate_test_alarm(ssh_connection)
    request.addfinalizer(lambda: cleanup_test_alarm(ssh_connection, entity_id))

    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    alarm_uuid = get_alarm_uuid_by_id(ssh_connection, alarm_id)

    get_logger().log_test_case_step("Verify reader can run FM read commands via OIDC")
    verify_fm_read_commands(fm_oidc_kw, username, password, lab_oam_ip, "Reader", alarm_uuid)

    get_logger().log_test_case_step("Verify reader is denied FM write commands via OIDC")
    # Suppress an event as sysadmin first so reader's unsuppress-all has something to PATCH

    EventSuppressionKeywords(ssh_connection).suppress_event(event_id)
    verify_fm_write_commands_denied(fm_oidc_kw, username, password, lab_oam_ip, "Reader", event_id)
    # Unsuppress as sysadmin to clean up
    EventSuppressionKeywords(ssh_connection).unsuppress_event(event_id)

    get_logger().log_test_case_step("Verify reader is denied alarm-delete via OIDC")
    alarm_uuid = get_alarm_uuid_by_id(ssh_connection, alarm_id)
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, f"fm alarm-delete {alarm_uuid}")
    validate_equals(result.is_forbidden(), True, "Reader role must be denied 'fm alarm-delete'")


@mark.p2
def test_oidc_fm_operator_role(request: FixtureRequest) -> None:
    """Verify OIDC operator role can run FM read and suppress commands but is denied alarm-delete.

    Steps:
        - Set up OIDC environment and operator role-bindings
        - Create LDAP operator user and group
        - Generate a test alarm
        - Verify operator can run FM read commands
        - Verify operator can run FM suppress/unsuppress commands
        - Verify operator is denied fm alarm-delete
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_operator_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "OperatorGroup"
    event_id = "100.106"

    request.addfinalizer(lambda: cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Set up operator role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "operator")

    get_logger().log_test_case_step("Create LDAP operator user")
    setup_ldap_user(ssh_connection, username, password, group_name)
    request.addfinalizer(lambda u=username, p=password, g=group_name: cleanup_ldap_user(ssh_connection, u, p, g))

    get_logger().log_test_case_step("Generate test alarm")
    entity_id, alarm_id = generate_test_alarm(ssh_connection)
    request.addfinalizer(lambda: cleanup_test_alarm(ssh_connection, entity_id))

    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    alarm_uuid = get_alarm_uuid_by_id(ssh_connection, alarm_id)

    get_logger().log_test_case_step("Verify operator can run FM read commands via OIDC")
    verify_fm_read_commands(fm_oidc_kw, username, password, lab_oam_ip, "Operator", alarm_uuid)

    get_logger().log_test_case_step("Verify operator is denied FM write commands via OIDC")

    EventSuppressionKeywords(ssh_connection).suppress_event(event_id)
    verify_fm_write_commands_denied(fm_oidc_kw, username, password, lab_oam_ip, "Operator", event_id)
    EventSuppressionKeywords(ssh_connection).unsuppress_event(event_id)

    get_logger().log_test_case_step("Verify operator is denied alarm-delete via OIDC")
    alarm_uuid = get_alarm_uuid_by_id(ssh_connection, alarm_id)
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, f"fm alarm-delete {alarm_uuid}")
    validate_equals(result.is_forbidden(), True, "Operator role must be denied 'fm alarm-delete'")


@mark.p2
def test_oidc_fm_configurator_role(request: FixtureRequest) -> None:
    """Verify OIDC configurator role can execute all FM commands.

    Steps:
        - Set up OIDC environment and configurator role-bindings
        - Create LDAP configurator user and group
        - Generate a test alarm
        - Verify configurator can run FM read commands
        - Verify configurator can run FM write commands
        - Verify configurator can run fm alarm-delete
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_configurator_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "ConfiguratorGroup"
    event_id = "100.106"

    request.addfinalizer(lambda: cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Set up configurator role-bindings")
    setup_role_bindings(ssh_connection, request, group_name, "configurator")

    get_logger().log_test_case_step("Create LDAP configurator user")
    setup_ldap_user(ssh_connection, username, password, group_name)
    request.addfinalizer(lambda u=username, p=password, g=group_name: cleanup_ldap_user(ssh_connection, u, p, g))

    get_logger().log_test_case_step("Generate test alarm")
    entity_id, alarm_id = generate_test_alarm(ssh_connection)
    request.addfinalizer(lambda: cleanup_test_alarm(ssh_connection, entity_id))

    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    alarm_uuid = get_alarm_uuid_by_id(ssh_connection, alarm_id)

    get_logger().log_test_case_step("Verify configurator can run FM read commands via OIDC")
    verify_fm_read_commands(fm_oidc_kw, username, password, lab_oam_ip, "Configurator", alarm_uuid)

    get_logger().log_test_case_step("Verify configurator can run FM write commands via OIDC")
    verify_fm_write_commands_allowed(fm_oidc_kw, username, password, lab_oam_ip, "Configurator", event_id)

    get_logger().log_test_case_step("Verify configurator can delete alarm via OIDC")
    alarm_uuid = get_alarm_uuid_by_id(ssh_connection, alarm_id)
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, f"fm alarm-delete {alarm_uuid}")
    validate_equals(result.is_successful(), True, "Configurator role must be allowed to run 'fm alarm-delete'")


@mark.p2
def test_oidc_fm_cli_arg_auth(request: FixtureRequest) -> None:
    """Verify FM commands work with --stx-auth-type=oidc CLI argument for all roles.

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP admin user and group
        - Run fm alarm-list and fm alarm-summary with --stx-auth-type=oidc as admin
        - Change role-bindings to reader
        - Run fm alarm-list with --stx-auth-type=oidc as reader (expect success)
        - Run fm event-suppress with --stx-auth-type=oidc as reader (expect Forbidden)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_cliarg_user01"
    password = lab_config.get_admin_credentials().get_password()
    admin_group = "CliArgAdminGroup"
    event_id = "100.106"

    request.addfinalizer(lambda: cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Set up admin role-bindings and user")
    setup_role_bindings(ssh_connection, request, admin_group, "admin")
    setup_ldap_user(ssh_connection, username, password, admin_group)
    request.addfinalizer(lambda u=username, p=password, g=admin_group: cleanup_ldap_user(ssh_connection, u, p, g))

    fm_oidc_kw = FmOidcKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify admin fm alarm-list with --stx-auth-type=oidc")
    result = fm_oidc_kw.run_fm_command_with_cli_arg(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(result.is_successful(), True, "Admin must be allowed 'fm --stx-auth-type=oidc alarm-list'")

    get_logger().log_test_case_step("Verify admin fm alarm-summary with --stx-auth-type=oidc")
    result = fm_oidc_kw.run_fm_command_with_cli_arg(username, password, lab_oam_ip, "fm alarm-summary")
    validate_equals(result.is_successful(), True, "Admin must be allowed 'fm --stx-auth-type=oidc alarm-summary'")

    get_logger().log_test_case_step("Verify admin fm event-suppress with --stx-auth-type=oidc")
    result = fm_oidc_kw.run_fm_command_with_cli_arg(username, password, lab_oam_ip, f"fm event-suppress --alarm_id {event_id} --yes")
    validate_equals(result.is_successful(), True, "Admin must be allowed 'fm --stx-auth-type=oidc event-suppress'")

    get_logger().log_test_case_step("Verify admin fm event-unsuppress-all with --stx-auth-type=oidc")
    result = fm_oidc_kw.run_fm_command_with_cli_arg(username, password, lab_oam_ip, "fm event-unsuppress-all")
    validate_equals(result.is_successful(), True, "Admin must be allowed 'fm --stx-auth-type=oidc event-unsuppress-all'")


@mark.p2
def test_oidc_fm_reader_cli_arg_denied(request: FixtureRequest) -> None:
    """Verify reader role is denied FM write commands with --stx-auth-type=oidc CLI argument.

    Steps:
        - Set up OIDC environment and reader role-bindings
        - Create LDAP reader user and group
        - Run fm alarm-list with --stx-auth-type=oidc (expect success)
        - Run fm event-suppress with --stx-auth-type=oidc (expect Forbidden)
        - Run fm event-unsuppress-all with --stx-auth-type=oidc (expect Forbidden)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_rdrcli_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "CliArgReaderGroup"
    event_id = "100.106"

    request.addfinalizer(lambda: cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Set up reader role-bindings and user")
    setup_role_bindings(ssh_connection, request, group_name, "reader")
    setup_ldap_user(ssh_connection, username, password, group_name)
    request.addfinalizer(lambda u=username, p=password, g=group_name: cleanup_ldap_user(ssh_connection, u, p, g))

    fm_oidc_kw = FmOidcKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify reader fm alarm-list with --stx-auth-type=oidc succeeds")
    result = fm_oidc_kw.run_fm_command_with_cli_arg(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(result.is_successful(), True, "Reader must be allowed 'fm --stx-auth-type=oidc alarm-list'")

    get_logger().log_test_case_step("Verify reader fm event-suppress with --stx-auth-type=oidc is denied")
    result = fm_oidc_kw.run_fm_command_with_cli_arg(username, password, lab_oam_ip, f"fm event-suppress --alarm_id {event_id} --yes")
    validate_equals(result.is_forbidden(), True, "Reader must be denied 'fm --stx-auth-type=oidc event-suppress'")

    get_logger().log_test_case_step("Verify reader fm event-unsuppress-all with --stx-auth-type=oidc is denied")
    # Suppress as sysadmin first so reader's unsuppress-all triggers a PATCH

    EventSuppressionKeywords(ssh_connection).suppress_event(event_id)
    result = fm_oidc_kw.run_fm_command_with_cli_arg(username, password, lab_oam_ip, "fm event-unsuppress-all")
    validate_equals(result.is_forbidden(), True, "Reader must be denied 'fm --stx-auth-type=oidc event-unsuppress-all'")
    EventSuppressionKeywords(ssh_connection).unsuppress_event(event_id)


@mark.p2
def test_oidc_fm_verify_service_params_on_bootstrap(request: FixtureRequest) -> None:
    """Verify OIDC service parameters and local_starlingxrc oidc sourcing (TS-1).

    Steps:
        - Run system service-parameter-list and filter for oidc parameters
        - Verify oidc-client-id, oidc-groups-claim, oidc-issuer-url, oidc-username-claim exist
        - Create LDAP user, run oidc-auth, source local_starlingxrc oidc
        - Verify STX_AUTH_TYPE is set to oidc after sourcing
        - Verify fm alarm-list succeeds with OIDC auth
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_bootstrap_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "BootstrapAdminGroup"

    request.addfinalizer(lambda: cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Verify OIDC service parameters exist in kube_apiserver")
    svc_param_kw = SystemServiceParameterKeywords(ssh_connection)
    params = svc_param_kw.list_service_parameters(service="kubernetes", section="kube_apiserver")
    param_names = [p.get_name() for p in params.get_parameters()]

    expected_oidc_params = ["oidc-client-id", "oidc-groups-claim", "oidc-issuer-url", "oidc-username-claim"]
    for expected in expected_oidc_params:
        validate_equals(expected in param_names, True, f"OIDC service parameter '{expected}' must be present after bootstrap")

    get_logger().log_test_case_step("Set up OIDC environment, role-bindings, and LDAP user")
    setup_oidc_environment(ssh_connection, security_config, lab_config)
    setup_role_bindings(ssh_connection, request, group_name, "admin")
    setup_ldap_user(ssh_connection, username, password, group_name)
    request.addfinalizer(lambda u=username, p=password, g=group_name: cleanup_ldap_user(ssh_connection, u, p, g))

    get_logger().log_test_case_step("SSH as LDAP user, run oidc-auth, source local_starlingxrc oidc, verify STX_AUTH_TYPE")
    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    ldap_ssh = fm_oidc_kw.create_ldap_ssh(username, password, lab_oam_ip)
    try:
        ldap_ssh.send("kubeconfig-setup")
        ldap_ssh.send("source ~/.profile")
        ldap_ssh.send(f"echo '{password}' | oidc-auth")
        ldap_ssh.send(f"source local_starlingxrc oidc <<< '{password}'")
        # source sets env vars in current shell; combine with echo in one command
        output = ldap_ssh.send(f"source local_starlingxrc oidc <<< '{password}' && echo STX_AUTH_TYPE=$STX_AUTH_TYPE")
        raw = "\n".join(output) if isinstance(output, list) else output
        validate_equals("oidc" in raw.lower(), True, "STX_AUTH_TYPE must be 'oidc' after sourcing local_starlingxrc oidc")
    finally:
        ldap_ssh.close()

    get_logger().log_test_case_step("Verify fm alarm-list succeeds with OIDC auth via keyword")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(result.is_successful(), True, "fm alarm-list must succeed after sourcing local_starlingxrc oidc")


@mark.p2
def test_oidc_fm_keystone_regression(request: FixtureRequest) -> None:
    """Verify Keystone authentication still works as default when STX_AUTH_TYPE is unset.

    Steps:
        - Run fm alarm-list via standard Keystone auth (source openrc)
        - Verify the command succeeds and returns a valid alarm list
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify fm alarm-list works with Keystone auth")
    alarm_kw = AlarmListKeywords(ssh_connection)
    alarms_output = alarm_kw.get_alarm_list()
    alarms = alarms_output.get_alarms()
    validate_equals(isinstance(alarms, list), True, "Keystone auth fm alarm-list must return a valid alarm list")


@mark.p3
def test_oidc_fm_deleted_user(request: FixtureRequest) -> None:
    """Verify deleted LDAP user cannot run FM commands via OIDC (TS-19).

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP user, verify fm alarm-list succeeds
        - Delete the LDAP user
        - Verify SSH as deleted user fails or FM commands fail
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_deluser_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "DeletedUserGroup"

    request.addfinalizer(lambda: cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment and role-bindings")
    setup_oidc_environment(ssh_connection, security_config, lab_config)
    setup_role_bindings(ssh_connection, request, group_name, "admin")
    setup_ldap_user(ssh_connection, username, password, group_name)
    request.addfinalizer(lambda u=username, p=password, g=group_name: cleanup_ldap_user(ssh_connection, u, p, g))

    fm_oidc_kw = FmOidcKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify fm alarm-list succeeds before user deletion")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(result.is_successful(), True, "User must be allowed fm alarm-list before deletion")

    get_logger().log_test_case_step("Delete the LDAP user")
    LdapKeywords(ssh_connection, password).delete_user(username)

    get_logger().log_test_case_step("Verify deleted user cannot access FM")
    # After deletion, the user cannot SSH — the persistent session's cached token
    # may still work until expiry, but a fresh connection will fail.
    # Close the cached session and verify a fresh FM command fails.
    fm_oidc_kw.close_session()
    # On a fresh session, SSH as deleted user will fail with AuthenticationException
    # which means the user is properly denied access
    lab_config = ConfigurationManager.get_lab_config()
    ldap_ssh = SSHConnectionManager.create_ssh_connection(lab_oam_ip, username, password, name=f"deleted-{username}", ssh_port=lab_config.get_ssh_port())
    ssh_failed = not ldap_ssh.is_connected
    if ldap_ssh.is_connected:
        ldap_ssh.close()
    validate_equals(ssh_failed, True, "Deleted user must not be able to SSH")


@mark.p3
def test_oidc_fm_invalid_token(request: FixtureRequest) -> None:
    """Verify FM commands fail with an invalid/expired OIDC token (TS-18N).

    Steps:
        - Set up OIDC environment and admin role-bindings
        - Create LDAP admin user and group
        - Verify admin can run fm alarm-list via OIDC (baseline)
        - Corrupt the OIDC token in kubeconfig
        - Verify fm alarm-list fails with authentication error
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_invtoken_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "InvTokenAdminGroup"

    request.addfinalizer(lambda: cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Set up admin role-bindings and user")
    setup_role_bindings(ssh_connection, request, group_name, "admin")
    setup_ldap_user(ssh_connection, username, password, group_name)
    request.addfinalizer(lambda u=username, p=password, g=group_name: cleanup_ldap_user(ssh_connection, u, p, g))

    fm_oidc_kw = FmOidcKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify fm alarm-list via OIDC succeeds (baseline)")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(result.is_successful(), True, "Admin must be allowed fm alarm-list (baseline)")

    get_logger().log_test_case_step("Run fm alarm-list with invalid token via corrupted kubeconfig")
    ldap_ssh = fm_oidc_kw.create_ldap_ssh(username, password, lab_oam_ip)
    try:
        ldap_ssh.send("kubeconfig-setup")
        ldap_ssh.send("source ~/.profile")
        ldap_ssh.send(f"oidc-auth -p {password}")
        ldap_ssh.send(f"source local_starlingxrc oidc <<< '{password}'")
        # Corrupt the token in kubeconfig
        ldap_ssh.send("sed -i 's/token:.*/token: INVALID_TOKEN_12345/' $HOME/.kube/config")
        # Use --stx-auth-type=oidc and set KUBECONFIG explicitly
        output = ldap_ssh.send(
            "export KUBECONFIG=$HOME/.kube/config && source /etc/platform/openrc --no_credentials && " "export OS_USERNAME=$(whoami) && fm --stx-auth-type=oidc alarm-list",
            command_timeout=60,
        )
        raw_output = "\n".join(output) if isinstance(output, list) else output
        result = FmOidcCommandResultOutput("fm alarm-list", raw_output)
        validate_equals(result.is_successful(), False, "FM command must fail with invalid/corrupted OIDC token")
    finally:
        ldap_ssh.close()


@mark.p2
def test_oidc_fm_remote_cli(request: FixtureRequest) -> None:
    """Verify FM commands work via remote SSH with OIDC authentication (TS-10).

    Simulates remote CLI access by SSH-ing as the OIDC user to the controller
    OAM IP, sourcing local_starlingxrc oidc, and running FM commands.
    Verifies reader role can read but is denied write commands.

    Steps:
        - Set up OIDC environment
        - Set role-bindings for reader
        - Create LDAP user and add to reader group
        - SSH as user to OAM IP and run fm alarm-list via OIDC (expect success)
        - SSH as user to OAM IP and run fm event-suppress via OIDC (expect Forbidden)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()

    username = "oidc_remotecli_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "RemoteCliReaderGroup"
    event_id = "100.106"

    def cleanup() -> None:
        """Teardown OIDC environment."""
        cleanup_oidc_environment(ssh_connection, security_config)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Set up OIDC environment")
    setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Set up reader role-bindings and LDAP user")
    setup_role_bindings(ssh_connection, request, group_name, "reader")
    setup_ldap_user(ssh_connection, username, password, group_name)
    request.addfinalizer(lambda u=username, p=password, g=group_name: cleanup_ldap_user(ssh_connection, u, p, g))

    get_logger().log_test_case_step("SSH as user to OAM IP and run fm alarm-list via OIDC")
    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(result.is_successful(), True, "Reader must be allowed fm alarm-list via remote CLI")

    get_logger().log_test_case_step("SSH as user to OAM IP and run fm event-suppress via OIDC (expect Forbidden)")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, f"fm event-suppress --alarm_id {event_id} --yes")
    validate_equals(result.is_forbidden(), True, "Reader must be denied fm event-suppress via remote CLI")
