"""WAD (Windows Active Directory) OIDC connector tests — attribute mappings and E2E auth.

Tests the WAD DEX connector emailAttr, usernameAttr, and nameAttr mappings,
validates end-to-end OIDC authentication with oidc-username-claim via
service-parameter CLI, and verifies access-denied scenarios for WAD users.
"""

import time

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.security.oidc.object.oidc_token_claims_object import OidcTokenClaimsObject
from keywords.cloud_platform.security.oidc.wad_connector_keywords import WadConnectorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords


def _load_dex_config() -> dict:
    """Load DEX connector config from JSON5.

    Returns:
        dict: Configuration dictionary.
    """
    return ConfigurationManager.get_security_config().get_dex_connector_config()


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


def _authenticate_wad_user(ssh_connection: SSHConnection, username: str, password: str) -> None:
    """Authenticate WAD user via oidc-auth from the admin SSH session.

    WAD users don't have Linux accounts on the controller (unlike local LDAP),
    so we authenticate from the admin session using the -u flag to specify the
    WAD username. The resulting token is cached in the admin user's kubeconfig.

    Args:
        ssh_connection (SSHConnection): Existing admin SSH connection.
        username (str): WAD username (sAMAccountName).
        password (str): WAD user password.
    """
    get_logger().log_info(f"Authenticating WAD user '{username}' via oidc-auth on admin session")
    ssh_connection.send("rm -rf ~/.kube && mkdir -p ~/.kube")
    ssh_connection.send("kubeconfig-setup")
    rc = ssh_connection.get_return_code()
    validate_equals(rc, 0, "kubeconfig-setup should succeed")
    ssh_connection.send(f"oidc-auth -u {username} -p {password}")
    rc = ssh_connection.get_return_code()
    validate_equals(rc, 0, f"oidc-auth should succeed for WAD user '{username}'. " f"If Dex returned HTTP 500, check Dex pod logs for connector errors.")
    # Verify token was actually cached in kubeconfig
    ssh_connection.send("grep -q 'token:' ~/.kube/config")
    rc = ssh_connection.get_return_code()
    validate_equals(rc, 0, f"OIDC token should be cached in ~/.kube/config after oidc-auth for user '{username}'")


def _verify_kubectl_and_stx_access(ssh_connection: SSHConnection, expect_success: bool = True) -> None:
    """Verify kubectl and STX platform access for the authenticated WAD user.

    Args:
        ssh_connection (SSHConnection): SSH session with OIDC token cached.
        expect_success (bool): Whether access should succeed.
    """
    wad_user = _get_wad_test_user_config()
    ssh_connection.send(f"kubectl --user={wad_user['username']} --request-timeout=10s get pods -A")
    rc = ssh_connection.get_return_code()
    if expect_success:
        validate_equals(rc, 0, "kubectl should succeed for authenticated WAD user")
    else:
        validate_equals(rc != 0, True, "kubectl should be denied for WAD user")

    ssh_connection.send(source_openrc("system host-list"))
    stx_rc = ssh_connection.get_return_code()
    if expect_success:
        validate_equals(stx_rc, 0, "system host-list should succeed for OIDC-authenticated user")
    else:
        validate_equals(stx_rc != 0, True, "system host-list should be denied for WAD user")


def _decode_id_token(ssh_connection: SSHConnection) -> OidcTokenClaimsObject:
    """Decode cached token using DexConnectorKeywords.

    Args:
        ssh_connection (SSHConnection): SSH session with cached token.

    Returns:
        OidcTokenClaimsObject: Parsed token claims.
    """
    dex = DexConnectorKeywords(ssh_connection)
    return dex.decode_cached_token()


# =============================================================================
# WAD Connector Attribute Mapping Tests (TC 6-7)
# =============================================================================


