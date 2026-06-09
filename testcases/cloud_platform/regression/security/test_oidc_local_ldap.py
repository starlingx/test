"""Local LDAP OIDC connector tests — attribute mappings, E2E auth, negative, HA.

Tests the recommended emailAttr, nameAttr, and usernameAttr mappings
for the Local LDAP DEX connector, validates oidc-username-claim via
service-parameter CLI, and verifies end-to-end OIDC authentication
including negative cases and HA scenarios.
"""

import json5
from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords


def _load_dex_config() -> dict:
    """Load DEX connector config from JSON5.

    Returns:
        dict: Configuration dictionary.
    """
    path = get_stx_resource_path("config/security/files/dex_connector_config.json5")
    with open(path) as f:
        return json5.load(f)["dex_connector"]


def _get_test_user_config() -> dict:
    """Load test user configuration.

    Returns:
        dict: Test user config with username, password, email, crb_name.
    """
    return _load_dex_config()["test_user"]


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
    lab_config = ConfigurationManager.get_lab_config()

    working_dir = config["working_dir"]
    file_keywords.create_directory(working_dir)

    template = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-ldap-attr-mapping-overrides.yaml")
    replacements = {
        "mgmt_ip": lab_config.get_management_ip(),
        "bind_pw": ConfigurationManager.get_security_config().get_domain_name(),
        "email_attr": email_attr,
        "name_attr": name_attr,
    }
    override_file = yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-ldap-attr-test.yaml", working_dir)
    dex_keywords.apply_dex_override_and_reapply(override_file, config["oidc_app_name"], config["namespace"])


def _create_ldap_ssh(username: str, password: str, oam_ip: str) -> SSHConnection:
    """Create SSH session as LDAP user and authenticate via oidc-auth.

    Args:
        username (str): LDAP username.
        password (str): LDAP password.
        oam_ip (str): Lab OAM IP.

    Returns:
        SSHConnection: Authenticated SSH session.
    """
    ldap_ssh = SSHConnectionManager.create_ssh_connection(oam_ip, username, password)
    ldap_ssh.connect()
    ldap_ssh.send("kubeconfig-setup")
    ldap_ssh.send("source ~/.profile")
    ldap_ssh.send(f"oidc-auth -p {password}")
    return ldap_ssh


def _verify_kubectl_and_stx_access(ldap_ssh: SSHConnection, expect_success: bool = True) -> None:
    """Verify kubectl and STX platform access for the authenticated LDAP user.

    Args:
        ldap_ssh (SSHConnection): Authenticated LDAP SSH session.
        expect_success (bool): Whether access should succeed.
    """
    ldap_ssh.send("kubectl get pods -A")
    rc = ldap_ssh.get_return_code()
    if expect_success:
        validate_equals(rc, 0, "kubectl should succeed for authenticated LDAP user")
    else:
        validate_equals(rc != 0, True, "kubectl should be denied")

    ldap_ssh.send(source_openrc("system host-list"))
    stx_rc = ldap_ssh.get_return_code()
    if expect_success:
        validate_equals(stx_rc, 0, "system host-list should succeed for OIDC-authenticated user")
    else:
        validate_equals(stx_rc != 0, True, "system host-list should be denied")


# =============================================================================
# D1: Attribute Mapping + Service Parameter Tests
# =============================================================================


@mark.p1
@mark.lab_has_standby_controller
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
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info(f"Applying Local LDAP attrs: emailAttr={ldap['email_attr']}, nameAttr={ldap['name_attr']}")
    _apply_ldap_attr_override(ssh_connection, config, ldap["email_attr"], ldap["name_attr"])

    dex_keywords = DexConnectorKeywords(ssh_connection)
    dex_keywords.helm_override_keywords.verify_helm_user_override(ldap["email_attr"], config["oidc_app_name"], "dex", config["namespace"])
    dex_keywords.helm_override_keywords.verify_helm_user_override(ldap["name_attr"], config["oidc_app_name"], "dex", config["namespace"])


