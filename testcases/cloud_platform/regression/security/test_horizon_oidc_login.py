"""STX Horizon OIDC (DEX) browser-based authentication.

Verifies Horizon WebSSO login via OAuth2-proxy + DEX with the Local LDAP
connector: the Horizon login page offers the OpenID Connect auth method, a
headless browser completes the DEX login (connector selection, DEX-native form,
and Grant Access approval), and the Horizon dashboard loads.

Follows the TCPG-5002 STX-CLI OIDC pattern: the LDAP user/group, DEX ldap-1
connector, and identity/stx role-bindings are set up the same way, and the DEX
handling is reused via DexLoginPage. Horizon authorizes the session through the
keystone role-bindings (no Kubernetes ClusterRoleBinding is required for the
Horizon WebSSO flow).
"""

import time

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_config import LabConfig
from config.security.objects.dex_config import DexConfig
from config.security.objects.dex_test_user import DexTestUser
from config.security.objects.security_config import SecurityConfig
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.keycloak.keycloak_admin_keywords import KeycloakAdminKeywords
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.security.oidc.oidc_environment_keywords import OidcEnvironmentKeywords
from keywords.cloud_platform.security.oidc.oidc_setup_keywords import OidcSetupKeywords
from keywords.cloud_platform.security.oidc.wad_connector_keywords import WadConnectorKeywords
from keywords.cloud_platform.security.oidc_login.horizon_oidc_login_keywords import HorizonOidcLoginKeywords
from keywords.cloud_platform.security.oidc_login.objects.stx_oidc_role_context import StxOidcRoleContext
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords
from web_pages.horizon.admin.platform.horizon_fault_management_page import HorizonFaultManagementPage
from web_pages.horizon.admin.platform.horizon_host_inventory_page import HorizonHostInventoryPage


def _apply_ldap_dex_override(ssh_connection: SSHConnection, config: DexConfig) -> None:
    """Configure the Local LDAP DEX connector (id 'ldap-1') by applying the LDAP dex override.

    Fills the framework LDAP override template with the lab management IP, LDAP
    bind password, and attribute mappings, then applies it and re-applies
    oidc-auth-apps so DEX serves the ldap-1 connector.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        config (DexConfig): DEX connector configuration object.
    """
    yaml_keywords = YamlKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    dex_keywords = DexConnectorKeywords(ssh_connection)

    working_dir = config.get_working_dir()
    file_keywords.create_directory(working_dir)

    template = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-ldap-attr-mapping-overrides.yaml")
    mgmt_ip = SystemAddrpoolListKeywords(ssh_connection).get_system_addrpool_list().get_management_floating_address()
    if ":" in mgmt_ip:
        mgmt_ip = f"[{mgmt_ip}]"
    replacements = {
        "mgmt_ip": mgmt_ip,
        "bind_pw": KeyringKeywords(ssh_connection).get_keyring(service="ldap", identifier="ldapadmin"),
        "email_attr": config.get_local_ldap().get_email_attr(),
        "name_attr": config.get_local_ldap().get_name_attr(),
    }
    override_file = yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-ldap-horizon-oidc.yaml", working_dir)
    dex_keywords.apply_dex_override_and_reapply(override_file, config.get_oidc_app_name(), config.get_namespace())


