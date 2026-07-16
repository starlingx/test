"""Local LDAP OIDC connector tests — attribute mappings, E2E auth, negative, HA.

Tests the recommended emailAttr, nameAttr, and usernameAttr mappings
for the Local LDAP DEX connector, validates oidc-username-claim via
service-parameter CLI, and verifies end-to-end OIDC authentication
including negative cases and HA scenarios.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords


def _load_dex_config() -> dict:
    """Load DEX connector config from SecurityConfig via ConfigurationManager.

    Returns:
        dict: Configuration dictionary.
    """
    return ConfigurationManager.get_security_config().get_dex_connector_config()


def _get_test_user_config() -> dict:
    """Load test user configuration.

    Returns:
        dict: Test user config with username, password, email, crb_name.
    """
    return _load_dex_config()["test_user"]


def _configure_subcloud_oidc_params(
    subcloud_ssh: SSHConnection,
    oidc_issuer_url: str,
    username_claim: str,
) -> None:
    """Configure OIDC service parameters on subcloud for centralized DC auth.

    Args:
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.
        oidc_issuer_url (str): SC's dex issuer URL.
        username_claim (str): OIDC username claim value.
    """
    service_params = SystemServiceParameterKeywords(subcloud_ssh)
    oidc_params = {
        "oidc-issuer-url": oidc_issuer_url,
        "oidc-client-id": "stx-oidc-client-app",
        "oidc-username-claim": username_claim,
        "oidc-groups-claim": "groups",
    }
    for param_name, param_value in oidc_params.items():
        try:
            service_params.add_service_parameter("kubernetes", "kube_apiserver", param_name, param_value)
        except AssertionError:
            service_params.modify_service_parameter("kubernetes", "kube_apiserver", param_name, param_value)
    service_params.apply_service_parameters("kubernetes")

    get_logger().log_info("Waiting for subcloud kube-apiserver to restart with OIDC parameters")
    DexConnectorKeywords(subcloud_ssh)._wait_for_all_apiservers_ready(timeout=120)


def _apply_ldap_attr_override(ssh_connection: SSHConnection, config: dict, email_attr: str, name_attr: str) -> None:
    """Generate and apply LDAP override with specified attribute mappings.

    Args:
        ssh_connection (SSHConnection): Active controller SSH.
        config (dict): DEX connector configuration.
        email_attr (str): emailAttr value.
        name_attr (str): nameAttr value.
    """
    yaml_keywords = YamlKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    dex_keywords = DexConnectorKeywords(ssh_connection)

    working_dir = config["working_dir"]
    file_keywords.create_directory(working_dir)

    template = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-ldap-attr-mapping-overrides.yaml")
    mgmt_ip = SystemAddrpoolListKeywords(ssh_connection).get_system_addrpool_list().get_management_floating_address()
    if ":" in mgmt_ip:
        mgmt_ip = f"[{mgmt_ip}]"
    replacements = {
        "mgmt_ip": mgmt_ip,
        "bind_pw": KeyringKeywords(ssh_connection).get_keyring(service="ldap", identifier="ldapadmin"),
        "email_attr": email_attr,
        "name_attr": name_attr,
    }
    override_file = yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-ldap-attr-test.yaml", working_dir)
    dex_keywords.apply_dex_override_and_reapply(override_file, config["oidc_app_name"], config["namespace"])


def _create_ldap_ssh(username: str, password: str, oam_ip: str, backend: str = "", client_ip: str = "") -> SSHConnection:
    """Create SSH session as LDAP user and authenticate via oidc-auth.

    Args:
        username (str): LDAP username.
        password (str): LDAP password.
        oam_ip (str): Lab OAM IP to SSH into.
        backend (str): Dex connector backend ID (e.g., 'ldap-1'). Required when multiple backends exist.
        client_ip (str): OIDC client IP override (e.g., SC OAM for centralized DC). Uses local OAM if empty.

    Returns:
        SSHConnection: Authenticated SSH session.
    """
    ldap_ssh = SSHConnectionManager.create_ssh_connection(oam_ip, username, password)
    ldap_ssh.connect()
    ldap_ssh.send("rm -rf ~/.kube && mkdir -p ~/.kube")
    ldap_ssh.send("kubeconfig-setup")
    ldap_ssh.send("source ~/.profile")
    backend_flag = f" -b {backend}" if backend else ""
    client_flag = f" -c {client_ip}" if client_ip else ""
    ldap_ssh.send(f"oidc-auth -p {password}{backend_flag}{client_flag}")
    return ldap_ssh


def _verify_kubectl_and_stx_access(ldap_ssh: SSHConnection, expect_success: bool = True, expected_email: str = "", expected_username: str = "") -> None:
    """Verify kubectl, STX platform access, and token claims for the authenticated LDAP user.

    Args:
        ldap_ssh (SSHConnection): Authenticated LDAP SSH session.
        expect_success (bool): Whether access should succeed.
        expected_email (str): If set, verify email claim matches this value.
        expected_username (str): If set, verify preferred_username claim matches this value.
    """
    if expect_success:
        ldap_ssh.send("kubectl get pods -A --request-timeout=30s")
    else:
        # Use shorter timeout for negative tests
        ldap_ssh.send("kubectl get pods -A --request-timeout=10s")
    rc = ldap_ssh.get_return_code()
    if expect_success:
        validate_equals(rc, 0, "kubectl should succeed for authenticated LDAP user")
    else:
        validate_equals(rc != 0, True, "kubectl should be denied")
        return

    output = ldap_ssh.send(source_openrc("system host-list"))
    raw = "\n".join(output) if isinstance(output, list) else str(output)
    validate_str_contains(raw, "controller", "system host-list should succeed for OIDC-authenticated user")

    # Decode token and verify claims match expected attribute mappings
    if expected_email or expected_username:
        dex_keywords = DexConnectorKeywords(ldap_ssh)
        claims = dex_keywords.decode_cached_token()
        if expected_email:
            validate_equals(claims.get_email(), expected_email, f"ID token email claim should be '{expected_email}'")
        if expected_username:
            validate_equals(claims.get_preferred_username(), expected_username, f"ID token preferred_username claim should be '{expected_username}'")


# =============================================================================
# D1: Attribute Mapping + Service Parameter Tests
# =============================================================================


@mark.p1
def test_local_ldap_recommended_attr_mappings(request):
    """Test recommended emailAttr/nameAttr for Local LDAP connector.

    Test Steps:
        - Apply DEX override with emailAttr=mail, nameAttr=gecos
        - Reapply oidc-auth-apps
        - Verify helm-override-show contains the recommended mappings
    """
    config = _load_dex_config()
    ldap = config["local_ldap"]
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info(f"Applying Local LDAP attrs: emailAttr={ldap['email_attr']}, nameAttr={ldap['name_attr']}")
    _apply_ldap_attr_override(ssh_connection, config, ldap["email_attr"], ldap["name_attr"])

    dex_keywords = DexConnectorKeywords(ssh_connection)
    dex_keywords.helm_override_keywords.verify_helm_user_override(ldap["email_attr"], config["oidc_app_name"], "dex", config["namespace"])
    dex_keywords.helm_override_keywords.verify_helm_user_override(ldap["name_attr"], config["oidc_app_name"], "dex", config["namespace"])


@mark.p1
def test_oidc_username_claim_set_via_service_parameter(request):
    """Test oidc-username-claim modification via service-parameter CLI.

    Test Steps:
        - Set oidc-username-claim to 'preferred_username', verify
        - Set oidc-username-claim to 'email', verify
        - Restore to 'preferred_username'
    """
    config = _load_dex_config()
    claim = config["oidc_username_claim"]
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dex_keywords = DexConnectorKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        service_param_kw = SystemServiceParameterKeywords(ssh)
        service_param_kw.modify_service_parameter("kubernetes", "kube_apiserver", "oidc-username-claim", claim["default"])

    request.addfinalizer(cleanup)

    get_logger().log_info("Setting oidc-username-claim='preferred_username'")
    dex_keywords.set_oidc_username_claim(claim["default"])
    validate_equals(dex_keywords.get_oidc_username_claim(), claim["default"], "Claim should be 'preferred_username'")

    get_logger().log_info("Setting oidc-username-claim='email'")
    dex_keywords.set_oidc_username_claim(claim["alternative"])
    validate_equals(dex_keywords.get_oidc_username_claim(), claim["alternative"], "Claim should be 'email'")


@mark.p2
def test_oidc_username_claim_default_is_preferred_username():
    """Test default bootstrap oidc-username-claim is 'preferred_username'.

    Test Steps:
        - Query current oidc-username-claim service parameter
        - Verify value is 'preferred_username'
    """
    config = _load_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dex_keywords = DexConnectorKeywords(ssh_connection)

    current = dex_keywords.get_oidc_username_claim()
    validate_equals(current, config["oidc_username_claim"]["default"], "Default oidc-username-claim should be 'preferred_username'")


# =============================================================================
# D2: E2E Local LDAP Authentication Tests
# =============================================================================


@mark.p0
def test_ldap_user_mail_attribute_setup(request):
    """Verify LDAP user can be created with mail attribute.

    Test Steps:
        - Create LDAP user via playbook
        - Add mail attribute via ldapmodify
        - Verify mail attribute via ldapsearch
    """
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step(f"Deleting LDAP user: {test_user['username']}")
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])

    request.addfinalizer(cleanup)

    get_logger().log_info(f"Creating LDAP user: {test_user['username']} (role={test_user['role']})")
    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])

    get_logger().log_info(f"Adding mail attribute '{test_user['email']}' to user '{test_user['username']}'")
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])

    get_logger().log_info("Verifying mail attribute via ldapsearch")
    mail = ldap_keywords.verify_mail_attribute(test_user["username"])
    validate_equals(mail, test_user["email"], "LDAP user should have mail attribute set")


@mark.p0
def test_ldap_access_with_preferred_username_claim(request):
    """Verify K8s access with Local LDAP + oidc-username-claim=preferred_username.

    Test Steps:
        - Create LDAP user with mail attribute
        - Apply corrected LDAP attr mappings
        - Set oidc-username-claim=preferred_username
        - Create CRB by username
        - SSH as LDAP user, oidc-auth, kubectl — should succeed
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    # CRB must use issuer-prefixed username: kube-apiserver resolves OIDC users as <issuer>#<claim_value>
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", f"{oidc_issuer}#{test_user['username']}")

    get_logger().log_info("SSH as LDAP user, oidc-auth, verify kubectl")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True, expected_username=test_user["username"], expected_email=test_user["email"])
    ldap_ssh.close()


