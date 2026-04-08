from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.keycloak.keycloak_admin_keywords import KeycloakAdminKeywords
from keywords.cloud_platform.security.keycloak.keycloak_mfa_keywords import KeycloakMfaKeywords
from keywords.cloud_platform.security.oidc.oidc_environment_keywords import OidcEnvironmentKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p1
def test_oidc_keycloak_mfa_first_login(request):
    """Configure OIDC with Keycloak MFA and authenticate for the first time.

    Resets the user's TOTP enrollment to force the CONFIGURE_TOTP registration
    flow, then authenticates via browser and validates kubectl access.

    Steps:
        - Import the Keycloak CA certificate as the oidc-upstream-idp-ca secret in kube-system
        - Render and apply dex Helm overrides with Keycloak connector configuration
        - Apply oidc-auth-apps
        - Create ClusterRoleBinding for the admin group
        - Extract and save the system-local-ca certificate
        - Create local OIDC login kubeconfig
        - Reset user TOTP enrollment via Keycloak Admin API
        - Authenticate via Keycloak CONFIGURE_TOTP flow (first-time TOTP registration)
        - Validate kubectl can list pods using the obtained token
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    namespace = security_config.get_oidc_keycloak_namespace()
    secret_name = security_config.get_oidc_keycloak_upstream_idp_ca_secret_name()
    oidc_app_name = "oidc-auth-apps"
    working_dir = security_config.get_oidc_keycloak_working_dir()

    oidc_env = OidcEnvironmentKeywords(ssh_connection)

    def cleanup():
        oidc_env.cleanup(
            secret_name=secret_name,
            namespace=namespace,
            crb_binding_name=security_config.get_oidc_keycloak_crb_binding_name(),
        )

    request.addfinalizer(cleanup)

    oam_ip = lab_config.get_floating_ip()
    if lab_config.is_ipv6():
        oam_ip = f"[{oam_ip}]"

    get_logger().log_info("Pre-step: Clear OIDC token cache")
    mfa_keywords = KeycloakMfaKeywords(ssh_connection)
    mfa_keywords.clear_oidc_token_cache("/home/sysadmin/.kube/cache/oidc-login")

    kubeconfig_path = oidc_env.setup(
        oam_ip=oam_ip,
        namespace=namespace,
        secret_name=secret_name,
        oidc_app_name=oidc_app_name,
        working_dir=working_dir,
        ca_cert_pem=security_config.get_oidc_keycloak_ca_cert(),
        client_id=security_config.get_oidc_keycloak_client_id(),
        client_secret=security_config.get_oidc_keycloak_client_secret(),
        external_idp_issuer_url=security_config.get_oidc_keycloak_external_idp_issuer_url(),
        crb_binding_name=security_config.get_oidc_keycloak_crb_binding_name(),
        crb_cluster_role=security_config.get_oidc_keycloak_crb_cluster_role(),
        crb_group=security_config.get_oidc_keycloak_crb_group(),
        ca_cert_filename=security_config.get_oidc_keycloak_system_local_ca_cert_filename(),
        kubeconfig_filename=security_config.get_oidc_keycloak_kubeconfig_filename(),
        oidc_client_id=security_config.get_oidc_keycloak_static_client_id(),
        oidc_client_secret=security_config.get_oidc_keycloak_static_client_secret(),
    )

    get_logger().log_info("Resetting OTP credentials for test user to force CONFIGURE_TOTP flow")
    issuer_url = security_config.get_oidc_keycloak_external_idp_issuer_url()
    keycloak_admin = KeycloakAdminKeywords(
        keycloak_url=issuer_url.rsplit("/realms", 1)[0],
        realm=issuer_url.rsplit("/", 1)[-1],
        admin_username=security_config.get_oidc_keycloak_admin_username(),
        admin_password=security_config.get_oidc_keycloak_admin_password(),
    )
    keycloak_admin.delete_user_otp_credentials(security_config.get_oidc_keycloak_test_username())

    get_logger().log_info("Step 7: Authenticate via Keycloak MFA - first login (CONFIGURE_TOTP)")
    login_url = f"http://{oam_ip}:{security_config.get_oidc_keycloak_login_port()}/"
    result = mfa_keywords.run_kubectl_with_browser_login(
        kubeconfig_path=kubeconfig_path,
        login_url=login_url,
        username=security_config.get_oidc_keycloak_test_username(),
        password=security_config.get_oidc_keycloak_test_password(),
        totp_secret=None,
    )
    validate_equals(result.is_kubectl_successful(), True, "kubectl should return non-empty output after first login CONFIGURE_TOTP flow")
    get_logger().log_info(f"kubectl output:\n{result.get_output()}")


@mark.p1
def test_oidc_keycloak_mfa_subsequent_login(request):
    """Authenticate via Keycloak MFA using a cached OIDC token.

    Sets up the OIDC environment and runs kubectl directly using the token
    cached from a previous login. No browser interaction is required.

    Steps:
        - Import the Keycloak CA certificate as the oidc-upstream-idp-ca secret in kube-system
        - Render and apply dex Helm overrides with Keycloak connector configuration
        - Apply oidc-auth-apps
        - Create ClusterRoleBinding for the admin group
        - Extract and save the system-local-ca certificate
        - Create local OIDC login kubeconfig
        - Validate cached OIDC token exists
        - Run kubectl using the cached OIDC token (no browser required)
        - Validate kubectl can list pods
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    namespace = security_config.get_oidc_keycloak_namespace()
    secret_name = security_config.get_oidc_keycloak_upstream_idp_ca_secret_name()
    oidc_app_name = "oidc-auth-apps"
    working_dir = security_config.get_oidc_keycloak_working_dir()
    oidc_token_cache_dir = "/home/sysadmin/.kube/cache/oidc-login"

    oidc_env = OidcEnvironmentKeywords(ssh_connection)

    def cleanup():
        oidc_env.cleanup(
            secret_name=secret_name,
            namespace=namespace,
            crb_binding_name=security_config.get_oidc_keycloak_crb_binding_name(),
        )

    request.addfinalizer(cleanup)

    oam_ip = lab_config.get_floating_ip()
    if lab_config.is_ipv6():
        oam_ip = f"[{oam_ip}]"

    kubeconfig_path = oidc_env.setup(
        oam_ip=oam_ip,
        namespace=namespace,
        secret_name=secret_name,
        oidc_app_name=oidc_app_name,
        working_dir=working_dir,
        ca_cert_pem=security_config.get_oidc_keycloak_ca_cert(),
        client_id=security_config.get_oidc_keycloak_client_id(),
        client_secret=security_config.get_oidc_keycloak_client_secret(),
        external_idp_issuer_url=security_config.get_oidc_keycloak_external_idp_issuer_url(),
        crb_binding_name=security_config.get_oidc_keycloak_crb_binding_name(),
        crb_cluster_role=security_config.get_oidc_keycloak_crb_cluster_role(),
        crb_group=security_config.get_oidc_keycloak_crb_group(),
        ca_cert_filename=security_config.get_oidc_keycloak_system_local_ca_cert_filename(),
        kubeconfig_filename=security_config.get_oidc_keycloak_kubeconfig_filename(),
        oidc_client_id=security_config.get_oidc_keycloak_static_client_id(),
        oidc_client_secret=security_config.get_oidc_keycloak_static_client_secret(),
    )

    get_logger().log_info("Step 7: Run kubectl using cached OIDC token - no browser required")
    mfa_keywords = KeycloakMfaKeywords(ssh_connection)

    mfa_keywords.validate_token_cache_exists(oidc_token_cache_dir)
    result = mfa_keywords.run_kubectl_with_cached_token(kubeconfig_path)
    get_logger().log_info(f"kubectl output:\n{result.get_output()}")
    validate_equals(result.is_kubectl_successful(), True, "Should be able to list pods across all namespaces using cached OIDC token")