def _refresh_oauth2_proxy(ssh_connection: SSHConnection) -> None:
    """Restart the oauth2-proxy pods and wait for them to become Running.

    Re-applying oidc-auth-apps can leave the stx-oauth2-proxy pods holding a
    stale upstream connection to Keystone, which makes Horizon WebSSO return a
    502 (see CGTS-105762). Deleting the pods forces a fresh upstream connection
    so the federation login through oauth2-proxy succeeds.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
    """
    namespace = "kube-system"
    label = "app=oauth2-proxy"
    get_logger().log_test_case_step("Refresh oauth2-proxy pods (avoid stale upstream to keystone - CGTS-105762)")
    get_pods = KubectlGetPodsKeywords(ssh_connection)
    delete_pods = KubectlDeletePodsKeywords(ssh_connection)

    pods = get_pods.get_pods(namespace=namespace, label=label).get_pods()
    for pod in pods:
        get_logger().log_info(f"Deleting oauth2-proxy pod {pod.get_name()}")
        delete_pods.delete_pod(pod.get_name(), namespace=namespace)

    # Wait only for the oauth2-proxy pods (by name prefix) to come back Running —
    # not all of kube-system, which includes Completed cron-job pods.
    get_pods.wait_for_pods_to_reach_status("Running", pod_names=["stx-oauth2-proxy"], namespace=namespace, timeout=180)
    # Brief settle so the fresh pod is serving (not just Running) before login.
    time.sleep(10)


def _setup_ldap_oidc_horizon(ssh_connection: SSHConnection, group_name: str, stx_role: str) -> StxOidcRoleContext:
    """Set up an LDAP user + group + DEX ldap-1 connector + keystone role-bindings for Horizon OIDC.

    Creates the LDAP user/group, configures the ldap-1 DEX connector, sets the
    oidc-username-claim, and applies identity/stx role-bindings for the given
    role. Horizon WebSSO authorizes via keystone role-bindings, so no Kubernetes
    ClusterRoleBinding is created here. The Horizon URL (port 8443) is stored on
    the returned context. Teardown callables are returned for the caller to
    register in LIFO order.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        group_name (str): LDAP group name bound to the keystone role.
        stx_role (str): STX role to bind (e.g. 'admin').

    Returns:
        StxOidcRoleContext: Context with the Horizon URL, user, and teardown callables.
    """
    lab_config = ConfigurationManager.get_lab_config()
    dex_config = ConfigurationManager.get_security_config().get_dex_connector_config()
    test_user = dex_config.get_test_user()
    admin_password = lab_config.get_admin_credentials().get_password()

    ldap_keywords = LdapKeywords(ssh_connection, admin_password)
    dex_keywords = DexConnectorKeywords(ssh_connection)
    oidc_setup = OidcSetupKeywords(ssh_connection)
    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        ldap_cleanup = LdapKeywords(ssh, admin_password)
        ldap_cleanup.delete_user(test_user.get_username())
        ldap_cleanup.delete_group(group_name)
        FileKeywords(ssh).delete_directory(dex_config.get_working_dir())

    get_logger().log_test_case_step(f"Create LDAP user/group and add user to group ({group_name})")
    ldap_keywords.create_user(test_user.get_username(), test_user.get_password(), user_role=test_user.get_role())
    ldap_keywords.add_mail_attribute(test_user.get_username(), test_user.get_email())
    ldap_keywords.create_group(group_name)
    ldap_keywords.add_user_to_group(test_user.get_username(), group_name)

    get_logger().log_test_case_step("Configure the Local LDAP DEX connector (ldap-1) and re-apply oidc-auth-apps")
    _apply_ldap_dex_override(ssh_connection, dex_config)
    dex_keywords.set_oidc_username_claim(dex_config.get_oidc_username_claim().get_default())

    get_logger().log_test_case_step(f"Set up identity/stx role-bindings ({group_name} -> {stx_role})")
    role_bindings_teardown = oidc_setup.setup_role_bindings(group_name, stx_role)

    # Re-applying oidc-auth-apps + restarting keystone can leave oauth2-proxy with
    # a stale upstream connection. Refresh it before the browser login.
    _refresh_oauth2_proxy(ssh_connection)

    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    horizon_url = f"https://{bracketed_ip}:8443"
    # Order matters: [role_bindings_teardown, cleanup]. The caller registers them
    # in this order so (LIFO) cleanup runs first (keystone up) and the
    # keystone-restarting role-bindings teardown runs last.
    return StxOidcRoleContext(test_user, horizon_url, oam_ip, "ldap-1", [role_bindings_teardown, cleanup])


