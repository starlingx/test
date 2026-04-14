from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_config import LabConfig
from config.security.objects.security_config import SecurityConfig
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.keycloak.keycloak_admin_keywords import KeycloakAdminKeywords
from keywords.cloud_platform.security.keycloak.keycloak_mfa_keywords import KeycloakMfaKeywords
from keywords.cloud_platform.security.oidc.oidc_environment_keywords import OidcEnvironmentKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.clusterrole.kubectl_create_clusterrole_keywords import KubectlCreateClusterRoleKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords


def _get_oidc_token_cache_dir(security_config: SecurityConfig) -> str:
    """Get the OIDC token cache directory path on the remote host.

    Args:
        security_config (SecurityConfig): Security configuration object.

    Returns:
        str: Full path to the OIDC token cache directory.
    """
    return f"{security_config.get_oidc_keycloak_remote_user_home()}/.kube/cache/oidc-login"


def _get_keycloak_admin(security_config: SecurityConfig) -> KeycloakAdminKeywords:
    """Build a KeycloakAdminKeywords instance from security configuration.

    Args:
        security_config (SecurityConfig): Security configuration object.

    Returns:
        KeycloakAdminKeywords: Configured Keycloak admin keywords instance.
    """
    issuer_url = security_config.get_oidc_keycloak_external_idp_issuer_url()
    return KeycloakAdminKeywords(
        keycloak_url=issuer_url.rsplit("/realms", 1)[0],
        realm=issuer_url.rsplit("/", 1)[-1],
        admin_username=security_config.get_oidc_keycloak_admin_username(),
        admin_password=security_config.get_oidc_keycloak_admin_password(),
    )


def _setup_oidc_environment(ssh_connection: SSHConnection, security_config: SecurityConfig, lab_config: LabConfig, kubeconfig_filename: str = None, create_admin_crb: bool = True) -> str:
    """Set up the full OIDC Keycloak environment on the remote host.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
        lab_config (LabConfig): Lab configuration object.
        kubeconfig_filename (str): Optional override for the kubeconfig filename.
        create_admin_crb (bool): Whether to create the wrcp-admin ClusterRoleBinding.

    Returns:
        str: Full path to the generated kubeconfig file on the remote host.
    """
    oam_ip = lab_config.get_floating_ip()
    if lab_config.is_ipv6():
        oam_ip = f"[{oam_ip}]"
    return OidcEnvironmentKeywords(ssh_connection).setup(
        oam_ip=oam_ip,
        namespace=security_config.get_oidc_keycloak_namespace(),
        secret_name=security_config.get_oidc_keycloak_upstream_idp_ca_secret_name(),
        oidc_app_name="oidc-auth-apps",
        working_dir=security_config.get_oidc_keycloak_working_dir(),
        ca_cert_pem=security_config.get_oidc_keycloak_ca_cert(),
        client_id=security_config.get_oidc_keycloak_client_id(),
        client_secret=security_config.get_oidc_keycloak_client_secret(),
        external_idp_issuer_url=security_config.get_oidc_keycloak_external_idp_issuer_url(),
        ca_cert_filename=security_config.get_oidc_keycloak_system_local_ca_cert_filename(),
        kubeconfig_filename=kubeconfig_filename or security_config.get_oidc_keycloak_kubeconfig_filename(),
        oidc_client_id=security_config.get_oidc_keycloak_static_client_id(),
        oidc_client_secret=security_config.get_oidc_keycloak_static_client_secret(),
        crb_binding_name=security_config.get_oidc_keycloak_crb_binding_name() if create_admin_crb else None,
        crb_cluster_role=security_config.get_oidc_keycloak_crb_cluster_role() if create_admin_crb else None,
        crb_group=security_config.get_oidc_keycloak_crb_group() if create_admin_crb else None,
    )


