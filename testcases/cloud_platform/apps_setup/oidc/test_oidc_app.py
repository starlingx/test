"""OIDC DEX connector pre/post upgrade, rollback, and B&R validation.

Validates that OIDC settings (dex overrides, oidc-username-claim,
service parameters) are preserved unchanged across upgrade, rollback,
and backup-restore operations, and that OIDC access continues to work.

Test Ordering:
    These tests use a _pre/_post naming convention for multi-stage Jenkins
    pipelines. They are NOT run in the same pytest invocation:

        Stage 1: pytest test_oidc_app.py -k "_pre"   (setup + verify)
        Stage 2: <upgrade / rollback / B&R operation>
        Stage 3: pytest test_oidc_app.py -k "_post"  (re-verify + cleanup)

    Each _pre test creates resources and verifies access. Each _post test
    re-verifies access with the same resources and cleans up via finalizer.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.security.objects.dex_config import DexConfig
from config.security.objects.dex_test_user import DexTestUser
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.keycloak.keycloak_admin_keywords import KeycloakAdminKeywords
from keywords.cloud_platform.security.keycloak.keycloak_mfa_keywords import KeycloakMfaKeywords
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.security.oidc.oidc_auth_keywords import OidcAuthKeywords
from keywords.cloud_platform.security.oidc.remote_oidc_connector_keywords import RemoteOidcConnectorKeywords
from keywords.cloud_platform.security.oidc.wad_connector_keywords import WadConnectorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords


def _get_dex_config() -> DexConfig:
    """Load DEX connector config object from JSON5.

    Returns:
        DexConfig: Typed DEX connector configuration.
    """
    return ConfigurationManager.get_security_config().get_dex_connector_config()


def _apply_ldap_attr_override(ssh_connection: SSHConnection, dex_config: DexConfig) -> None:
    """Generate and apply LDAP override with configured attribute mappings.

    Args:
        ssh_connection (SSHConnection): Active controller SSH.
        dex_config (DexConfig): DEX connector configuration.
    """
    yaml_keywords = YamlKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    dex_keywords = DexConnectorKeywords(ssh_connection)

    working_dir = dex_config.get_working_dir()
    file_keywords.create_directory(working_dir)

    template = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-ldap-attr-mapping-overrides.yaml")
    mgmt_ip = SystemAddrpoolListKeywords(ssh_connection).get_system_addrpool_list().get_management_floating_address()
    if ":" in mgmt_ip:
        mgmt_ip = f"[{mgmt_ip}]"
    replacements = {
        "mgmt_ip": mgmt_ip,
        "bind_pw": KeyringKeywords(ssh_connection).get_keyring(service="ldap", identifier="ldapadmin"),
        "email_attr": dex_config.get_local_ldap().get_email_attr(),
        "name_attr": dex_config.get_local_ldap().get_name_attr(),
    }
    override_file = yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-ldap-attr-test.yaml", working_dir)
    dex_keywords.apply_dex_override_and_reapply(override_file, dex_config.get_oidc_app_name(), dex_config.get_namespace())


def _get_oidc_issuer(oam_ip: str) -> str:
    """Construct the OIDC issuer URL from the OAM IP.

    Args:
        oam_ip (str): Lab OAM IP address.

    Returns:
        str: OIDC issuer URL.
    """
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    return f"https://{bracketed_ip}:30556/dex"


def _verify_keycloak_oidc_access(ssh_connection: SSHConnection, kc_user: DexTestUser) -> None:
    """Verify Keycloak OIDC access via browser-based login flow.

    Prepares the Keycloak admin state (clears OTP, brute force lockout),
    extracts the system CA certificate, generates a kubeconfig from template,
    and performs a kubectl command authenticated via browser login.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        kc_user (DexTestUser): Keycloak test user configuration.
    """
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    working_dir = security_config.get_oidc_keycloak_working_dir()

    FileKeywords(ssh_connection).create_directory(working_dir)

    keycloak_admin = KeycloakAdminKeywords(
        keycloak_url=security_config.get_oidc_keycloak_external_idp_issuer_url().rsplit("/realms", 1)[0],
        realm=security_config.get_oidc_keycloak_external_idp_issuer_url().rsplit("/", 1)[-1],
        admin_username=security_config.get_oidc_keycloak_admin_username(),
        admin_password=security_config.get_oidc_keycloak_admin_password(),
    )
    keycloak_admin.delete_user_otp_credentials(kc_user.get_username())
    keycloak_admin.clear_user_brute_force_lockout(kc_user.get_username())

    ca_cert_content = KubectlGetSecretsKeywords(ssh_connection).get_secret_with_custom_output(
        secret_name="system-local-ca",
        namespace="cert-manager",
        output_format="jsonpath",
        extra_parameters="'{.data.ca\\.crt}'",
        base64=True,
    )
    ca_cert_path = f"{working_dir}system-local-ca.crt"
    FileKeywords(ssh_connection).create_file_with_heredoc(ca_cert_path, ca_cert_content)

    template_file = get_stx_resource_path("resources/cloud_platform/security/oidc/local-oidc-login-kubeconfig.yml")
    replacement_dict = {
        "ca_cert_filename": ca_cert_path,
        "oam_ip": bracketed_ip,
        "oidc_client_id": security_config.get_oidc_keycloak_static_client_id(),
        "oidc_client_secret": security_config.get_oidc_keycloak_static_client_secret(),
    }
    kubeconfig_path = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dict, "remote-oidc-kubeconfig", working_dir)

    mfa_keywords = KeycloakMfaKeywords(ssh_connection)
    mfa_keywords.clear_oidc_token_cache()
    login_url = f"http://{bracketed_ip}:{security_config.get_oidc_keycloak_login_port()}/"
    result = mfa_keywords.run_kubectl_with_browser_login(
        kubeconfig_path=kubeconfig_path,
        login_url=login_url,
        username=kc_user.get_username(),
        password=kc_user.get_password(),
        totp_secret=None,
    )
    validate_equals(result.is_kubectl_successful(), True, "kubectl should succeed after Keycloak login")


# =============================================================================
# OIDC Pre/Post Tests — LDAP Backend
#
# _pre: creates LDAP user + CRB, applies dex override, verifies OIDC access.
# _post: re-verifies OIDC access with same user/CRB, then cleans up.
# =============================================================================


@mark.p0
def test_oidc_ldap_pre(request):
    """Create LDAP user, configure dex, and verify OIDC access before operation."""
    dex_config = _get_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    ldap_keywords = LdapKeywords(ssh_connection, lab_config.get_admin_credentials().get_password())
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    oam_ip = lab_config.get_floating_ip()
    test_user = dex_config.get_test_user()
    oidc_issuer = _get_oidc_issuer(oam_ip)

    get_logger().log_test_case_step("Creating LDAP user")
    ldap_keywords.create_user(test_user.get_username(), test_user.get_password(), user_role=test_user.get_role())
    ldap_keywords.add_mail_attribute(test_user.get_username(), test_user.get_email())

    get_logger().log_test_case_step("Applying dex LDAP override")
    _apply_ldap_attr_override(ssh_connection, dex_config)
    dex_keywords.set_oidc_username_claim(dex_config.get_oidc_username_claim().get_default())

    get_logger().log_test_case_step("Creating CRB and verifying OIDC access")
    crb_keywords.create_clusterrolebinding_for_user(test_user.get_crb_name(), "cluster-admin", f"{oidc_issuer}#{test_user.get_username()}")
    ldap_ssh = OidcAuthKeywords.create_ldap_user_ssh(oam_ip, test_user.get_username(), test_user.get_password())
    KubectlGetPodsKeywords(ldap_ssh).get_pods()
    ldap_ssh.close()


@mark.p0
def test_oidc_ldap_post(request):
    """Verify same LDAP user still has OIDC access after operation."""
    dex_config = _get_dex_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    test_user = dex_config.get_test_user()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up LDAP test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user.get_crb_name())
        LdapKeywords(ssh, lab_config.get_admin_credentials().get_password()).delete_user(test_user.get_username())
        FileKeywords(ssh).delete_directory(dex_config.get_working_dir())

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Verifying same LDAP user still has OIDC access after operation")
    ldap_ssh = OidcAuthKeywords.create_ldap_user_ssh(oam_ip, test_user.get_username(), test_user.get_password())
    KubectlGetPodsKeywords(ldap_ssh).get_pods()
    ldap_ssh.close()


# =============================================================================
# OIDC Pre/Post Tests — WAD Backend
#
# _pre: applies WAD connector override, creates CRB, verifies OIDC access.
# _post: re-verifies WAD OIDC access, then cleans up CRB.
# =============================================================================


@mark.p0
def test_oidc_wad_pre(request):
    """Configure WAD connector and verify OIDC access before operation."""
    dex_config = _get_dex_config()
    wad_config = dex_config.get_wad_connector()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    oidc_auth = OidcAuthKeywords(ssh_connection)
    oam_ip = lab_config.get_floating_ip()
    wad_user = dex_config.get_wad_test_user()
    oidc_issuer = _get_oidc_issuer(oam_ip)

    # oidc-auth below overwrites sysadmin's ~/.kube/config with an OIDC token.
    # Restore the admin context on teardown so later tests (incl. CGCS) don't
    # hit "Please enter Username:" once the token expires.
    request.addfinalizer(oidc_auth.restore_admin_kubeconfig)

    get_logger().log_test_case_step("Applying WAD connector override")
    wad_keywords = WadConnectorKeywords(ssh_connection)
    wad_keywords.apply_wad_override(
        config=dex_config,
        email_attr="userPrincipalName",
        username_attr=wad_config.get_username_attr(),
        name_attr=wad_config.get_name_attr(),
        reuse_values=True,
    )

    get_logger().log_test_case_step("Creating CRB for WAD user")
    crb_keywords.create_clusterrolebinding_for_user(wad_user.get_crb_name(), "cluster-admin", f"{oidc_issuer}#{wad_user.get_username()}")

    get_logger().log_test_case_step("Verifying WAD OIDC access before operation")
    oidc_auth.authenticate_wad_user(wad_user.get_username(), wad_user.get_password(), backend=wad_config.get_connector_id())
    KubectlGetPodsKeywords(ssh_connection).get_pods()


@mark.p0
def test_oidc_wad_post(request):
    """Verify same WAD user still has OIDC access after operation."""
    dex_config = _get_dex_config()
    wad_config = dex_config.get_wad_connector()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    wad_user = dex_config.get_wad_test_user()
    oidc_auth = OidcAuthKeywords(ssh_connection)

    # Restore kubeconfig as its own finalizer, registered before poisoning and
    # independent of other cleanup, so it runs even if the test fails at any
    # stage or another cleanup step raises.
    request.addfinalizer(OidcAuthKeywords(ssh_connection).restore_admin_kubeconfig)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up WAD test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(wad_user.get_crb_name())

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Verifying same WAD user still has OIDC access after operation")
    oidc_auth.authenticate_wad_user(wad_user.get_username(), wad_user.get_password(), backend=wad_config.get_connector_id())
    KubectlGetPodsKeywords(ssh_connection).get_pods()


# =============================================================================
# OIDC Pre/Post Tests — Remote OIDC (Keycloak) Backend
#
# _pre: applies remote OIDC override, creates CRB, verifies browser-based login.
# _post: re-verifies Keycloak OIDC access, then cleans up CRB.
# =============================================================================


@mark.p0
def test_oidc_keycloak_pre(request):
    """Configure Remote OIDC (Keycloak) connector and verify access before operation."""
    dex_config = _get_dex_config()
    remote_oidc_config = dex_config.get_remote_oidc()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    oam_ip = lab_config.get_floating_ip()
    kc_user = dex_config.get_keycloak_test_user()
    oidc_issuer = _get_oidc_issuer(oam_ip)

    get_logger().log_test_case_step("Applying Remote OIDC (Keycloak) connector override")
    oidc_keywords = RemoteOidcConnectorKeywords(ssh_connection)
    oidc_keywords.apply_remote_oidc_override(config=dex_config, claim_mapping=remote_oidc_config.get_claim_mapping())

    get_logger().log_test_case_step("Creating CRB for Keycloak user")
    crb_keywords.create_clusterrolebinding_for_user(kc_user.get_crb_name(), "cluster-admin", f"{oidc_issuer}#{kc_user.get_username()}")

    get_logger().log_test_case_step("Verifying Keycloak OIDC access before operation")
    _verify_keycloak_oidc_access(ssh_connection, kc_user)


@mark.p0
def test_oidc_keycloak_post(request):
    """Verify same Keycloak user still has OIDC access after operation."""
    dex_config = _get_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kc_user = dex_config.get_keycloak_test_user()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up Keycloak test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(kc_user.get_crb_name())

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Verifying same Keycloak user still has OIDC access after operation")
    _verify_keycloak_oidc_access(ssh_connection, kc_user)