@mark.p0
def test_ldap_access_with_email_claim(request):
    """Verify K8s access with Local LDAP + oidc-username-claim=email.

    Test Steps:
        - Create LDAP user with mail attribute
        - Apply corrected LDAP attr mappings (emailAttr=mail)
        - Set oidc-username-claim=email
        - Create CRB by email address
        - SSH as LDAP user, oidc-auth, kubectl — should succeed
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", test_user["email"])

    get_logger().log_info("SSH as LDAP user, oidc-auth, verify kubectl with email CRB")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True, expected_email=test_user["email"], expected_username=test_user["username"])
    ldap_ssh.close()


# =============================================================================
# D3: Negative / Error Tests
# =============================================================================


@mark.p0
def test_ldap_access_denied_no_mail_with_email_claim(request):
    """Verify K8s access denied when LDAP user has no mail attr and claim=email.

    Test Steps:
        - Create LDAP user WITHOUT mail attribute
        - Set oidc-username-claim=email, CRB by email
        - SSH as LDAP user, oidc-auth, kubectl — should be denied
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", test_user["email"])

    get_logger().log_info("Attempting kubectl — should fail (no mail attr, claim=email)")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=False)
    ldap_ssh.close()


@mark.p0
def test_ldap_access_denied_crb_mismatch(request):
    """Verify access denied when CRB is by username but claim=email.

    Test Steps:
        - Create LDAP user with mail
        - Set oidc-username-claim=email, CRB by USERNAME (mismatch)
        - SSH as LDAP user, oidc-auth, kubectl — should be denied
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", test_user["username"])

    get_logger().log_info("Attempting kubectl — should fail (CRB by username, claim=email)")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=False)
    ldap_ssh.close()


@mark.p1
def test_ldap_invalid_email_attr_graceful(request):
    """Verify app applies gracefully with invalid emailAttr field.

    Test Steps:
        - Configure emailAttr=nonExistentField
        - Apply oidc-auth-apps — should not crash
    """
    config = _load_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dex_keywords = DexConnectorKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        _apply_ldap_attr_override(ssh, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    _apply_ldap_attr_override(ssh_connection, config, "nonExistentField", config["local_ldap"]["name_attr"])
    dex_keywords.helm_override_keywords.verify_helm_user_override("nonExistentField", config["oidc_app_name"], "dex", config["namespace"])


@mark.p1
def test_ldap_invalid_name_attr_graceful(request):
    """Verify app applies gracefully with invalid nameAttr field.

    Test Steps:
        - Configure nameAttr=nonExistentField
        - Apply oidc-auth-apps — should not crash
    """
    config = _load_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dex_keywords = DexConnectorKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        _apply_ldap_attr_override(ssh, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], "nonExistentField")
    dex_keywords.helm_override_keywords.verify_helm_user_override("nonExistentField", config["oidc_app_name"], "dex", config["namespace"])


@mark.p1
def test_ldap_switch_claim_invalidates_old_crb(request):
    """Verify switching oidc-username-claim invalidates existing CRB.

    Test Steps:
        - Set claim=preferred_username, CRB by username, verify access
        - Switch to claim=email — old CRB should be invalid
        - Create new CRB by email, verify access restored
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])

    get_logger().log_info("Verify access with preferred_username claim")
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", f"{oidc_issuer}#{test_user['username']}")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()

    get_logger().log_info("Switch to email claim — old CRB should fail")
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=False)
    ldap_ssh.close()

    get_logger().log_info("Create CRB by email — access should be restored")
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", test_user["email"])
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()