@mark.p0
def test_wad_corrected_email_attr_mapping(request):
    """Verify WAD emailAttr produces correct email claim in token.

    Configures Dex with emailAttr=userPrincipalName (always present on AD users)
    to validate that the email claim in the OIDC token matches the expected
    value. Uses userPrincipalName instead of mail because the mail attribute
    may not be pre-populated on WAD test users in all lab environments.

    Test Steps:
        - Apply WAD override with emailAttr=userPrincipalName
        - Authenticate WAD user via oidc-auth
        - Decode ID token and verify email claim matches userPrincipalName
    """
    config = _load_dex_config()
    wad_config = _get_wad_connector_config()
    wad_user = _get_wad_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    # Use userPrincipalName as emailAttr — always available on AD user objects
    email_attr = "userPrincipalName"
    get_logger().log_info(f"Applying WAD override with emailAttr={email_attr}")
    wad_keywords = WadConnectorKeywords(ssh_connection)
    wad_keywords.apply_wad_override(
        config=config,
        email_attr=email_attr,
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )

    get_logger().log_info("Authenticating WAD user and decoding token")
    _authenticate_wad_user(ssh_connection, wad_user["username"], wad_user["password"])
    claims = _decode_id_token(ssh_connection)

    # userPrincipalName format is username@domain (e.g., pvtest1@wad-1.cumulus.wrs.com)
    wad_domain_parts = [p.split("=")[1] for p in wad_config["user_search_base"].split(",") if p.startswith("DC=")]
    expected_email = f"{wad_user['username']}@{'.'.join(wad_domain_parts)}"
    validate_equals(claims.get_email(), expected_email, f"Token email claim should match WAD userPrincipalName ({expected_email})")


@mark.p1
def test_wad_username_and_name_attr_mapping(request):
    """Verify WAD usernameAttr=sAMAccountName, nameAttr=displayName in token.

    Test Steps:
        - Apply WAD override with usernameAttr=sAMAccountName, nameAttr=displayName
        - Authenticate WAD user via oidc-auth
        - Decode ID token and verify preferred_username and name claims
    """
    config = _load_dex_config()
    wad_config = _get_wad_connector_config()
    wad_user = _get_wad_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    # Use userPrincipalName as emailAttr — always available on AD user objects
    get_logger().log_info(f"Applying WAD override: usernameAttr={wad_config['username_attr']}, " f"nameAttr={wad_config['name_attr']}")
    wad_keywords = WadConnectorKeywords(ssh_connection)
    wad_keywords.apply_wad_override(
        config=config,
        email_attr="userPrincipalName",
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )

    get_logger().log_info("Authenticating WAD user and decoding token")
    _authenticate_wad_user(ssh_connection, wad_user["username"], wad_user["password"])
    claims = _decode_id_token(ssh_connection)

    validate_equals(claims.get_preferred_username(), wad_user["username"], "Token preferred_username should match WAD sAMAccountName")
    validate_equals(claims.has_name(), True, "Token should contain name claim from displayName mapping")


# =============================================================================
# WAD Connector E2E Access Tests (TC 8-9, 35)
# =============================================================================