def _cleanup_oidc_environment(ssh_connection: SSHConnection, security_config: SecurityConfig) -> None:
    """Clean up the OIDC Keycloak environment on the remote host.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
    """
    OidcEnvironmentKeywords(ssh_connection).cleanup(
        secret_name=security_config.get_oidc_keycloak_upstream_idp_ca_secret_name(),
        namespace=security_config.get_oidc_keycloak_namespace(),
        crb_binding_name=security_config.get_oidc_keycloak_crb_binding_name(),
    )


@mark.p1
def test_oidc_kubectl_admin_role_can_create_pod(request: FixtureRequest):
    """Verify kubectl run succeeds when user has admin role mapped to cluster-admin.

    Clears the OIDC token cache, sets up the OIDC environment, then runs
    kubectl run nginx with browser-based Keycloak MFA authentication using
    a user that belongs to the admin group bound to cluster-admin.

    Steps:
        - Clear OIDC token cache
        - Set up OIDC environment
        - Run kubectl run test-pod --image=busybox --restart=Never via browser login
        - Login with admin role user credentials and valid OTP
        - Validate kubectl run succeeded
        - Validate cached OIDC token exists after browser login
        - Run kubectl get pods -A using the cached OIDC token (no browser required)
        - Validate kubectl succeeds using the cached token
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    mfa_keywords = KeycloakMfaKeywords(ssh_connection)

    get_logger().log_test_case_step("Clear OIDC token cache")
    mfa_keywords.clear_oidc_token_cache()

    get_logger().log_test_case_step("Set up OIDC environment")
    kubeconfig_path = _setup_oidc_environment(ssh_connection, security_config, lab_config)

    def cleanup():
        KubectlDeletePodsKeywords(ssh_connection, "/etc/kubernetes/admin.conf").cleanup_pod("test-pod", "default")
        _cleanup_oidc_environment(ssh_connection, security_config)

    request.addfinalizer(cleanup)

    oam_ip = lab_config.get_floating_ip()
    if lab_config.is_ipv6():
        oam_ip = f"[{oam_ip}]"
    login_url = f"http://{oam_ip}:{security_config.get_oidc_keycloak_login_port()}/"

    get_logger().log_test_case_step("Reset OTP credentials and clear brute force lockout before browser login")
    keycloak_admin = _get_keycloak_admin(security_config)
    keycloak_admin.delete_user_otp_credentials(security_config.get_oidc_keycloak_admin2_username())
    keycloak_admin.clear_user_brute_force_lockout(security_config.get_oidc_keycloak_admin2_username())

    get_logger().log_test_case_step("Run kubectl run nginx with browser login as admin role user")
    run_result = mfa_keywords.run_kubectl_run_with_browser_login(
        kubeconfig_path=kubeconfig_path,
        login_url=login_url,
        pod_name="test-pod",
        image="busybox",
        namespace="default",
        username=security_config.get_oidc_keycloak_admin2_username(),
        password=security_config.get_oidc_keycloak_admin2_password(),
        totp_secret=None,
    )
    get_logger().log_info(f"kubectl run output:\n{run_result.get_output()}")
    validate_equals(run_result.is_kubectl_run_successful("test-pod"), True, "kubectl run should succeed for user with admin role")

    get_logger().log_test_case_step("Validate cached OIDC token exists after browser login")
    mfa_keywords.validate_token_cache_exists(_get_oidc_token_cache_dir(security_config))

    get_logger().log_test_case_step("Run kubectl get pods -A using cached OIDC token (no browser required)")
    cached_result = mfa_keywords.run_kubectl_with_cached_token(kubeconfig_path)
    get_logger().log_info(f"kubectl output:\n{cached_result.get_output()}")
    validate_equals(cached_result.is_kubectl_successful(), True, "kubectl should succeed using cached OIDC token after admin browser login")


@mark.p1
def test_oidc_kubectl_operator_role_get_allowed_run_forbidden(request: FixtureRequest):
    """Verify operator role user can list pods but cannot create pods.

    Creates a cluster-operator ClusterRole with get/list permissions only,
    binds it to the operator group, then authenticates as the operator user
    via Keycloak MFA. Validates kubectl get pods succeeds and kubectl run
    is rejected with an RBAC forbidden error.

    Steps:
        - Clear OIDC token cache
        - Create cluster-operator ClusterRole with get/list verbs
        - Create ClusterRoleBinding for operator group
        - Set up OIDC environment
        - Reset OTP credentials and clear brute force lockout for operator user
        - Run kubectl get pods -A via browser login as operator user (CONFIGURE_TOTP)
        - Validate kubectl get pods succeeds
        - Run kubectl run test-pod --image=busybox --restart=Never using cached token
        - Validate kubectl run fails with RBAC forbidden error
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    mfa_keywords = KeycloakMfaKeywords(ssh_connection)
    clusterrole_keywords = KubectlCreateClusterRoleKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    operator_role = security_config.get_oidc_keycloak_operator_cluster_role_name()
    operator_binding = security_config.get_oidc_keycloak_operator_crb_binding_name()
    operator_group = security_config.get_oidc_keycloak_operator_crb_group()

    get_logger().log_test_case_step("Clear OIDC token cache")
    mfa_keywords.clear_oidc_token_cache()

    get_logger().log_test_case_step("Create cluster-operator ClusterRole with get/list permissions")
    clusterrole_keywords.create_clusterrole(
        role_name=operator_role,
        verbs=["get", "list"],
        resources=["pods", "services", "deployments", "namespaces", "nodes"],
    )

    get_logger().log_test_case_step("Create ClusterRoleBinding for operator group")
    crb_keywords.create_clusterrolebinding_for_group(
        binding_name=operator_binding,
        clusterrole=operator_role,
        group=operator_group,
    )

    get_logger().log_test_case_step("Set up OIDC environment")
    kubeconfig_path = _setup_oidc_environment(ssh_connection, security_config, lab_config, create_admin_crb=False)

    def cleanup():
        crb_keywords.delete_clusterrolebinding(operator_binding)
        clusterrole_keywords.delete_clusterrole(operator_role)
        _cleanup_oidc_environment(ssh_connection, security_config)

    request.addfinalizer(cleanup)

    oam_ip = lab_config.get_floating_ip()
    if lab_config.is_ipv6():
        oam_ip = f"[{oam_ip}]"
    login_url = f"http://{oam_ip}:{security_config.get_oidc_keycloak_login_port()}/"

    get_logger().log_test_case_step("Reset OTP credentials and clear brute force lockout for operator user")
    keycloak_admin = _get_keycloak_admin(security_config)
    keycloak_admin.delete_user_otp_credentials(security_config.get_oidc_keycloak_operator_username())
    keycloak_admin.clear_user_brute_force_lockout(security_config.get_oidc_keycloak_operator_username())

    get_logger().log_test_case_step("Run kubectl get pods -A via browser login as operator user")
    get_result = mfa_keywords.run_kubectl_with_browser_login(
        kubeconfig_path=kubeconfig_path,
        login_url=login_url,
        username=security_config.get_oidc_keycloak_operator_username(),
        password=security_config.get_oidc_keycloak_operator_password(),
        totp_secret=None,
    )
    get_logger().log_info(f"kubectl get pods output:\n{get_result.get_output()}")
    validate_equals(get_result.is_kubectl_successful(), True, "kubectl get pods should succeed for operator role user")

    get_logger().log_test_case_step("Run kubectl run test-pod as operator user using cached token - expecting RBAC forbidden")
    run_result = mfa_keywords.run_kubectl_run_with_cached_token(
        kubeconfig_path=kubeconfig_path,
        pod_name="operator-test-pod",
        image="busybox",
        namespace="default",
    )
    get_logger().log_info(f"kubectl run output:\n{run_result.get_output()}")
    validate_equals(run_result.is_kubectl_forbidden(), True, "kubectl run should be forbidden for operator role user")