def _setup_wad_oidc_horizon(ssh_connection: SSHConnection, group_name: str, stx_role: str) -> StxOidcRoleContext:
    """Set up the WAD DEX connector + keystone role-bindings for a Horizon OIDC login test.

    Unlike LDAP, the WAD user/group already exist in Active Directory, so this only
    applies the WAD DEX connector override, ensures the WAD user's mail attribute,
    sets the oidc-username-claim, and applies identity/stx role-bindings for the
    given role. Horizon WebSSO authorizes via keystone role-bindings, so no
    Kubernetes ClusterRoleBinding is created. The oauth2-proxy pods are refreshed
    before login, and the Horizon URL (port 8443) is stored on the returned context.
    Teardown callables are returned for the caller to register in LIFO order.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        group_name (str): WAD group name bound to the keystone role.
        stx_role (str): STX role to bind (e.g. 'admin').

    Returns:
        StxOidcRoleContext: Context with the Horizon URL, user, and teardown callables.
    """
    lab_config = ConfigurationManager.get_lab_config()
    dex_config = ConfigurationManager.get_security_config().get_dex_connector_config()
    wad_connector = dex_config.get_wad_connector()
    wad_user = dex_config.get_wad_test_user()

    wad_keywords = WadConnectorKeywords(ssh_connection)
    dex_keywords = DexConnectorKeywords(ssh_connection)
    oidc_setup = OidcSetupKeywords(ssh_connection)
    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up WAD test resources")
        FileKeywords(ssh).delete_directory(dex_config.get_working_dir())

    get_logger().log_test_case_step("Configure the WAD DEX connector and re-apply oidc-auth-apps")
    wad_keywords.apply_wad_override(dex_config, wad_connector.get_email_attr(), wad_connector.get_username_attr(), wad_connector.get_name_attr())
    wad_keywords.ensure_wad_user_mail_attribute(dex_config, wad_user.get_username(), wad_user.get_email())
    dex_keywords.set_oidc_username_claim(dex_config.get_oidc_username_claim().get_default())

    get_logger().log_test_case_step(f"Set up identity/stx role-bindings ({group_name} -> {stx_role})")
    role_bindings_teardown = oidc_setup.setup_role_bindings(group_name, stx_role)

    # Re-applying oidc-auth-apps + restarting keystone can leave oauth2-proxy with
    # a stale upstream connection. Refresh it before the browser login.
    _refresh_oauth2_proxy(ssh_connection)

    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    horizon_url = f"https://{bracketed_ip}:8443"
    # Order matters: [role_bindings_teardown, cleanup]. The caller registers them
    # in this order so (LIFO) cleanup runs first (keystone up) and the
    # keystone-restarting role-bindings teardown runs last.
    return StxOidcRoleContext(wad_user, horizon_url, oam_ip, wad_connector.get_connector_id(), [role_bindings_teardown, cleanup])


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