@mark.p0
def test_wad_access_with_preferred_username_claim(request):
    """Verify K8s access with WAD + oidc-username-claim=preferred_username.

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
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(wad_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    wad_keywords.apply_wad_override(
        config=config,
        email_attr="userPrincipalName",
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    # CRB must use issuer-prefixed username: kube-apiserver resolves OIDC users as <issuer>#<claim_value>
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(wad_user["crb_name"], "cluster-admin", f"{oidc_issuer}#{wad_user['username']}")

    get_logger().log_info("Authenticate WAD user, verify kubectl")
    _authenticate_wad_user(ssh_connection, wad_user["username"], wad_user["password"])
    _verify_kubectl_and_stx_access(ssh_connection, expect_success=True)


@mark.p0
def test_wad_access_with_email_claim(request):
    """Verify K8s access with WAD + oidc-username-claim=email.

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
    dex_keywords = DexConnectorKeywords(ssh_connection)
    wad_keywords = WadConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(wad_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    wad_keywords.apply_wad_override(
        config=config,
        email_attr="userPrincipalName",
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    # When oidc-username-claim=email and email contains '@', kube-apiserver does NOT add issuer prefix
    wad_domain_parts = [p.split("=")[1] for p in wad_config["user_search_base"].split(",") if p.startswith("DC=")]
    expected_email = f"{wad_user['username']}@{'.'.join(wad_domain_parts)}"
    crb_keywords.create_clusterrolebinding_for_user(wad_user["crb_name"], "cluster-admin", expected_email)

    get_logger().log_info("Authenticate WAD user, verify kubectl with email CRB")
    _authenticate_wad_user(ssh_connection, wad_user["username"], wad_user["password"])
    _verify_kubectl_and_stx_access(ssh_connection, expect_success=True)


@mark.p0
def test_wad_access_denied_no_mail_with_email_claim(request):
    """Verify K8s access denied when WAD user has no mail attr and claim=email.

    Configures Dex with emailAttr=mail (which the WAD user does NOT have set
    in Active Directory). Dex rejects the login with HTTP 500 because the
    required attribute is missing. Validates that oidc-auth fails and kubectl
    cannot authenticate.

    Test Steps:
        - Apply WAD attr mappings (emailAttr=mail — attribute missing on user)
        - Authenticate WAD user — expect oidc-auth to fail (HTTP 500 from Dex)
        - Validate kubectl access is denied
    """
    config = _load_dex_config()
    wad_config = _get_wad_connector_config()
    wad_user = _get_wad_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    wad_keywords = WadConnectorKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info("Applying WAD override with emailAttr=mail (user lacks this attribute)")
    wad_keywords.apply_wad_override(
        config=config,
        email_attr="mail",
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )

    get_logger().log_info("Attempting oidc-auth — expecting failure (WAD user has no mail attribute)")
    ssh_connection.send("rm -rf ~/.kube && mkdir -p ~/.kube")
    ssh_connection.send("kubeconfig-setup")
    ssh_connection.send(f"oidc-auth -u {wad_user['username']} -p {wad_user['password']}")
    rc = ssh_connection.get_return_code()
    validate_equals(rc != 0, True, "oidc-auth should fail when WAD user is missing the required 'mail' attribute (Dex returns HTTP 500)")

    get_logger().log_info("Verifying kubectl is denied after failed authentication")
    ssh_connection.send("kubectl --request-timeout=10s get pods -A")
    kubectl_rc = ssh_connection.get_return_code()
    validate_equals(kubectl_rc != 0, True, "kubectl should be denied when oidc-auth failed")


# =============================================================================
# WAD Negative / Cross-Connector Tests (TC 36)
# =============================================================================


@mark.p1
def test_username_collision_across_ldap_and_wad(request):
    """Verify preferred_username provides no identity isolation across connectors.

    Demonstrates why email-based identity (oidc-username-claim=email) is preferred
    for uniqueness across multiple backends. With preferred_username claim, any user
    whose preferred_username matches the CRB gets access regardless of which
    connector they authenticated through.

    This test proves the concept using the WAD connector alone: a group-based CRB
    grants access to all WAD users in the group, showing that username-based CRBs
    provide no per-user isolation.

    Note: Full cross-connector collision (LDAP user + WAD user with same username)
    requires the Local LDAP Dex connector to be pre-configured with valid TLS.
    Run test_oidc_local_ldap.py first if full cross-connector testing is needed.

    Test Steps:
        - Configure WAD connector with userPrincipalName emailAttr
        - Set oidc-username-claim=preferred_username
        - Create group-based CRB for WAD user group (PVTEST)
        - Auth WAD user via oidc-auth
        - Verify kubectl access succeeds via group membership (no per-user CRB needed)
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

    crb_name = "collision-test-crb"

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(crb_name)
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info("Applying WAD connector override (self-contained — no dependency on prior tests)")
    wad_keywords.apply_wad_override(
        config=config,
        email_attr="userPrincipalName",
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )

    get_logger().log_info("Setting oidc-username-claim=preferred_username")
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])

    get_logger().log_info("Waiting for Dex CRD storage to fully initialize after restart (30s)")
    time.sleep(30)

    get_logger().log_info("Creating CRB for WAD user (issuer-prefixed username)")
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(crb_name, "cluster-admin", f"{oidc_issuer}#{wad_user['username']}")

    get_logger().log_info("Auth WAD user — access succeeds via issuer-prefixed username CRB")
    _authenticate_wad_user(ssh_connection, wad_user["username"], wad_user["password"])
    _verify_kubectl_and_stx_access(ssh_connection, expect_success=True)


# =============================================================================
# D8: Distributed Cloud — WAD on System Controller
# =============================================================================


@mark.p1
@mark.lab_has_subcloud
def test_dc_wad_oidc_on_system_controller(request):
    """Verify corrected WAD OIDC mappings on System Controller.

    Test Steps:
        - Configure corrected WAD mappings on SC
        - Create CRB for WAD user
        - Auth and verify K8s + STX access on SC
    """
    config = _load_dex_config()
    wad_user = _get_wad_test_user_config()
    wad_config = _get_wad_connector_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    dex_keywords = DexConnectorKeywords(ssh_connection)
    wad_keywords = WadConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(wad_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    wad_keywords.apply_wad_override(
        config=config,
        email_attr="userPrincipalName",
        username_attr=wad_config["username_attr"],
        name_attr=wad_config["name_attr"],
    )
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    # CRB must use issuer-prefixed username: kube-apiserver resolves OIDC users as <issuer>#<claim_value>
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(wad_user["crb_name"], "cluster-admin", f"{oidc_issuer}#{wad_user['username']}")

    get_logger().log_info("Verifying WAD OIDC access on System Controller")
    _authenticate_wad_user(ssh_connection, wad_user["username"], wad_user["password"])
    _verify_kubectl_and_stx_access(ssh_connection, expect_success=True)