@mark.p1
def test_oidc_kubectl_guard_role_get_denied_and_auth_can_i_denied(request: FixtureRequest):
    """Verify authentication succeeds but all kubectl operations are denied for guard role user.

    Creates a cluster-guard ClusterRole with no resource permissions, binds it
    to the guard group, then authenticates as jthomas via Keycloak MFA. Validates
    that kubectl get pods is forbidden, and kubectl auth can-i confirms no
    permissions for list pods or create pods.

    Steps:
        - Clear OIDC token cache
        - Create cluster-guard ClusterRole with no resource permissions
        - Create ClusterRoleBinding for guard group
        - Set up OIDC environment
        - Run kubectl get pods -A via browser login as guard user with valid OTP
        - Validate kubectl get pods is forbidden (authentication succeeded, RBAC denied)
        - Run kubectl auth can-i list pods -A using cached token
        - Validate result is 'no'
        - Run kubectl auth can-i create pods using cached token
        - Validate result is 'no'
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    mfa_keywords = KeycloakMfaKeywords(ssh_connection)
    clusterrole_keywords = KubectlCreateClusterRoleKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    guard_role = security_config.get_oidc_keycloak_guard_cluster_role_name()
    guard_binding = security_config.get_oidc_keycloak_guard_crb_binding_name()
    guard_group = security_config.get_oidc_keycloak_guard_crb_group()

    get_logger().log_test_case_step("Clear OIDC token cache")
    mfa_keywords.clear_oidc_token_cache()

    get_logger().log_test_case_step("Create cluster-guard ClusterRole with no resource permissions")
    clusterrole_keywords.create_clusterrole(
        role_name=guard_role,
        verbs=["get", "list"],
        resources=["configmaps"],
    )

    get_logger().log_test_case_step("Create ClusterRoleBinding for guard group")
    crb_keywords.create_clusterrolebinding_for_group(
        binding_name=guard_binding,
        clusterrole=guard_role,
        group=guard_group,
    )

    get_logger().log_test_case_step("Set up OIDC environment")
    kubeconfig_path = _setup_oidc_environment(ssh_connection, security_config, lab_config, create_admin_crb=False)

    def cleanup():
        crb_keywords.delete_clusterrolebinding(guard_binding)
        clusterrole_keywords.delete_clusterrole(guard_role)
        _cleanup_oidc_environment(ssh_connection, security_config)

    request.addfinalizer(cleanup)

    oam_ip = lab_config.get_floating_ip()
    if lab_config.is_ipv6():
        oam_ip = f"[{oam_ip}]"
    login_url = f"http://{oam_ip}:{security_config.get_oidc_keycloak_login_port()}/"

    get_logger().log_test_case_step("Run kubectl get pods -A via browser login as guard user")
    get_result = mfa_keywords.run_kubectl_with_browser_login(
        kubeconfig_path=kubeconfig_path,
        login_url=login_url,
        username=security_config.get_oidc_keycloak_guard_username(),
        password=security_config.get_oidc_keycloak_guard_password(),
        totp_secret=security_config.get_oidc_keycloak_guard_totp_secret(),
    )
    get_logger().log_info(f"kubectl get pods output:\n{get_result.get_output()}")
    validate_equals(get_result.is_kubectl_forbidden(), True, "kubectl get pods should be forbidden for guard role user")

    get_logger().log_test_case_step("Run kubectl auth can-i list pods -A using cached token")
    can_i_list_result = mfa_keywords.run_kubectl_auth_can_i_with_cached_token(
        kubeconfig_path=kubeconfig_path,
        verb="list",
        resource="pods",
        all_namespaces=True,
    )
    get_logger().log_info(f"kubectl auth can-i list pods output: {can_i_list_result.get_output()}")
    validate_equals(can_i_list_result.is_kubectl_auth_denied(), True, "kubectl auth can-i list pods should return 'no' for guard role user")

    get_logger().log_test_case_step("Run kubectl auth can-i create pods using cached token")
    can_i_create_result = mfa_keywords.run_kubectl_auth_can_i_with_cached_token(
        kubeconfig_path=kubeconfig_path,
        verb="create",
        resource="pods",
    )
    get_logger().log_info(f"kubectl auth can-i create pods output: {can_i_create_result.get_output()}")
    validate_equals(can_i_create_result.is_kubectl_auth_denied(), True, "kubectl auth can-i create pods should return 'no' for guard role user")


@mark.p1
def test_oidc_keycloak_mfa_first_login(request: FixtureRequest):
    """Configure OIDC with Keycloak MFA and authenticate for the first time.

    Resets the user's TOTP enrollment to force the CONFIGURE_TOTP registration
    flow, then authenticates via browser and validates kubectl access.

    Steps:
        - Clear OIDC token cache
        - Set up OIDC environment
        - Reset user TOTP enrollment via Keycloak Admin API
        - Authenticate via Keycloak CONFIGURE_TOTP flow (first-time TOTP registration)
        - Validate kubectl can list pods using the obtained token
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    request.addfinalizer(lambda: _cleanup_oidc_environment(ssh_connection, security_config))

    oam_ip = lab_config.get_floating_ip()
    if lab_config.is_ipv6():
        oam_ip = f"[{oam_ip}]"

    mfa_keywords = KeycloakMfaKeywords(ssh_connection)

    get_logger().log_test_case_step("Clear OIDC token cache")
    mfa_keywords.clear_oidc_token_cache()

    get_logger().log_test_case_step("Set up OIDC environment")
    kubeconfig_path = _setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Reset OTP credentials to force CONFIGURE_TOTP flow")
    keycloak_admin = _get_keycloak_admin(security_config)
    keycloak_admin.delete_user_otp_credentials(security_config.get_oidc_keycloak_test_username())
    keycloak_admin.clear_user_brute_force_lockout(security_config.get_oidc_keycloak_test_username())

    get_logger().log_test_case_step("Authenticate via Keycloak MFA first login (CONFIGURE_TOTP)")
    login_url = f"http://{oam_ip}:{security_config.get_oidc_keycloak_login_port()}/"
    result = mfa_keywords.run_kubectl_with_browser_login(
        kubeconfig_path=kubeconfig_path,
        login_url=login_url,
        username=security_config.get_oidc_keycloak_test_username(),
        password=security_config.get_oidc_keycloak_test_password(),
        totp_secret=None,
    )
    get_logger().log_info(f"kubectl output:\n{result.get_output()}")
    validate_equals(result.is_kubectl_successful(), True, "kubectl should succeed after first login CONFIGURE_TOTP flow")


