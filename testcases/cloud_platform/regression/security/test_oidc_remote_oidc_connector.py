"""Remote OIDC (Keycloak) connector tests — claim mappings and E2E auth.

Tests the Remote OIDC DEX connector claimMapping configuration,
validates end-to-end OIDC authentication via Keycloak with
oidc-username-claim via service-parameter CLI, and verifies
access using preferred_username and email claims.
"""

import json
import time

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.security.keycloak.keycloak_admin_keywords import KeycloakAdminKeywords
from keywords.cloud_platform.security.keycloak.keycloak_mfa_keywords import KeycloakMfaKeywords
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.security.oidc.object.oidc_token_claims_object import OidcTokenClaimsObject
from keywords.cloud_platform.security.oidc.oidc_environment_keywords import OidcEnvironmentKeywords
from keywords.cloud_platform.security.oidc.remote_oidc_connector_keywords import RemoteOidcConnectorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords


def _load_dex_config() -> dict:
    """Load DEX connector config from JSON5.

    Returns:
        dict: Configuration dictionary.
    """
    return ConfigurationManager.get_security_config().get_dex_connector_config()


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


def _get_oidc_prefixed_username(oam_ip: str, username: str) -> str:
    """Build the full OIDC-prefixed username as seen by kube-apiserver.

    Kubernetes prefixes the issuer URL + '#' to the oidc-username-claim value.
    CRBs must use this full prefixed form for RBAC to match.

    Args:
        oam_ip (str): Lab OAM IP (raw, without brackets).
        username (str): The OIDC claim value (preferred_username or email).

    Returns:
        str: Full prefixed username (e.g., 'https://[ip]:30556/dex#nthomas').
    """
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    return f"https://{bracketed_ip}:30556/dex#{username}"


