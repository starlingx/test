"""WAD (Windows Active Directory) OIDC connector tests — attribute mappings and E2E auth.

Tests the WAD DEX connector emailAttr, usernameAttr, and nameAttr mappings,
validates end-to-end OIDC authentication with oidc-username-claim via
service-parameter CLI, and verifies access-denied scenarios for WAD users.
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
from keywords.cloud_platform.security.oidc.object.oidc_token_claims_object import OidcTokenClaimsObject
from keywords.cloud_platform.security.oidc.wad_connector_keywords import WadConnectorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
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


def _get_wad_test_user_config() -> dict:
    """Load WAD test user configuration.

    Returns:
        dict: WAD test user config with username, password, email, crb_name.
    """
    return _load_dex_config()["wad_test_user"]


def _get_wad_connector_config() -> dict:
    """Load WAD connector configuration.

    Returns:
        dict: WAD connector config with email_attr, username_attr, name_attr.
    """
    return _load_dex_config()["wad_connector"]


def _create_wad_ssh(username: str, password: str, oam_ip: str) -> SSHConnection:
    """Create SSH session as WAD user and authenticate via oidc-auth.

    Args:
        username (str): WAD username.
        password (str): WAD password.
        oam_ip (str): Lab OAM IP.

    Returns:
        SSHConnection: Authenticated SSH session.
    """
    wad_ssh = SSHConnectionManager.create_ssh_connection(oam_ip, username, password)
    wad_ssh.connect()
    wad_ssh.send("kubeconfig-setup")
    wad_ssh.send("source ~/.profile")
    wad_ssh.send(f"oidc-auth -p {password}")
    return wad_ssh


def _verify_kubectl_and_stx_access(wad_ssh: SSHConnection, expect_success: bool = True) -> None:
    """Verify kubectl and STX platform access for the authenticated WAD user.

    Args:
        wad_ssh (SSHConnection): Authenticated WAD SSH session.
        expect_success (bool): Whether access should succeed.
    """
    wad_ssh.send("kubectl get pods -A")
    rc = wad_ssh.get_return_code()
    if expect_success:
        validate_equals(rc, 0, "kubectl should succeed for authenticated WAD user")
    else:
        validate_equals(rc != 0, True, "kubectl should be denied for WAD user")

    wad_ssh.send(source_openrc("system host-list"))
    stx_rc = wad_ssh.get_return_code()
    if expect_success:
        validate_equals(stx_rc, 0, "system host-list should succeed for OIDC-authenticated user")
    else:
        validate_equals(stx_rc != 0, True, "system host-list should be denied for WAD user")


def _decode_id_token(wad_ssh: SSHConnection) -> OidcTokenClaimsObject:
    """Decode cached token using DexConnectorKeywords.

    Args:
        wad_ssh (SSHConnection): Authenticated SSH session with cached token.

    Returns:
        OidcTokenClaimsObject: Parsed token claims.
    """
    dex = DexConnectorKeywords(wad_ssh)
    return dex.decode_cached_token()


# =============================================================================
# WAD Connector Attribute Mapping Tests (TC 6-7)
# =============================================================================


@mark.p0
@mark.lab_has_standby_controller
def test_wad_corrected_email_attr_mapping(request):
    """TC6: Verify WAD emailAttr=mail produces correct email claim in token.

    Test Steps:
        - Apply WAD override with emailAttr=mail
        - Authenticate WAD user via oidc-auth
        - Decode ID token and verify email claim matches real email
    """
    config = _load_dex_config()
    wad_config = _get_wad_connector_config()
    wad_user = _get_wad_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info(f"Applying WAD override with emailAttr={wad_config['email_attr']}")
    wad_keywords = WadConnectorKeywords(ssh_connection)
    wad_keywords.apply_wad_override(
        config=config,
        email_attr=wad_config["email_attr"],
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )

    get_logger().log_info("Authenticating WAD user and decoding token")
    wad_ssh = _create_wad_ssh(wad_user["username"], wad_user["password"], oam_ip)
    claims = _decode_id_token(wad_ssh)
    wad_ssh.close()

    validate_equals(claims.get_email(), wad_user["email"], "Token email claim should match WAD user's mail attribute")


@mark.p1
@mark.lab_has_standby_controller
def test_wad_username_and_name_attr_mapping(request):
    """TC7: Verify WAD usernameAttr=sAMAccountName, nameAttr=displayName in token.

    Test Steps:
        - Apply WAD override with usernameAttr=sAMAccountName, nameAttr=displayName
        - Authenticate WAD user via oidc-auth
        - Decode ID token and verify preferred_username and name claims
    """
    config = _load_dex_config()
    wad_config = _get_wad_connector_config()
    wad_user = _get_wad_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info(f"Applying WAD override: usernameAttr={wad_config['username_attr']}, " f"nameAttr={wad_config['name_attr']}")
    wad_keywords = WadConnectorKeywords(ssh_connection)
    wad_keywords.apply_wad_override(
        config=config,
        email_attr=wad_config["email_attr"],
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )

    get_logger().log_info("Authenticating WAD user and decoding token")
    wad_ssh = _create_wad_ssh(wad_user["username"], wad_user["password"], oam_ip)
    claims = _decode_id_token(wad_ssh)
    wad_ssh.close()

    validate_equals(claims.get_preferred_username(), wad_user["username"], "Token preferred_username should match WAD sAMAccountName")
    validate_equals(claims.has_name(), True, "Token should contain name claim from displayName mapping")


# =============================================================================
# WAD Connector E2E Access Tests (TC 8-9, 35)
# =============================================================================


@mark.p0
@mark.lab_has_standby_controller
def test_wad_access_with_preferred_username_claim(request):
    """TC8: Verify K8s access with WAD + oidc-username-claim=preferred_username.

    Test Steps:
        - Apply WAD attr mappings (usernameAttr=sAMAccountName)
        - Set oidc-username-claim=preferred_username
        - Create CRB by WAD username
        - Authenticate WAD user, verify kubectl access succeeds
    """
    config = _load_dex_config()
    wad_config = _get_wad_connector_config()
    wad_user = _get_wad_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    dex_keywords = DexConnectorKeywords(ssh_connection)
    wad_keywords = WadConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(wad_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    wad_keywords.apply_wad_override(
        config=config,
        email_attr=wad_config["email_attr"],
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    crb_keywords.create_clusterrolebinding_for_user(wad_user["crb_name"], "cluster-admin", wad_user["username"])

    get_logger().log_info("SSH as WAD user, oidc-auth, verify kubectl")
    wad_ssh = _create_wad_ssh(wad_user["username"], wad_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(wad_ssh, expect_success=True)
    wad_ssh.close()


@mark.p0
@mark.lab_has_standby_controller
def test_wad_access_with_email_claim(request):
    """TC9: Verify K8s access with WAD + oidc-username-claim=email.

    Test Steps:
        - Apply WAD attr mappings (emailAttr=mail)
        - Set oidc-username-claim=email
        - Create CRB by WAD user email
        - Authenticate WAD user, verify kubectl access succeeds
    """
    config = _load_dex_config()
    wad_config = _get_wad_connector_config()
    wad_user = _get_wad_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    dex_keywords = DexConnectorKeywords(ssh_connection)
    wad_keywords = WadConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(wad_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    wad_keywords.apply_wad_override(
        config=config,
        email_attr=wad_config["email_attr"],
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(wad_user["crb_name"], "cluster-admin", wad_user["email"])

    get_logger().log_info("SSH as WAD user, oidc-auth, verify kubectl with email CRB")
    wad_ssh = _create_wad_ssh(wad_user["username"], wad_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(wad_ssh, expect_success=True)
    wad_ssh.close()


@mark.p0
@mark.lab_has_standby_controller
def test_wad_access_denied_no_mail_with_email_claim(request):
    """TC35: Verify K8s access denied when WAD user has no mail attr and claim=email.

    Test Steps:
        - Apply WAD attr mappings (emailAttr=mail)
        - Set oidc-username-claim=email
        - Create CRB by email
        - Authenticate WAD user WITHOUT mail attribute, verify kubectl denied
    """
    config = _load_dex_config()
    wad_config = _get_wad_connector_config()
    wad_user = _get_wad_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    dex_keywords = DexConnectorKeywords(ssh_connection)
    wad_keywords = WadConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(wad_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    wad_keywords.apply_wad_override(
        config=config,
        email_attr=wad_config["email_attr"],
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(wad_user["crb_name"], "cluster-admin", wad_user["email"])

    get_logger().log_info("Attempting kubectl — should fail (WAD user without mail, claim=email)")
    wad_ssh = _create_wad_ssh(wad_user["username"], wad_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(wad_ssh, expect_success=False)
    wad_ssh.close()


# =============================================================================
# WAD Negative / Cross-Connector Tests (TC 36)
# =============================================================================


@mark.p1
@mark.lab_has_standby_controller
def test_username_collision_across_ldap_and_wad(request):
    """TC36: Verify username collision when same username exists in LDAP and WAD.

    Demonstrates why email-based identity is preferred for uniqueness.
    With oidc-username-claim=preferred_username, both LDAP and WAD users
    with the same username match the same CRB — no identity isolation.

    Test Steps:
        - Create LDAP user with username matching WAD test user
        - Configure both LDAP and WAD connectors
        - Set oidc-username-claim=preferred_username
        - Create CRB by username
        - Auth from LDAP — access succeeds
        - Auth from WAD — access also succeeds (same username, no isolation)
    """
    config = _load_dex_config()
    test_user = config["test_user"]
    wad_config = _get_wad_connector_config()
    wad_user = _get_wad_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    ldap_keywords = LdapKeywords(ssh_connection, security_config.get_domain_name())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    wad_keywords = WadConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    crb_name = "collision-test-crb"

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        sec_config = ConfigurationManager.get_security_config()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(crb_name)
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        LdapKeywords(ssh, sec_config.get_domain_name()).delete_user(test_user["username"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info("Creating LDAP user with same username pattern as WAD user")
    ldap_keywords.create_user(test_user["username"], test_user["password"], user_role=test_user["role"])

    get_logger().log_info("Applying WAD connector override")
    wad_keywords.apply_wad_override(
        config=config,
        email_attr=wad_config["email_attr"],
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )

    get_logger().log_info("Setting oidc-username-claim=preferred_username")
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    crb_keywords.create_clusterrolebinding_for_user(crb_name, "cluster-admin", test_user["username"])

    get_logger().log_info("Auth from LDAP — should succeed")
    ldap_ssh = _create_wad_ssh(test_user["username"], test_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(ldap_ssh, expect_success=True)
    ldap_ssh.close()

    get_logger().log_info("Auth from WAD with same username — also succeeds (no isolation)")
    wad_ssh = _create_wad_ssh(wad_user["username"], wad_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(wad_ssh, expect_success=True)
    wad_ssh.close()