@mark.p1
def test_oidc_keycloak_mfa_subsequent_login(request: FixtureRequest):
    """Authenticate via Keycloak MFA using a cached OIDC token.

    Sets up the OIDC environment and runs kubectl directly using the token
    cached from a previous login. No browser interaction is required.

    Steps:
        - Set up OIDC environment
        - Validate cached OIDC token exists
        - Run kubectl using the cached OIDC token (no browser required)
        - Validate kubectl can list pods
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    request.addfinalizer(lambda: _cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    kubeconfig_path = _setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Validate cached OIDC token exists")
    mfa_keywords = KeycloakMfaKeywords(ssh_connection)
    mfa_keywords.validate_token_cache_exists(_get_oidc_token_cache_dir(security_config))

    get_logger().log_test_case_step("Run kubectl using cached OIDC token")
    result = mfa_keywords.run_kubectl_with_cached_token(kubeconfig_path)
    get_logger().log_info(f"kubectl output:\n{result.get_output()}")
    validate_equals(result.is_kubectl_successful(), True, "kubectl should succeed using cached OIDC token")


@mark.p1
def test_oidc_kubectl_id_token_expired_silent_refresh(request: FixtureRequest):
    """Verify kubectl silently refreshes an expired ID token using the cached refresh token.

    With offline_access scope, kubelogin caches both id_token and refresh_token.
    The cached id_token is directly replaced with an expired token on the remote
    host. kubelogin detects the expired id_token and silently exchanges the cached
    refresh_token for a new one - no browser prompt, kubectl succeeds.

    Steps:
        - Set up OIDC environment
        - Validate cached OIDC token exists
        - Replace the cached id_token with an expired token
        - Run kubectl get pods -A
        - Validate kubectl succeeds via silent refresh token exchange
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    request.addfinalizer(lambda: _cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    kubeconfig_path = _setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Validate cached OIDC token exists")
    mfa_keywords = KeycloakMfaKeywords(ssh_connection)
    mfa_keywords.validate_token_cache_exists(_get_oidc_token_cache_dir(security_config))

    get_logger().log_test_case_step("Replace cached id_token with an expired token")
    mfa_keywords.expire_cached_id_token(_get_oidc_token_cache_dir(security_config))

    get_logger().log_test_case_step("Run kubectl after id_token expiry - expecting silent refresh via cached refresh_token")
    result = mfa_keywords.run_kubectl_with_cached_token(kubeconfig_path)
    get_logger().log_info(f"kubectl output:\n{result.get_output()}")
    validate_equals(result.is_kubectl_successful(), True, "kubectl should succeed via silent refresh token exchange after id_token expiry")


@mark.p1
def test_oidc_kubectl_refresh_token_expired_requires_browser_reauth(request: FixtureRequest):
    """Verify kubectl prompts browser URL when the cached refresh token is invalid.

    Both the cached id_token and refresh_token are directly invalidated in the
    cache file on the remote host. kubelogin cannot silently refresh and outputs
    the browser login URL to stdout, indicating re-authentication is required.

    Steps:
        - Set up OIDC environment
        - Validate cached OIDC token exists
        - Replace the cached id_token with an expired token
        - Replace the cached refresh_token with an invalid value
        - Run kubectl get pods -A
        - Validate kubectl output contains the browser login URL
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    mfa_keywords = KeycloakMfaKeywords(ssh_connection)

    request.addfinalizer(lambda: _cleanup_oidc_environment(ssh_connection, security_config))
    request.addfinalizer(mfa_keywords.clear_oidc_token_cache)

    get_logger().log_test_case_step("Set up OIDC environment")
    kubeconfig_path = _setup_oidc_environment(ssh_connection, security_config, lab_config)

    get_logger().log_test_case_step("Validate cached OIDC token exists")
    mfa_keywords.validate_token_cache_exists(_get_oidc_token_cache_dir(security_config))

    get_logger().log_test_case_step("Invalidate cached id_token and refresh_token")
    mfa_keywords.expire_cached_id_token(_get_oidc_token_cache_dir(security_config))
    mfa_keywords.invalidate_cached_refresh_token(_get_oidc_token_cache_dir(security_config))

    get_logger().log_test_case_step("Run kubectl with invalid tokens - expecting browser URL prompt in output")
    result = mfa_keywords.run_kubectl_with_cached_token(kubeconfig_path)
    get_logger().log_info(f"kubectl output:\n{result.get_output()}")
    validate_equals(result.is_browser_prompt_shown(), True, "kubectl should prompt browser URL when refresh token is invalid")


@mark.p1
def test_oidc_kubectl_invalid_kubeconfig_fails(request: FixtureRequest):
    """Verify kubectl authentication fails with an invalid issuer URL in the kubeconfig.

    Sets up the OIDC environment normally, then patches the kubeconfig in-place
    with an invalid issuer URL and validates that authentication fails.

    Steps:
        - Set up OIDC environment
        - Patch kubeconfig with invalid issuer URL
        - Run kubectl get pods -A
        - Validate authentication fails
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()

    request.addfinalizer(lambda: _cleanup_oidc_environment(ssh_connection, security_config))

    get_logger().log_test_case_step("Set up OIDC environment")
    kubeconfig_path = _setup_oidc_environment(ssh_connection, security_config, lab_config)
    mfa_keywords = KeycloakMfaKeywords(ssh_connection)

    get_logger().log_test_case_step("Patch kubeconfig with invalid issuer URL")
    mfa_keywords.patch_kubeconfig_issuer_url(kubeconfig_path, security_config.get_oidc_keycloak_invalid_issuer_url())
    result = mfa_keywords.run_kubectl_with_cached_token(kubeconfig_path)
    get_logger().log_info(f"kubectl output (invalid issuer):\n{result.get_output()}")
    validate_equals(result.is_kubectl_successful(), False, "kubectl should fail authentication with invalid issuer URL")