def _setup_oidc_keycloak_environment(ssh_connection: SSHConnection, security_config: SecurityConfig, lab_config: LabConfig) -> str:
    """Set up the full OIDC Keycloak environment on the remote host.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
        lab_config (LabConfig): Lab configuration object.

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
        kubeconfig_filename=security_config.get_oidc_keycloak_kubeconfig_filename(),
        oidc_client_id=security_config.get_oidc_keycloak_static_client_id(),
        oidc_client_secret=security_config.get_oidc_keycloak_static_client_secret(),
        crb_binding_name=security_config.get_oidc_keycloak_crb_binding_name(),
        crb_cluster_role=security_config.get_oidc_keycloak_crb_cluster_role(),
        crb_group=security_config.get_oidc_keycloak_crb_group(),
    )


def _cleanup_oidc_keycloak_environment(ssh_connection: SSHConnection, security_config: SecurityConfig) -> None:
    """Clean up the OIDC Keycloak environment and restore the lab to a safe state.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
    """
    OidcEnvironmentKeywords(ssh_connection).teardown(
        oidc_app_name="oidc-auth-apps",
        namespace=security_config.get_oidc_keycloak_namespace(),
    )


def _setup_keycloak_oidc_horizon(ssh_connection: SSHConnection, security_config: SecurityConfig, lab_config: LabConfig, stx_role: str) -> StxOidcRoleContext:
    """Set up the Keycloak OIDC environment + keystone role-bindings for a Horizon OIDC login test.

    Resets the test user's OTP + brute-force lockout for a clean MFA enrollment,
    sets up the full OIDC Keycloak environment (oidc-auth-apps + kubeconfig + CRB),
    then binds the Keycloak keystone group (crb_group) to the given STX role so the
    browser-login user is authorized for Horizon. The oauth2-proxy pods are
    refreshed before login, and the Horizon URL (port 8443) is stored on the
    returned context. Teardown callables are returned for the caller to register
    in LIFO order.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
        lab_config (LabConfig): Lab configuration object.
        stx_role (str): STX role to bind (e.g. 'admin').

    Returns:
        StxOidcRoleContext: Context with the Horizon URL, user, and teardown callables.
    """
    username = security_config.get_oidc_keycloak_test_username()
    password = security_config.get_oidc_keycloak_test_password()
    group_name = security_config.get_oidc_keycloak_crb_group()
    oidc_setup = OidcSetupKeywords(ssh_connection)

    get_logger().log_test_case_step("Reset Keycloak OTP and clear brute-force lockout for the test user")
    keycloak_admin = _get_keycloak_admin(security_config)
    keycloak_admin.delete_user_otp_credentials(username)
    keycloak_admin.clear_user_brute_force_lockout(username)

    get_logger().log_test_case_step("Set up the OIDC Keycloak environment (oidc-auth-apps + kubeconfig + CRB)")
    _setup_oidc_keycloak_environment(ssh_connection, security_config, lab_config)

    def env_cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Restoring OIDC Keycloak environment")
        _cleanup_oidc_keycloak_environment(ssh, security_config)

    get_logger().log_test_case_step(f"Set up identity/stx role-bindings ({group_name} -> {stx_role})")
    role_bindings_teardown = oidc_setup.setup_role_bindings(group_name, stx_role)

    # Re-applying oidc-auth-apps + restarting keystone can leave oauth2-proxy with
    # a stale upstream connection. Refresh it before the browser login.
    _refresh_oauth2_proxy(ssh_connection)

    oam_ip = lab_config.get_floating_ip()
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    horizon_url = f"https://{bracketed_ip}:8443"
    keycloak_user = DexTestUser({"username": username, "password": password})
    # Order matters: [role_bindings_teardown, env_cleanup]. The caller registers
    # them in this order so (LIFO) env_cleanup runs first while keystone is up and
    # the keystone-restarting role-bindings teardown runs last.
    return StxOidcRoleContext(keycloak_user, horizon_url, oam_ip, "keycloak", [role_bindings_teardown, env_cleanup])


@mark.p1
def test_horizon_oidc_login_ldap_backend(request: FixtureRequest):
    """Verify Horizon WebSSO OIDC login via the Local LDAP connector loads the dashboard.

    Sets up an LDAP user bound to the admin role and the ldap-1 DEX connector,
    then logs into Horizon through the browser OIDC flow (OpenID Connect auth
    method -> DEX connector select -> DEX-native login -> Grant Access) and
    validates the Horizon dashboard loads.

    Teardown:
        - Delete the LDAP user/group, working dir, and role-bindings
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ctx = _setup_ldap_oidc_horizon(ssh_connection, "Level1SystemAdmin", "admin")
    # LIFO: register role-bindings teardown FIRST so it runs LAST (it restarts
    # keystone); cleanup runs first while keystone is still up.
    for teardown in ctx.get_teardowns():
        request.addfinalizer(teardown)

    test_user = ctx.get_test_user()
    get_logger().log_test_case_step("Log into Horizon via browser OIDC login (LDAP connector)")
    dashboard_loaded = HorizonOidcLoginKeywords(ssh_connection).login_to_horizon_via_oidc(
        horizon_url=ctx.get_login_url(),
        username=test_user.get_username(),
        password=test_user.get_password(),
        connector=ctx.get_connector_id(),
    )

    get_logger().log_test_case_step("Validate the Horizon dashboard loaded after OIDC login")
    validate_equals(dashboard_loaded, True, "Horizon dashboard should load after LDAP OIDC browser login")