@mark.p1
@mark.lab_has_standby_controller
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
        DexConnectorKeywords(ssh).set_oidc_username_claim(claim["default"])

    request.addfinalizer(cleanup)

    get_logger().log_info("Setting oidc-username-claim='preferred_username'")
    dex_keywords.set_oidc_username_claim(claim["default"])
    validate_equals(dex_keywords.get_oidc_username_claim(), claim["default"], "Claim should be 'preferred_username'")

    get_logger().log_info("Setting oidc-username-claim='email'")
    dex_keywords.set_oidc_username_claim(claim["alternative"])
    validate_equals(dex_keywords.get_oidc_username_claim(), claim["alternative"], "Claim should be 'email'")


@mark.p2
@mark.lab_has_standby_controller
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
@mark.lab_has_standby_controller
def test_ldap_user_mail_attribute_setup(request):
    """Verify LDAP user can be created with mail attribute.

    Test Steps:
        - Create LDAP user via playbook
        - Add mail attribute via ldapmodify
        - Verify mail attribute via ldapsearch
    """
    test_user = _get_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    ldap_keywords = LdapKeywords(ssh_connection, security_config.get_domain_name())

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        sec_config = ConfigurationManager.get_security_config()
        LdapKeywords(ssh, sec_config.get_domain_name()).delete_user(test_user["username"])

    request.addfinalizer(cleanup)

    get_logger().log_info(f"Creating LDAP user: {test_user['username']}")
    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])

    get_logger().log_info(f"Adding mail attribute: {test_user['email']}")
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])

    get_logger().log_info("Verifying mail attribute via ldapsearch")
    mail = ldap_keywords.verify_mail_attribute(test_user["username"])
    validate_equals(mail, test_user["email"], "LDAP user should have mail attribute set")


@mark.p0
@mark.lab_has_standby_controller
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
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, security_config.get_domain_name())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        sec_config = ConfigurationManager.get_security_config()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        LdapKeywords(ssh, sec_config.get_domain_name()).delete_user(test_user["username"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", test_user["username"])

    get_logger().log_info("SSH as LDAP user, oidc-auth, verify kubectl")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()


@mark.p0
@mark.lab_has_standby_controller
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
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, security_config.get_domain_name())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        sec_config = ConfigurationManager.get_security_config()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, sec_config.get_domain_name()).delete_user(test_user["username"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", test_user["email"])

    get_logger().log_info("SSH as LDAP user, oidc-auth, verify kubectl with email CRB")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()


# =============================================================================
# D3: Negative / Error Tests
# =============================================================================


@mark.p0
@mark.lab_has_standby_controller
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
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, security_config.get_domain_name())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        sec_config = ConfigurationManager.get_security_config()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, sec_config.get_domain_name()).delete_user(test_user["username"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

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
@mark.lab_has_standby_controller
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
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, security_config.get_domain_name())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        sec_config = ConfigurationManager.get_security_config()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, sec_config.get_domain_name()).delete_user(test_user["username"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

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
@mark.lab_has_standby_controller
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
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    _apply_ldap_attr_override(ssh_connection, config, "nonExistentField", config["local_ldap"]["name_attr"])
    dex_keywords.helm_override_keywords.verify_helm_user_override("nonExistentField", config["oidc_app_name"], "dex", config["namespace"])


@mark.p1
@mark.lab_has_standby_controller
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
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], "nonExistentField")
    dex_keywords.helm_override_keywords.verify_helm_user_override("nonExistentField", config["oidc_app_name"], "dex", config["namespace"])


@mark.p1
@mark.lab_has_standby_controller
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
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, security_config.get_domain_name())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        sec_config = ConfigurationManager.get_security_config()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, sec_config.get_domain_name()).delete_user(test_user["username"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])

    get_logger().log_info("Verify access with preferred_username claim")
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", test_user["username"])
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
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, security_config.get_domain_name())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        sec_config = ConfigurationManager.get_security_config()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user["crb_name"])
        LdapKeywords(ssh, sec_config.get_domain_name()).delete_user(test_user["username"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])
    ldap_keywords.add_mail_attribute(test_user["username"], test_user["email"])
    _apply_ldap_attr_override(ssh_connection, config, config["local_ldap"]["email_attr"], config["local_ldap"]["name_attr"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    crb_keywords.create_clusterrolebinding_for_user(test_user["crb_name"], "cluster-admin", test_user["username"])

    get_logger().log_info("Verifying access before swact")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()

    get_logger().log_info("Performing controller swact")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    SystemHostSwactKeywords(ssh_connection).host_swact()

    get_logger().log_info("Re-verifying access after swact")
    ldap_ssh = _create_ldap_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()