# =============================================================================
# D4: HA Tests (Swact + Reboot)
# =============================================================================


@mark.p0
@mark.lab_has_standby_controller
def test_ldap_oidc_access_after_swact(request):
    """Verify OIDC access works after controller swact.

    Test Steps:
        - Configure LDAP mappings, verify access
        - Swact controller
        - Re-verify K8s access
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", f"{oidc_issuer}#{test_user['username']}")

    get_logger().log_info("Verifying access before swact")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()

    get_logger().log_info("Performing controller swact")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    SystemHostSwactKeywords(ssh_connection).host_swact()

    get_logger().log_info("Waiting for Dex to recover after swact")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    DexConnectorKeywords(ssh_connection).wait_for_dex_ready()

    get_logger().log_info("Re-verifying access after swact")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()


# =============================================================================
# D4: HA (Ungraceful Reboot) + Cross-Backend Identity Isolation
# =============================================================================


@mark.p1
@mark.lab_has_standby_controller
def test_ldap_oidc_access_after_ungraceful_reboot(request):
    """Verify OIDC access after ungraceful active controller reboot.

    Test Steps:
        - Configure LDAP mappings, verify access
        - Force reboot active controller
        - Wait for recovery
        - Re-verify K8s and STX access
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()
    active_host = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", f"{oidc_issuer}#{test_user['username']}")

    get_logger().log_info("Verifying access before reboot")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()

    get_logger().log_info(f"Force rebooting active controller: {active_host}")
    prev_uptime = SystemHostListKeywords(ssh_connection).get_uptime(active_host)
    reboot_ssh = LabConnectionKeywords().get_ssh_for_hostname(active_host)
    SystemHostRebootKeywords(reboot_ssh).host_force_reboot()

    get_logger().log_info("Waiting for controller recovery after force reboot")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    reboot_keywords = SystemHostRebootKeywords(ssh_connection)
    validate_equals(
        reboot_keywords.wait_for_force_reboot(active_host, prev_uptime),
        True,
        f"{active_host} should recover after force reboot",
    )

    get_logger().log_info("Verifying OIDC pods are ready after reboot")
    kubectl_wait = KubectlWaitPodKeywords(ssh_connection)
    kubectl_wait.wait_for_pods_ready("app=dex", config["namespace"])
    DexConnectorKeywords(ssh_connection).wait_for_dex_ready()

    get_logger().log_info("Re-verifying OIDC access after ungraceful reboot")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()