@mark.p2
def test_horizon_oidc_login_wad_backend(request: FixtureRequest):
    """Verify Horizon WebSSO OIDC login via the WAD connector loads the dashboard.

    Sets up the WAD DEX connector with the WAD group bound to the admin role, then
    logs into Horizon through the browser OIDC flow (OpenID Connect auth method ->
    DEX connector select -> DEX-native login -> Grant Access) as the AD test user
    and validates the Horizon dashboard loads.

    Teardown:
        - Delete the working dir and role-bindings
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ctx = _setup_wad_oidc_horizon(ssh_connection, "Level1SystemAdmin", "admin")
    # LIFO: register role-bindings teardown FIRST so it runs LAST (it restarts
    # keystone); cleanup runs first while keystone is still up.
    for teardown in ctx.get_teardowns():
        request.addfinalizer(teardown)

    test_user = ctx.get_test_user()
    get_logger().log_test_case_step("Log into Horizon via browser OIDC login (WAD connector)")
    dashboard_loaded = HorizonOidcLoginKeywords(ssh_connection).login_to_horizon_via_oidc(
        horizon_url=ctx.get_login_url(),
        username=test_user.get_username(),
        password=test_user.get_password(),
        connector=ctx.get_connector_id(),
    )

    get_logger().log_test_case_step("Validate the Horizon dashboard loaded after OIDC login")
    validate_equals(dashboard_loaded, True, "Horizon dashboard should load after WAD OIDC browser login")


@mark.p2
def test_horizon_oidc_login_keycloak_backend(request: FixtureRequest):
    """Verify Horizon WebSSO OIDC login via the external Keycloak IdP loads the dashboard.

    Sets up the OIDC Keycloak environment (oidc-auth-apps + kubeconfig + CRB),
    resets OTP + brute-force lockout for a clean MFA enrollment, binds the Keycloak
    keystone group to the admin role, then logs into Horizon through the browser
    OIDC flow (OpenID Connect auth method -> DEX connector select -> Keycloak
    redirect login with TOTP -> Grant Access) and validates the Horizon dashboard
    loads.

    Teardown:
        - Remove the role-bindings, restore the OIDC Keycloak environment
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    totp_secret = security_config.get_oidc_keycloak_test_totp_secret()

    ctx = _setup_keycloak_oidc_horizon(ssh_connection, security_config, lab_config, "admin")
    # LIFO: register role-bindings teardown FIRST so it runs LAST (it restarts
    # keystone); env_cleanup runs first while keystone is still up.
    for teardown in ctx.get_teardowns():
        request.addfinalizer(teardown)

    test_user = ctx.get_test_user()
    get_logger().log_test_case_step("Log into Horizon via browser OIDC login (Keycloak connector)")
    dashboard_loaded = HorizonOidcLoginKeywords(ssh_connection).login_to_horizon_via_oidc(
        horizon_url=ctx.get_login_url(),
        username=test_user.get_username(),
        password=test_user.get_password(),
        connector=ctx.get_connector_id(),
        totp_secret=totp_secret,
    )

    get_logger().log_test_case_step("Validate the Horizon dashboard loaded after OIDC login")
    validate_equals(dashboard_loaded, True, "Horizon dashboard should load after Keycloak OIDC browser login")


