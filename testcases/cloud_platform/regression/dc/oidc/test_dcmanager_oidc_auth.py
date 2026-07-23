"""Verify dcmanager CLI commands with OIDC authentication for admin and reader roles."""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_config import LabConfig
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_oidc_keywords import DcManagerOidcKeywords
from keywords.cloud_platform.dcmanager.dcmanager_prestage_strategy_keywords import DcmanagerPrestageStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_management_enum import DcManagerSubcloudListManagementEnum
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords


# --- Constants ---

ADMIN_USERNAME = "oidc_dcm_admin01"
READER_USERNAME = "oidc_dcm_reader01"
ADMIN_GROUP = "DcmAdminGroup"
READER_GROUP = "DcmReaderGroup"

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
        emailAttr: uid
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


# --- Setup Helpers ---


def ensure_oidc_environment(ssh_connection: SSHConnection, lab_config: LabConfig) -> None:
    """Ensure OIDC environment is configured and oidc-auth-apps is applied.

    Checks if OIDC pods are already running before performing any setup.
    If pods are healthy, skips the entire helm-override/apply cycle.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        lab_config (LabConfig): Lab configuration object.
    """
    from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
    from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
    from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

    pods_kw = KubectlGetPodsKeywords(ssh_connection)

    # Quick check: are OIDC pods already running?
    pods_output = pods_kw.get_pods(namespace="kube-system")
    oidc_pods = [p for p in pods_output.get_pods() if "oidc-dex" in p.get_name() or "stx-oidc-client" in p.get_name()]
    ready_pods = [p for p in oidc_pods if p.get_status() == "Running"]
    if len(ready_pods) >= 2:
        get_logger().log_info("OIDC pods already running, skipping environment setup")
        return

    # Pods not ready — perform full setup
    get_logger().log_info("OIDC pods not ready, configuring environment")

    from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords

    ldap_admin_pw = KeyringKeywords(ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
    mgmt_ip = SystemAddrpoolListKeywords(ssh_connection).get_system_addrpool_list().get_management_floating_address()
    if ":" in mgmt_ip:
        mgmt_ip = f"[{mgmt_ip}]"

    # Write override files to remote host
    override_content = DEX_LOCAL_LDAP_OVERRIDE.format(ldap_admin_pw=ldap_admin_pw, mgmt_ip=mgmt_ip)
    ssh_connection.send(f"cat > /tmp/dex-dcm-oidc-override.yaml << 'EOFOVERRIDE'\n{override_content}EOFOVERRIDE")
    ssh_connection.send(f"cat > /tmp/oidc-client-dcm-override.yaml << 'EOFOVERRIDE'\n{OIDC_CLIENT_OVERRIDE}EOFOVERRIDE")

    # Apply helm overrides using keyword
    helm_kw = SystemHelmOverrideKeywords(ssh_connection)
    helm_kw.update_helm_override("/tmp/dex-dcm-oidc-override.yaml", "oidc-auth-apps", "dex", "kube-system")
    helm_kw.update_helm_override("/tmp/oidc-client-dcm-override.yaml", "oidc-auth-apps", "oidc-client", "kube-system")

    # Apply the app and wait for applied state
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply("oidc-auth-apps", timeout=300, polling_sleep_time=15)

    # Wait for OIDC pods to be ready
    pods_kw.wait_for_pods_to_reach_status(
        expected_status="Running",
        pod_names=["oidc-dex", "stx-oidc-client"],
        namespace="kube-system",
        timeout=180,
    )


def ensure_ldap_user(ssh_connection: SSHConnection, username: str, password: str, group_name: str) -> None:
    """Create LDAP user and group idempotently.

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


def ensure_role_bindings(ssh_connection: SSHConnection, group_name: str, role: str) -> None:
    """Set up STX role-bindings for the given group via service-parameter.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        group_name (str): LDAP group name.
        role (str): STX role (admin, reader).
    """
    service = "identity"
    section = "stx"
    param_name = "role-bindings"

    role_bindings_map = {
        "admin": f"%{group_name}:admin;%{group_name}:member;%{group_name}:reader",
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

    # Wait for puppet to create the rolebindings config file
    from keywords.files.file_keywords import FileKeywords
    from framework.validation.validation import validate_equals_with_retry

    file_kw = FileKeywords(ssh_connection)
    validate_equals_with_retry(
        function_to_execute=lambda: file_kw.validate_file_exists_with_sudo("/etc/platform/.rolebindings.conf"),
        expected_value=True,
        validation_description="Waiting for /etc/platform/.rolebindings.conf to be created by puppet",
        timeout=60,
        polling_sleep_time=5,
    )


def cleanup_ldap_user(ssh_connection: SSHConnection, username: str, password: str, group_name: str) -> None:
    """Delete LDAP user and group.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        username (str): LDAP username to delete.
        password (str): Password for ansible playbook.
        group_name (str): LDAP group to delete.
    """
    get_logger().log_teardown_step(f"Delete LDAP user '{username}' and group '{group_name}'")
    ldap_kw = LdapKeywords(ssh_connection, password)
    ldap_kw.delete_user(username)
    ldap_kw.delete_group(group_name)


def pick_managed_subcloud() -> tuple:
    """Pick a managed, online subcloud with fallback to secondary SC.

    Returns:
        tuple: (SSHConnection to the owning SC, subcloud name, OAM floating IP of the owning SC).
    """
    from keywords.cloud_platform.system.oam.system_oam_show_keywords import SystemOamShowKeywords

    owner_ssh, result = pick_subcloud_with_fallback(
        management_status=DcManagerSubcloudListManagementEnum.MANAGED,
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
    )
    subcloud_name = result.get_name()
    oam_ip = SystemOamShowKeywords(owner_ssh).oam_show().get_oam_floating_ip()
    get_logger().log_info(f"Selected subcloud '{subcloud_name}' on SC with OAM {oam_ip}")
    return owner_ssh, subcloud_name, oam_ip


# --- Test Cases ---


@mark.p2
@mark.lab_has_subcloud
def test_dcmanager_oidc_subcloud_list_admin(request: FixtureRequest) -> None:
    """Verify OIDC admin can run dcmanager subcloud list.

    Preconditions:
        - System controller is accessible
        - At least one subcloud exists

    Setup:
        - Ensure OIDC environment is configured
        - Ensure LDAP admin user exists with admin role binding

    Test Steps:
        1. Run dcmanager subcloud list as OIDC admin user
        2. Validate output contains subcloud data

    Teardown:
        - Delete LDAP user and group
        - Close OIDC session
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    password = lab_config.get_admin_credentials().get_password()
    lab_oam_ip = lab_config.get_floating_ip()

    dcm_oidc_kw = DcManagerOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: dcm_oidc_kw.close_session())
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, ADMIN_USERNAME, password, ADMIN_GROUP))

    get_logger().log_setup_step("Ensure OIDC environment is configured")
    ensure_oidc_environment(ssh_connection, lab_config)

    get_logger().log_setup_step("Ensure LDAP admin user exists")
    ensure_ldap_user(ssh_connection, ADMIN_USERNAME, password, ADMIN_GROUP)
    ensure_role_bindings(ssh_connection, ADMIN_GROUP, "admin")

    get_logger().log_test_case_step("Run dcmanager subcloud list as OIDC admin")
    oidc_ssh = dcm_oidc_kw.get_authenticated_session(ADMIN_USERNAME, password, lab_oam_ip)
    sc_list_kw = DcManagerSubcloudListKeywords(oidc_ssh, use_oidc=True)
    sc_list_kw.get_dcmanager_subcloud_list()