@mark.p1
@mark.lab_has_standby_controller
def test_email_identity_isolation_across_ldap_and_wad(request):
    """Verify email-based identity isolation across LDAP and WAD backends.

    With oidc-username-claim=email, users from different backends get different
    email identities in their tokens and RBAC correctly isolates access.
    Local LDAP uses emailAttr=mail so the user gets their mail attribute as
    identity. WAD uses emailAttr=sAMAccountName (WAD users lack a mail attr)
    so the WAD user gets their sAMAccountName as email identity. CRB bound
    to the LDAP user email does NOT grant access to the WAD user.

    Test Steps:
        - Create LDAP user with mail=user@ldap.local
        - Configure combined LDAP + WAD connector override
          (LDAP emailAttr=mail, WAD emailAttr=sAMAccountName)
        - Set oidc-username-claim=email
        - Create CRB by LDAP user email only
        - Auth from LDAP backend — access succeeds (email matches CRB)
        - Auth from WAD backend — access denied (WAD email=sAMAccountName != LDAP email)
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    wad_user = config["wad_test_user"]
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()
    crb_name = "email-isolation-crb"

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(crb_name)
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info("Creating LDAP user with mail attribute")
    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])

    get_logger().log_info("Applying combined LDAP + WAD connector override")
    wad_config = config["wad_connector"]
    file_keywords = FileKeywords(ssh_connection)
    yaml_keywords = YamlKeywords(ssh_connection)
    file_keywords.create_directory(config["working_dir"])
    mgmt_ip = SystemAddrpoolListKeywords(ssh_connection).get_system_addrpool_list().get_management_floating_address()
    if ":" in mgmt_ip:
        mgmt_ip = f"[{mgmt_ip}]"
    ldap_bind_pw = KeyringKeywords(ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
    template = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-ldap-wad-combined-overrides.yaml")
    replacements = {
        "mgmt_ip": mgmt_ip,
        "bind_pw": ldap_bind_pw,
        "email_attr": config["local_ldap"]["email_attr"],
        "name_attr": config["local_ldap"]["name_attr"],
        "wad_server": wad_config["wad_server"],
        "wad_bind_dn": wad_config["bind_dn"],
        "wad_bind_pw": wad_config["bind_pw"],
        "wad_user_search_base": wad_config["user_search_base"],
        "wad_group_search_base": wad_config["group_search_base"],
        "wad_email_attr": wad_config["email_attr"],
        "wad_username_attr": wad_config["username_attr"],
        "wad_name_attr": wad_config["name_attr"],
    }
    override_file = yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-ldap-wad-combined.yaml", config["working_dir"], preserve_order=True)
    dex_keywords.apply_dex_override_and_reapply(override_file, config["oidc_app_name"], config["namespace"])

    get_logger().log_info("Setting oidc-username-claim=email and creating CRB by LDAP email only")
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(crb_name, "cluster-admin", test_user["email"])

    get_logger().log_info("Auth from LDAP — should succeed (email matches CRB)")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip, backend="ldap-1")
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()

    get_logger().log_info("Auth from WAD — should be denied (WAD email identity != LDAP email in CRB)")
    ssh_connection.send("rm -rf ~/.kube && mkdir -p ~/.kube")
    ssh_connection.send("kubeconfig-setup")
    ssh_connection.send("source ~/.profile")
    # Use timeout around oidc-auth to prevent hang if Dex auth flow stalls
    ssh_connection.send(f"timeout 30 oidc-auth -u {wad_user['username']} -p {wad_user['password']} -b RemoteWAD")
    # Use timeout to prevent kubectl hang when token is invalid or missing
    ssh_connection.send("timeout 15 kubectl get pods -A 2>&1")
    wad_rc = ssh_connection.get_return_code()
    validate_equals(wad_rc != 0, True, "kubectl should be denied for WAD user (no CRB for WAD email identity)")


# =============================================================================
# D5: Bootstrap Validation Tests
# =============================================================================


@mark.p0
def test_bootstrap_default_oidc_username_claim():
    """Verify default bootstrap uses oidc-username-claim=preferred_username.

    Test Steps:
        - Query oidc-username-claim service parameter
        - Verify value is 'preferred_username'
        - Verify dex helm overrides have corrected emailAttr/nameAttr
    """
    config = _load_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dex_keywords = DexConnectorKeywords(ssh_connection)

    get_logger().log_info("Verifying default oidc-username-claim=preferred_username")
    current_claim = dex_keywords.get_oidc_username_claim()
    validate_equals(current_claim, config["oidc_username_claim"]["default"], "Default oidc-username-claim should be 'preferred_username'")

    get_logger().log_info("Verifying corrected emailAttr in helm overrides")
    dex_keywords.helm_override_keywords.verify_helm_user_override(config["local_ldap"]["email_attr"], config["oidc_app_name"], "dex", config["namespace"])
    dex_keywords.helm_override_keywords.verify_helm_user_override(config["local_ldap"]["name_attr"], config["oidc_app_name"], "dex", config["namespace"])


# =============================================================================
# D8: Distributed Cloud Tests
# =============================================================================


@mark.p0
@mark.lab_has_subcloud
def test_dc_ldap_oidc_on_system_controller(request):
    """Verify corrected OIDC mappings on System Controller.

    Test Steps:
        - Configure corrected LDAP mappings on SC
        - Apply oidc-auth-apps
        - Auth and verify K8s + STX access on SC
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        LdapKeywords(ssh, ConfigurationManager.get_lab_config().get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", f"{oidc_issuer}#{test_user['username']}")

    get_logger().log_info("Verifying OIDC access on System Controller")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()


@mark.p0
@mark.lab_has_subcloud
def test_dc_ldap_oidc_on_subcloud(request):
    """Verify centralized OIDC auth on subcloud via System Controller's dex.

    Test Steps:
        - Create LDAP user on SC and apply dex LDAP override
        - Configure subcloud oidc-issuer-url pointing to SC's dex
        - Create CRB and verify OIDC access on subcloud
    """
    config = _load_dex_config()
    test_user = _get_test_user_config()
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name = lab_config.get_subcloud_names()[0]

    sc_ssh = LabConnectionKeywords().get_active_controller_ssh()
    ldap_keywords = LdapKeywords(sc_ssh, lab_config.get_admin_credentials().get_password())
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(subcloud_ssh)

    subcloud_oam_ip = lab_config.get_subcloud(subcloud_name).get_floating_ip()
    sc_oam_ip = lab_config.get_floating_ip()
    bracketed_sc_oam = f"[{sc_oam_ip}]" if ":" in sc_oam_ip else sc_oam_ip
    sc_oidc_issuer = f"https://{bracketed_sc_oam}:30556/dex"

    def cleanup():
        get_logger().log_teardown_step("Cleaning up test resources")
        cleanup_sc_ssh = LabConnectionKeywords().get_active_controller_ssh()
        cleanup_sub_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        KubectlCreateClusterRoleBindingKeywords(cleanup_sub_ssh).delete_clusterrolebinding(test_user["crb_name"])
        LdapKeywords(cleanup_sc_ssh, lab_config.get_admin_credentials().get_password()).delete_user(test_user["username"])
        FileKeywords(cleanup_sc_ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Creating LDAP user on System Controller")
    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])

    get_logger().log_test_case_step("Applying dex LDAP override on System Controller")
    _apply_ldap_attr_override(sc_ssh, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    DexConnectorKeywords(sc_ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])

    get_logger().log_test_case_step("Configuring subcloud OIDC issuer to point to SC's dex")
    _configure_subcloud_oidc_params(subcloud_ssh, sc_oidc_issuer, config["oidc_username_claim"]["default"])

    get_logger().log_test_case_step("Creating CRB on subcloud")
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", f"{sc_oidc_issuer}#{test_user['username']}")

    get_logger().log_test_case_step("Verifying OIDC access on subcloud")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], subcloud_oam_ip, client_ip=sc_oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()