@mark.p2
def test_horizon_oidc_admin_navigate_fault_management(request: FixtureRequest):
    """Verify an admin OIDC user can navigate to the Fault Management (Active Alarms) tab.

    Logs into Horizon via the LDAP OIDC flow as an admin-role user, keeps the
    browser session open, then navigates to Admin -> Fault Management -> Active
    Alarms and validates the alarms table loads (navigation completes and the
    Angular table renders). This exercises post-login tab navigation, not just
    the dashboard landing.

    Teardown:
        - Quit the browser session
        - Delete the LDAP user/group, working dir, and role-bindings
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ctx = _setup_ldap_oidc_horizon(ssh_connection, "Level1SystemAdmin", "admin")
    # LIFO: register role-bindings teardown FIRST so it runs LAST (it restarts
    # keystone); cleanup runs first while keystone is still up.
    for teardown in ctx.get_teardowns():
        request.addfinalizer(teardown)

    test_user = ctx.get_test_user()
    get_logger().log_test_case_step("Log into Horizon via browser OIDC login (LDAP connector) and keep the session")
    driver = HorizonOidcLoginKeywords(ssh_connection).login_and_get_driver(
        horizon_url=ctx.get_login_url(),
        username=test_user.get_username(),
        password=test_user.get_password(),
        connector=ctx.get_connector_id(),
    )
    request.addfinalizer(driver.quit)

    get_logger().log_test_case_step("Navigate to Admin -> Fault Management -> Active Alarms")
    fault_page = HorizonFaultManagementPage(driver)
    fault_page.navigate_to_active_alarms_page()

    get_logger().log_test_case_step("Validate the active alarms page loaded (navigation succeeded)")
    validate_equals(":8443" in driver.get_current_url() and "active_alarms" in driver.get_current_url(), True, "Admin should land on the Active Alarms page after navigation")


@mark.p2
def test_horizon_oidc_admin_navigate_host_inventory(request: FixtureRequest):
    """Verify an admin OIDC user can navigate to the Host Inventory tab and read the hosts table.

    Logs into Horizon via the LDAP OIDC flow as an admin-role user, keeps the
    browser session open, navigates to Admin -> Platform -> Host Inventory, and
    validates the controller hosts table renders with headers. This confirms an
    admin can both reach the inventory tab and read its content.

    Teardown:
        - Quit the browser session
        - Delete the LDAP user/group, working dir, and role-bindings
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ctx = _setup_ldap_oidc_horizon(ssh_connection, "Level1SystemAdmin", "admin")
    # LIFO: register role-bindings teardown FIRST so it runs LAST (it restarts
    # keystone); cleanup runs first while keystone is still up.
    for teardown in ctx.get_teardowns():
        request.addfinalizer(teardown)

    test_user = ctx.get_test_user()
    get_logger().log_test_case_step("Log into Horizon via browser OIDC login (LDAP connector) and keep the session")
    driver = HorizonOidcLoginKeywords(ssh_connection).login_and_get_driver(
        horizon_url=ctx.get_login_url(),
        username=test_user.get_username(),
        password=test_user.get_password(),
        connector=ctx.get_connector_id(),
    )
    request.addfinalizer(driver.quit)

    get_logger().log_test_case_step("Navigate to Admin -> Platform -> Host Inventory")
    inventory_page = HorizonHostInventoryPage(driver)
    inventory_page.navigate_to_host_inventory_page()

    get_logger().log_test_case_step("Validate the controller hosts table rendered with headers")
    headers = inventory_page.get_controller_hosts_table_headers()
    get_logger().log_info(f"Host inventory table headers: {headers}")
    validate_equals(len(headers) > 0, True, "Admin should see the controller hosts table headers in Host Inventory")