def _create_keycloak_ssh(username: str, password: str, oam_ip: str) -> SSHConnection:
    """Authenticate Keycloak user via browser-based OIDC login flow.

    Creates a local OIDC kubeconfig and uses KeycloakMfaKeywords to automate
    the browser login against Keycloak. Does NOT re-apply the oidc-auth-apps
    (assumes Dex is already configured with the desired connector).

    Args:
        username (str): Keycloak username.
        password (str): Keycloak password.
        oam_ip (str): Lab OAM IP (raw, without brackets).

    Returns:
        SSHConnection: Admin SSH session with OIDC token cached for Keycloak user.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    mfa_keywords = KeycloakMfaKeywords(ssh_connection)

    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    working_dir = security_config.get_oidc_keycloak_working_dir()

    # Create OIDC kubeconfig for browser login (without re-applying the app)
    oidc_env = OidcEnvironmentKeywords(ssh_connection)
    oidc_env.ensure_kubelogin_installed_on_controller()
    FileKeywords(ssh_connection).create_directory(working_dir)

    # Extract system-local-ca certificate
    ca_cert_content = KubectlGetSecretsKeywords(ssh_connection).get_secret_with_custom_output(
        secret_name="system-local-ca",
        namespace="cert-manager",
        output_format="jsonpath",
        extra_parameters="'{.data.ca\\.crt}'",
        base64=True,
    )
    ca_cert_path = f"{working_dir}system-local-ca.crt"
    FileKeywords(ssh_connection).create_file_with_heredoc(ca_cert_path, ca_cert_content)

    # Generate OIDC kubeconfig
    template_file = get_stx_resource_path("resources/cloud_platform/security/oidc/local-oidc-login-kubeconfig.yml")
    replacement_dict = {
        "ca_cert_filename": ca_cert_path,
        "oam_ip": bracketed_ip,
        "oidc_client_id": security_config.get_oidc_keycloak_static_client_id(),
        "oidc_client_secret": security_config.get_oidc_keycloak_static_client_secret(),
    }
    kubeconfig_path = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dict, "remote-oidc-kubeconfig", working_dir)

    # Clear brute force lockout
    keycloak_admin = KeycloakAdminKeywords(
        keycloak_url=security_config.get_oidc_keycloak_external_idp_issuer_url().rsplit("/realms", 1)[0],
        realm=security_config.get_oidc_keycloak_external_idp_issuer_url().rsplit("/", 1)[-1],
        admin_username=security_config.get_oidc_keycloak_admin_username(),
        admin_password=security_config.get_oidc_keycloak_admin_password(),
    )
    keycloak_admin.delete_user_otp_credentials(username)
    keycloak_admin.clear_user_brute_force_lockout(username)

    # Clear OIDC token cache so kubelogin opens browser flow instead of using cached token
    mfa_keywords.clear_oidc_token_cache()

    # Verify Dex auth endpoint is reachable before starting kubelogin
    # (kubelogin won't bind port 8000 if it can't validate the issuer)
    dex_auth_url = f"https://{bracketed_ip}:30556/dex/auth?client_id=stx-oidc-client-app&response_type=code&scope=openid&redirect_uri=http://localhost:8000"
    timeout_time = time.time() + 30
    while time.time() < timeout_time:
        output = ssh_connection.send(f"curl -sk -o /dev/null -w '%{{http_code}}' '{dex_auth_url}' 2>&1")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        if "302" in raw or "200" in raw:
            get_logger().log_info("Dex auth endpoint verified — ready for kubelogin")
            break
        get_logger().log_info(f"Dex auth endpoint not ready ({raw.strip()}), retrying in 5s")
        time.sleep(5)

    # Authenticate via browser-based flow
    login_url = f"http://{bracketed_ip}:{security_config.get_oidc_keycloak_login_port()}/"
    result = mfa_keywords.run_kubectl_with_browser_login(
        kubeconfig_path=kubeconfig_path,
        login_url=login_url,
        username=username,
        password=password,
        totp_secret=None,
    )
    get_logger().log_info(f"Keycloak browser login: kubectl_successful={result.is_kubectl_successful()}")
    return ssh_connection


def _verify_kubectl_and_stx_access(kc_ssh: SSHConnection, expect_success: bool = True) -> None:
    """Verify kubectl and STX platform access for the authenticated Keycloak user.

    Uses the OIDC kubeconfig with cached token from the browser login flow.
    The kubeconfig is at the standard working_dir location. Retries kubectl
    up to 60s to allow the kube-apiserver OIDC JWKS cache to refresh after
    Dex pod restarts.

    Args:
        kc_ssh (SSHConnection): Authenticated Keycloak SSH session.
        expect_success (bool): Whether access should succeed.
    """
    security_config = ConfigurationManager.get_security_config()
    working_dir = security_config.get_oidc_keycloak_working_dir()
    kubeconfig_path = f"{working_dir}remote-oidc-kubeconfig"

    kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A'"
    if expect_success:
        # Retry for up to 120s to handle apiserver OIDC initialization after restart.
        # The apiserver needs time to fetch JWKS from Dex after a service-parameter-apply
        # restart, especially on Standard systems with 2 controllers.
        timeout_time = time.time() + 120
        rc = -1
        while time.time() < timeout_time:
            kc_ssh.send(kubectl_cmd)
            rc = kc_ssh.get_return_code()
            if rc == 0:
                break
            output = kc_ssh.send(f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A 2>&1 | head -1'")
            raw = "\n".join(output) if isinstance(output, list) else str(output)
            if "Unauthorized" in raw or "provide credentials" in raw or "must be logged in" in raw.lower():
                get_logger().log_info("kubectl Unauthorized — apiserver OIDC not ready yet, retrying in 10s")
                time.sleep(10)
                continue
            if "Forbidden" in raw:
                get_logger().log_info("kubectl Forbidden — apiserver oidc-username-claim may not have propagated, retrying in 10s")
                time.sleep(10)
                continue
            break
        validate_equals(rc, 0, "kubectl should succeed for authenticated Keycloak user")
    else:
        kc_ssh.send(kubectl_cmd)
        rc = kc_ssh.get_return_code()
        validate_equals(rc != 0, True, "kubectl should be denied for Keycloak user")

    # Only check platform CLI access for positive tests.
    # OIDC denial only affects kubectl (K8s API), not platform CLI (Keystone auth).
    if expect_success:
        kc_ssh.send(source_openrc("system host-list"))
        stx_rc = kc_ssh.get_return_code()
        validate_equals(stx_rc, 0, "system host-list should succeed for OIDC-authenticated user")


def _decode_id_token(kc_ssh: SSHConnection) -> OidcTokenClaimsObject:
    """Decode cached token using DexConnectorKeywords.

    Args:
        kc_ssh (SSHConnection): Authenticated SSH session with cached token.

    Returns:
        OidcTokenClaimsObject: Parsed token claims.
    """
    get_logger().log_info("Decoding OIDC token from kubelogin cache")
    # kubelogin stores tokens in ~/.kube/cache/oidc-login/ as JSON files
    output = kc_ssh.send('cat $(ls -t ~/.kube/cache/oidc-login/* 2>/dev/null | grep -v lock | head -1) 2>/dev/null | python3 -c \'import json,sys,base64; d=json.load(sys.stdin); parts=d["id_token"].split("."); payload=parts[1]+"="*(-len(parts[1])%4); print(base64.b64decode(payload).decode())\' 2>/dev/null')
    raw = "\n".join(output) if isinstance(output, list) else str(output)
    raw = raw.strip()
    if not raw or raw == "None":
        # Fallback to ~/.kube/config (oidc-auth flow)
        dex = DexConnectorKeywords(kc_ssh)
        return dex.decode_cached_token()
    claims_dict = json.loads(raw)
    return OidcTokenClaimsObject(claims_dict)


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
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info(f"Applying Remote OIDC override with claimMapping: {oidc_config['claim_mapping']}")
    oidc_keywords = RemoteOidcConnectorKeywords(ssh_connection)
    oidc_keywords.apply_remote_oidc_override(config=config, claim_mapping=oidc_config["claim_mapping"])

    get_logger().log_info("Authenticating Keycloak user and decoding token")
    kc_ssh = _create_keycloak_ssh(kc_user["username"], kc_user["password"], oam_ip)
    claims = _decode_id_token(kc_ssh)
    kc_ssh.close()

    validate_equals(claims.get_email(), kc_user["email"], "Token email claim should match Keycloak user email")
    validate_equals(claims.get_preferred_username(), kc_user["username"], "Token preferred_username should match Keycloak username")
    validate_equals(claims.has_name(), True, "Token should contain name claim from Keycloak")


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
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    oidc_keywords.apply_remote_oidc_override(config=config, claim_mapping=oidc_config["claim_mapping"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    crb_keywords.create_clusterrolebinding_for_user(kc_user["crb_name"], "cluster-admin", _get_oidc_prefixed_username(oam_ip, kc_user["username"]))

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
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    oidc_keywords.apply_remote_oidc_override(config=config, claim_mapping=oidc_config["claim_mapping"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(kc_user["crb_name"], "cluster-admin", kc_user["email"])

    get_logger().log_info("SSH as Keycloak user, oidc-auth, verify kubectl with email CRB")
    kc_ssh = _create_keycloak_ssh(kc_user["username"], kc_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(kc_ssh, expect_success=True)
    kc_ssh.close()


# =============================================================================
# Remote OIDC Negative Tests (TC 37)
# =============================================================================


@mark.p1
@mark.lab_has_standby_controller
def test_keycloak_unverified_email_rejected(request):
    """TC37: Verify access denied when Keycloak email_verified=false and claim=email.

    When oidc-username-claim=email, identity relies on the email claim.
    If Keycloak user has email_verified=false, the email claim should be
    empty or rejected, resulting in access denial even with a matching CRB.

    Test Steps:
        - Configure Remote OIDC (Keycloak) connector
        - Set oidc-username-claim=email
        - Create CRB by Keycloak user email
        - Auth with Keycloak user (email_verified=false)
        - Attempt kubectl — should be denied
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
    security_config = ConfigurationManager.get_security_config()

    # Set emailVerified=false on the test user for this negative test
    keycloak_admin = KeycloakAdminKeywords(
        keycloak_url=security_config.get_oidc_keycloak_external_idp_issuer_url().rsplit("/realms", 1)[0],
        realm=security_config.get_oidc_keycloak_external_idp_issuer_url().rsplit("/", 1)[-1],
        admin_username=security_config.get_oidc_keycloak_admin_username(),
        admin_password=security_config.get_oidc_keycloak_admin_password(),
    )
    keycloak_admin.set_email_verified(kc_user["username"], False)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(kc_user["crb_name"])
        DexConnectorKeywords(ssh).set_oidc_username_claim(config["oidc_username_claim"]["default"])
        FileKeywords(ssh).delete_directory(config["working_dir"])
        # Restore emailVerified=true for other tests
        keycloak_admin.set_email_verified(kc_user["username"], True)

    request.addfinalizer(cleanup)

    get_logger().log_info("Applying Remote OIDC connector override")
    oidc_keywords.apply_remote_oidc_override(config=config, claim_mapping=oidc_config["claim_mapping"])

    get_logger().log_info("Setting oidc-username-claim=email and creating CRB by email")
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["alternative"])
    crb_keywords.create_clusterrolebinding_for_user(kc_user["crb_name"], "cluster-admin", kc_user["email"])

    get_logger().log_info("Auth with Keycloak user (email_verified=false) — should be denied")
    kc_ssh = _create_keycloak_ssh(kc_user["username"], kc_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(kc_ssh, expect_success=False)
    kc_ssh.close()


# =============================================================================
# D8: Distributed Cloud — Remote OIDC Centralized Auth
# =============================================================================


@mark.p1
@mark.lab_has_subcloud
def test_dc_remote_oidc_centralized_auth(request):
    """TC33: Verify centralized OIDC auth on DC System Controller via Keycloak.

    Test Steps:
        - Configure Remote OIDC connector on SC
        - Create CRB for Keycloak user
        - Auth via Keycloak and verify K8s + STX access on SC
    """
    config = _load_dex_config()
    kc_user = _get_keycloak_test_user_config()
    oidc_config = _get_remote_oidc_config()
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
        FileKeywords(ssh).delete_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    oidc_keywords.apply_remote_oidc_override(config=config, claim_mapping=oidc_config["claim_mapping"])
    dex_keywords.set_oidc_username_claim(config["oidc_username_claim"]["default"])
    crb_keywords.create_clusterrolebinding_for_user(kc_user["crb_name"], "cluster-admin", _get_oidc_prefixed_username(oam_ip, kc_user["username"]))

    get_logger().log_info("Verifying Remote OIDC access on DC System Controller")
    kc_ssh = _create_keycloak_ssh(kc_user["username"], kc_user["password"], oam_ip)
    _verify_kubectl_and_stx_access(kc_ssh, expect_success=True)
    kc_ssh.close()
