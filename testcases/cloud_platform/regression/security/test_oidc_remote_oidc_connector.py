"""Remote OIDC (Keycloak) connector tests — claim mappings and E2E auth.

Tests the Remote OIDC DEX connector claimMapping configuration,
validates end-to-end OIDC authentication via Keycloak with
oidc-username-claim via service-parameter CLI, and verifies
access using preferred_username and email claims.
"""

import json

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
from keywords.cloud_platform.security.oidc.remote_oidc_connector_keywords import RemoteOidcConnectorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords


def _load_dex_config() -> dict:
    """Load DEX connector config from JSON5.

    Returns:
        dict: Configuration dictionary.
    """
    path = get_stx_resource_path("config/security/files/dex_connector_config.json5")
    with open(path) as f:
        return json5.load(f)["dex_connector"]


def _get_keycloak_test_user_config() -> dict:
    """Load Keycloak test user configuration.

    Returns:
        dict: Keycloak test user config with username, password, email, crb_name, realm.
    """
    return _load_dex_config()["keycloak_test_user"]


def _get_remote_oidc_config() -> dict:
    """Load Remote OIDC connector configuration.

    Returns:
        dict: Remote OIDC config with issuer_url, client_id, client_secret, claim_mapping.
    """
    return _load_dex_config()["remote_oidc"]


def _create_keycloak_ssh(username: str, password: str, oam_ip: str) -> SSHConnection:
    """Create SSH session as Keycloak user and authenticate via oidc-auth.

    Args:
        username (str): Keycloak username.
        password (str): Keycloak password.
        oam_ip (str): Lab OAM IP.

    Returns:
        SSHConnection: Authenticated SSH session.
    """
    kc_ssh = SSHConnectionManager.create_ssh_connection(oam_ip, username, password)
    kc_ssh.connect()
    kc_ssh.send("kubeconfig-setup")
    kc_ssh.send("source ~/.profile")
    kc_ssh.send(f"oidc-auth -p {password}")
    return kc_ssh


def _verify_kubectl_and_stx_access(kc_ssh: SSHConnection, expect_success: bool = True) -> None:
    """Verify kubectl and STX platform access for the authenticated Keycloak user.

    Args:
        kc_ssh (SSHConnection): Authenticated Keycloak SSH session.
        expect_success (bool): Whether access should succeed.
    """
    kc_ssh.send("kubectl get pods -A")
    rc = kc_ssh.get_return_code()
    if expect_success:
        validate_equals(rc, 0, "kubectl should succeed for authenticated Keycloak user")
    else:
        validate_equals(rc != 0, True, "kubectl should be denied for Keycloak user")

    kc_ssh.send(source_openrc("system host-list"))
    stx_rc = kc_ssh.get_return_code()
    if expect_success:
        validate_equals(stx_rc, 0, "system host-list should succeed for OIDC-authenticated user")
    else:
        validate_equals(stx_rc != 0, True, "system host-list should be denied for Keycloak user")


def _decode_id_token(ssh_connection: SSHConnection) -> dict:
    """Decode the current OIDC ID token and return claims as dict.

    Args:
        ssh_connection (SSHConnection): SSH session with cached token.

    Returns:
        dict: Decoded token claims.
    """
    ssh_connection.send("cat ~/.kube/oidc-login/id-token | " "cut -d'.' -f2 | base64 -d 2>/dev/null")
    output = ssh_connection.get_output()
    return json.loads(output)


# =============================================================================
# Remote OIDC Connector Claim Mapping Tests (TC 10)
# =============================================================================


@mark.p0
@mark.lab_has_standby_controller
def test_remote_oidc_claim_mapping(request):
    """TC10: Verify Remote OIDC claimMapping produces correct claims in token.

    Test Steps:
        - Apply Remote OIDC connector override with claimMapping
        - Authenticate Keycloak user via oidc-auth
        - Decode ID token and verify email, name, preferred_username claims
    """
    config = _load_dex_config()
    oidc_config = _get_remote_oidc_config()
    kc_user = _get_keycloak_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info(f"Applying Remote OIDC override with claimMapping: {oidc_config['claim_mapping']}")
    oidc_keywords = RemoteOidcConnectorKeywords(ssh_connection)
    oidc_keywords.apply_remote_oidc_override(config=config, claim_mapping=oidc_config["claim_mapping"])

    get_logger().log_info("Authenticating Keycloak user and decoding token")
    kc_ssh = _create_keycloak_ssh(kc_user["username"], kc_user["password"], oam_ip)
    claims = _decode_id_token(kc_ssh)
    kc_ssh.close()

    validate_equals(claims.get("email"), kc_user["email"], "Token email claim should match Keycloak user email")
    validate_equals(claims.get("preferred_username"), kc_user["username"], "Token preferred_username should match Keycloak username")
    validate_equals("name" in claims, True, "Token should contain name claim from Keycloak")


# =============================================================================
# Remote OIDC Connector E2E Access Tests (TC 11-12)
# =============================================================================


@mark.p0
@mark.lab_has_standby_controller
def test_remote_oidc_access_with_preferred_username_claim(request):
    """TC11: Verify K8s access with Remote OIDC + oidc-username-claim=preferred_username.

    Test Steps:
        - Apply Remote OIDC connector override
        - Set oidc-username-claim=preferred_username
        - Create CRB by Keycloak username
        - Authenticate Keycloak user, verify kubectl access succeeds
    """
    config = _load_dex_config()
    oidc_config = _get_remote_oidc_config()
    kc_user = _get_keycloak_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    dex_keywords = DexConnectorKeywords(ssh_connection)
    oidc_keywords = RemoteOidcConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(kc_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    oidc_keywords.apply_remote_oidc_override(config=config, claim_mapping=oidc_config["claim_mapping"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    crb_keywords.create_clusterrolebinding_for_user(kc_user["crb_name"], "cluster-admin", kc_user["username"])

    get_logger().log_info("SSH as Keycloak user, oidc-auth, verify kubectl")
    kc_ssh = _create_keycloak_ssh(kc_user["username"], kc_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(kc_ssh, expect_success=True)
    kc_ssh.close()


@mark.p0
@mark.lab_has_standby_controller
def test_remote_oidc_access_with_email_claim(request):
    """TC12: Verify K8s access with Remote OIDC + oidc-username-claim=email.

    Test Steps:
        - Apply Remote OIDC connector override
        - Set oidc-username-claim=email
        - Create CRB by Keycloak user email
        - Authenticate Keycloak user, verify kubectl access succeeds
    """
    config = _load_dex_config()
    oidc_config = _get_remote_oidc_config()
    kc_user = _get_keycloak_test_user_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    dex_keywords = DexConnectorKeywords(ssh_connection)
    oidc_keywords = RemoteOidcConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(kc_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    oidc_keywords.apply_remote_oidc_override(config=config, claim_mapping=oidc_config["claim_mapping"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(kc_user["crb_name"], "cluster-admin", kc_user["email"])

    get_logger().log_info("SSH as Keycloak user, oidc-auth, verify kubectl with email CRB")
    kc_ssh = _create_keycloak_ssh(kc_user["username"], kc_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(kc_ssh, expect_success=True)
    kc_ssh.close()