@mark.p2
@mark.lab_has_subcloud
def test_dcmanager_oidc_subcloud_list_reader(request: FixtureRequest) -> None:
    """Verify OIDC reader can run dcmanager subcloud list.

    Preconditions:
        - System controller is accessible
        - At least one subcloud exists

    Setup:
        - Ensure OIDC environment is configured
        - Ensure LDAP reader user exists with reader role binding

    Test Steps:
        1. Run dcmanager subcloud list as OIDC reader user
        2. Validate output contains subcloud data

    Teardown:
        - Delete LDAP user and group
        - Close OIDC session
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    password = lab_config.get_admin_credentials().get_password()
    lab_oam_ip = lab_config.get_floating_ip()

    dcm_oidc_kw = DcManagerOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: dcm_oidc_kw.close_session())
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, READER_USERNAME, password, READER_GROUP))

    get_logger().log_setup_step("Ensure OIDC environment is configured")
    ensure_oidc_environment(ssh_connection, lab_config)

    get_logger().log_setup_step("Ensure LDAP reader user exists")
    ensure_ldap_user(ssh_connection, READER_USERNAME, password, READER_GROUP)
    ensure_role_bindings(ssh_connection, READER_GROUP, "reader")

    get_logger().log_test_case_step("Run dcmanager subcloud list as OIDC reader")
    oidc_ssh = dcm_oidc_kw.get_authenticated_session(READER_USERNAME, password, lab_oam_ip)
    sc_list_kw = DcManagerSubcloudListKeywords(oidc_ssh, use_oidc=True)
    sc_list_kw.get_dcmanager_subcloud_list()


@mark.p2
@mark.lab_has_subcloud
def test_dcmanager_oidc_subcloud_prestage_admin(request: FixtureRequest) -> None:
    """Verify OIDC admin can run dcmanager subcloud prestage.

    Preconditions:
        - System controller is accessible
        - At least one managed, online subcloud exists

    Setup:
        - Ensure OIDC environment is configured
        - Ensure LDAP admin user exists with admin role binding
        - Pick a managed online subcloud

    Test Steps:
        1. Run dcmanager subcloud prestage on a real subcloud as OIDC admin
        2. Validate prestage is accepted and starts

    Teardown:
        - Delete LDAP user and group
        - Close OIDC session
    """
    ssh_connection, subcloud_name, lab_oam_ip = pick_managed_subcloud()
    lab_config = ConfigurationManager.get_lab_config()
    password = lab_config.get_admin_credentials().get_password()

    dcm_oidc_kw = DcManagerOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: dcm_oidc_kw.close_session())
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, ADMIN_USERNAME, password, ADMIN_GROUP))

    get_logger().log_setup_step("Ensure OIDC environment is configured")
    ensure_oidc_environment(ssh_connection, lab_config)

    get_logger().log_setup_step("Ensure LDAP admin user exists")
    ensure_ldap_user(ssh_connection, ADMIN_USERNAME, password, ADMIN_GROUP)
    ensure_role_bindings(ssh_connection, ADMIN_GROUP, "admin")


    get_logger().log_test_case_step(f"Run dcmanager subcloud prestage on '{subcloud_name}' as OIDC admin")
    oidc_ssh = dcm_oidc_kw.get_authenticated_session(ADMIN_USERNAME, password, lab_oam_ip)
    prestage_kw = DcmanagerSubcloudPrestage(oidc_ssh, use_oidc=True)
    prestage_kw.dcmanager_subcloud_prestage(subcloud_name, password, force=True)


@mark.p2
@mark.lab_has_subcloud
def test_dcmanager_oidc_subcloud_prestage_reader_denied(request: FixtureRequest) -> None:
    """Verify OIDC reader is denied dcmanager subcloud prestage.

    Preconditions:
        - System controller is accessible
        - At least one managed, online subcloud exists

    Setup:
        - Ensure OIDC environment is configured
        - Ensure LDAP reader user exists with reader role binding
        - Pick a managed online subcloud

    Test Steps:
        1. Run dcmanager subcloud prestage as OIDC reader
        2. Validate command is forbidden

    Teardown:
        - Delete LDAP user and group
        - Close OIDC session
    """
    ssh_connection, subcloud_name, lab_oam_ip = pick_managed_subcloud()
    lab_config = ConfigurationManager.get_lab_config()
    password = lab_config.get_admin_credentials().get_password()

    dcm_oidc_kw = DcManagerOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: dcm_oidc_kw.close_session())
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, READER_USERNAME, password, READER_GROUP))

    get_logger().log_setup_step("Ensure OIDC environment is configured")
    ensure_oidc_environment(ssh_connection, lab_config)

    get_logger().log_setup_step("Ensure LDAP reader user exists")
    ensure_ldap_user(ssh_connection, READER_USERNAME, password, READER_GROUP)
    ensure_role_bindings(ssh_connection, READER_GROUP, "reader")

    get_logger().log_test_case_step(f"Run dcmanager subcloud prestage on '{subcloud_name}' as OIDC reader (expect denied)")
    oidc_ssh = dcm_oidc_kw.get_authenticated_session(READER_USERNAME, password, lab_oam_ip)
    prestage_kw = DcmanagerSubcloudPrestage(oidc_ssh, use_oidc=True)
    error_output = prestage_kw.dcmanager_subcloud_prestage_with_error(subcloud_name, password, force=True)
    validate_str_contains(error_output, "Forbidden", "Reader OIDC prestage must be denied with Forbidden")


@mark.p2
@mark.lab_has_subcloud
def test_dcmanager_oidc_backup_create_admin(request: FixtureRequest) -> None:
    """Verify OIDC admin can run dcmanager subcloud-backup create.

    Preconditions:
        - System controller is accessible
        - At least one managed, online subcloud exists

    Setup:
        - Ensure OIDC environment is configured
        - Ensure LDAP admin user exists with admin role binding
        - Pick a managed online subcloud

    Test Steps:
        1. Run dcmanager subcloud-backup create on a real subcloud as OIDC admin
        2. Validate command is accepted

    Teardown:
        - Delete LDAP user and group
        - Close OIDC session
    """
    ssh_connection, subcloud_name, lab_oam_ip = pick_managed_subcloud()
    lab_config = ConfigurationManager.get_lab_config()
    password = lab_config.get_admin_credentials().get_password()

    dcm_oidc_kw = DcManagerOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: dcm_oidc_kw.close_session())
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, ADMIN_USERNAME, password, ADMIN_GROUP))

    get_logger().log_setup_step("Ensure OIDC environment is configured")
    ensure_oidc_environment(ssh_connection, lab_config)

    get_logger().log_setup_step("Ensure LDAP admin user exists")
    ensure_ldap_user(ssh_connection, ADMIN_USERNAME, password, ADMIN_GROUP)
    ensure_role_bindings(ssh_connection, ADMIN_GROUP, "admin")


    get_logger().log_test_case_step(f"Run dcmanager subcloud-backup create on '{subcloud_name}' as OIDC admin")
    oidc_ssh = dcm_oidc_kw.get_authenticated_session(ADMIN_USERNAME, password, lab_oam_ip)
    backup_kw = DcManagerSubcloudBackupKeywords(oidc_ssh, use_oidc=True)
    backup_kw.create_subcloud_backup(sysadmin_password=password, con_ssh=oidc_ssh, subcloud=subcloud_name, local_only=True)


@mark.p2
@mark.lab_has_subcloud
def test_dcmanager_oidc_prestage_strategy_for_install_admin(request: FixtureRequest) -> None:
    """Verify OIDC admin can run prestage-strategy for-install.

    Follows the same pattern as test_prestage_strategy_single_subcloud.py:
    create → apply → validate complete → delete.

    Preconditions:
        - System controller is accessible
        - At least one managed, online subcloud exists

    Setup:
        - Ensure OIDC environment is configured
        - Ensure LDAP admin user exists with admin role binding
        - Pick a managed online subcloud

    Test Steps:
        1. Create prestage-strategy (for-install) as OIDC admin
        2. Apply the strategy
        3. Validate strategy completes
        4. Delete the strategy

    Teardown:
        - Delete prestage-strategy if still present
        - Delete LDAP user and group
        - Close OIDC session
    """
    ssh_connection, subcloud_name, lab_oam_ip = pick_managed_subcloud()
    lab_config = ConfigurationManager.get_lab_config()
    password = lab_config.get_admin_credentials().get_password()

    dcm_oidc_kw = DcManagerOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: dcm_oidc_kw.close_session())
    request.addfinalizer(lambda: cleanup_ldap_user(ssh_connection, ADMIN_USERNAME, password, ADMIN_GROUP))

    get_logger().log_setup_step("Ensure OIDC environment is configured")
    ensure_oidc_environment(ssh_connection, lab_config)

    get_logger().log_setup_step("Ensure LDAP admin user exists")
    ensure_ldap_user(ssh_connection, ADMIN_USERNAME, password, ADMIN_GROUP)
    ensure_role_bindings(ssh_connection, ADMIN_GROUP, "admin")


    get_logger().log_test_case_step("Authenticate as OIDC admin")
    oidc_ssh = dcm_oidc_kw.get_authenticated_session(ADMIN_USERNAME, password, lab_oam_ip)

    strategy_kw = DcmanagerPrestageStrategyKeywords(oidc_ssh, use_oidc=True)
    cleanup_kw = DcmanagerStrategyCleanupKeywords(oidc_ssh, use_oidc=True)
    request.addfinalizer(lambda: cleanup_kw.cleanup_strategy("prestage"))

    get_logger().log_test_case_step(f"Create prestage-strategy for-install targeting '{subcloud_name}'")
    strategy_kw.get_dcmanager_prestage_strategy_create(sw_deploy=False, subcloud_name=subcloud_name)

    get_logger().log_test_case_step("Apply prestage-strategy")
    result = strategy_kw.get_dcmanager_prestage_strategy_apply()
    validate_equals(result.get_state(), "complete", "Prestage strategy must complete successfully via OIDC admin")

    get_logger().log_test_case_step("Delete prestage-strategy")
    strategy_kw.get_dcmanager_prestage_strategy_delete()
