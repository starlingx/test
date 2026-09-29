"""STX CLI OIDC login tests.

Verifies the end-to-end browser-based OIDC login flow for StarlingX platform
CLI: the oidc-login listener starts on the OAM IP, a headless Selenium browser
completes the Keycloak (MFA) login, and a 'system' platform command runs and
its output is validated.

Reuses the shared OIDC/Keycloak keywords:
    - OidcEnvironmentKeywords          (set up / tear down oidc-auth-apps + kubeconfig)
    - StxOidcLoginKeywords             (browser login + run stx command, MFA/TOTP)
    - KeycloakAdminKeywords            (reset OTP / clear brute-force lockout)
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_config import LabConfig
from config.security.objects.dex_config import DexConfig
from config.security.objects.security_config import SecurityConfig
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.keycloak.keycloak_admin_keywords import KeycloakAdminKeywords
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.security.oidc.oidc_environment_keywords import OidcEnvironmentKeywords
from keywords.cloud_platform.security.oidc.oidc_setup_keywords import OidcSetupKeywords
from keywords.cloud_platform.security.oidc_login.objects.stx_oidc_role_context import StxOidcRoleContext
from keywords.cloud_platform.security.oidc_login.stx_oidc_login_keywords import StxOidcLoginKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords


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
    override_file = yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-ldap-stx-oidc.yaml", working_dir)
    dex_keywords.apply_dex_override_and_reapply(override_file, config.get_oidc_app_name(), config.get_namespace())


def _setup_ldap_oidc_role(ssh_connection: SSHConnection, group_name: str, stx_role: str) -> StxOidcRoleContext:
    """Set up an LDAP user + group + DEX ldap-1 connector + role-bindings for a browser-login role test.

    Creates the LDAP user/group, configures the ldap-1 DEX connector, sets the
    oidc-username-claim, applies identity/stx role-bindings for the given role,
    and creates the cluster-admin ClusterRoleBinding for the issuer-prefixed user.
    Teardown callables are returned on the context so the caller registers them in
    the correct LIFO order.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        group_name (str): LDAP group name bound to the keystone role.
        stx_role (str): STX role to bind (e.g. 'reader', 'operator').

    Returns:
        StxOidcRoleContext: Context with login values and teardown callables.
    """
    lab_config = ConfigurationManager.get_lab_config()
    dex_config = ConfigurationManager.get_security_config().get_dex_connector_config()
    test_user = dex_config.get_test_user()
    admin_password = lab_config.get_admin_credentials().get_password()

    ldap_keywords = LdapKeywords(ssh_connection, admin_password)
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    oidc_setup = OidcSetupKeywords(ssh_connection)
    oam_ip = lab_config.get_floating_ip()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user.get_crb_name())
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

    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(test_user.get_crb_name(), "cluster-admin", f"{oidc_issuer}#{test_user.get_username()}")
    login_url = f"http://{bracketed_ip}:8000/"
    # Order matters: [role_bindings_teardown, cleanup]. The caller registers them
    # in this order so (LIFO) cleanup runs first (keystone up) and the
    # keystone-restarting role-bindings teardown runs last.
    return StxOidcRoleContext(test_user, login_url, oam_ip, "ldap-1", [role_bindings_teardown, cleanup])


def _run_stx_via_browser(ssh_connection: SSHConnection, ctx: StxOidcRoleContext, stx_cli_cmd: str) -> object:
    """Run an STX CLI command via browser-based LDAP OIDC login and return the result.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        ctx (StxOidcRoleContext): Context holding user/login-url/oam/connector.
        stx_cli_cmd (str): STX CLI command to run.

    Returns:
        object: KubectlResultObject with the command output.
    """
    test_user = ctx.get_test_user()
    return StxOidcLoginKeywords(ssh_connection).run_stx_command_with_browser_login(
        stx_cli_cmd=stx_cli_cmd,
        login_url=ctx.get_login_url(),
        oam_ip=ctx.get_oam_ip(),
        username=test_user.get_username(),
        password=test_user.get_password(),
        connector=ctx.get_connector_id(),
        is_keycloak=False,
        totp_secret=None,
    )


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


def _setup_oidc_environment(ssh_connection: SSHConnection, security_config: SecurityConfig, lab_config: LabConfig) -> str:
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


def _cleanup_oidc_environment(ssh_connection: SSHConnection, security_config: SecurityConfig) -> None:
    """Clean up the OIDC Keycloak environment and restore the lab to a safe state.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        security_config (SecurityConfig): Security configuration object.
    """
    OidcEnvironmentKeywords(ssh_connection).teardown(
        oidc_app_name="oidc-auth-apps",
        namespace=security_config.get_oidc_keycloak_namespace(),
    )


@mark.p1
def test_stx_oidc_login_ldap_system_host_list(request: FixtureRequest):
    """Verify 'system host-list' runs after browser-based OIDC login via the LDAP connector.

    Exercises the full flow using the Local LDAP DEX connector (DEX-native login
    form, no MFA): the oidc-login listener starts on the OAM IP when the STX CLI
    command runs, a headless Selenium browser selects the LDAP connector and logs
    in, and 'system host-list' returns controller hosts. The group is bound to the
    'admin' role so 'system host-list' is authorized.

    Teardown:
        - Delete the ClusterRoleBinding, the LDAP user/group, working dir, role-bindings
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ctx = _setup_ldap_oidc_role(ssh_connection, "Level1SystemAdmin", "admin")
    # LIFO: register role-bindings teardown FIRST so it runs LAST (it restarts
    # keystone); cleanup runs first while keystone is still up.
    for teardown in ctx.get_teardowns():
        request.addfinalizer(teardown)

    get_logger().log_test_case_step("Run 'system host-list' with browser-based OIDC login via LDAP connector")
    result = _run_stx_via_browser(ssh_connection, ctx, "system host-list")
    get_logger().log_info(f"system host-list output:\n{result.get_output()}")

    get_logger().log_test_case_step("Validate 'system host-list' returned controller hosts")
    validate_equals("controller" in result.get_output(), True, "system host-list should return controller hosts after LDAP OIDC browser login")


@mark.p2
def test_stx_oidc_login_ldap_reader_role(request: FixtureRequest):
    """Verify the reader role via browser OIDC login: read allowed, write denied.

    Binds the LDAP group to the STX 'reader' role, logs in through the browser
    DEX flow, then confirms a read command ('system service-parameter-list')
    succeeds while a write command ('system application-apply dummy-app') is
    denied with a 403/Forbidden RBAC error.

    Teardown:
        - Delete the ClusterRoleBinding, LDAP user/group, working dir, role-bindings
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ctx = _setup_ldap_oidc_role(ssh_connection, "Level1SystemReader", "reader")
    # LIFO: register role-bindings teardown FIRST so it runs LAST (it restarts
    # keystone); cleanup runs first while keystone is still up.
    for teardown in ctx.get_teardowns():
        request.addfinalizer(teardown)

    get_logger().log_test_case_step("Reader: verify read command 'system service-parameter-list' is allowed")
    read_result = _run_stx_via_browser(ssh_connection, ctx, "system service-parameter-list")
    get_logger().log_info(f"reader read output:\n{read_result.get_output()}")
    validate_equals(read_result.is_stx_forbidden(), False, "Reader must NOT be denied 'system service-parameter-list'")

    get_logger().log_test_case_step("Reader: verify write command 'system application-apply dummy-app' is denied")
    write_result = _run_stx_via_browser(ssh_connection, ctx, "system application-apply dummy-app")
    get_logger().log_info(f"reader write output:\n{write_result.get_output()}")
    validate_equals(write_result.is_stx_forbidden(), True, "Reader must be denied 'system application-apply'")


@mark.p2
def test_stx_oidc_login_ldap_operator_role(request: FixtureRequest):
    """Verify the operator role via browser OIDC login: read allowed, write denied.

    Binds the LDAP group to the STX 'operator' role (which the framework maps to
    operator+reader), logs in through the browser DEX flow, then confirms a read
    command succeeds while a config-changing write command is denied with a
    403/Forbidden RBAC error.

    Teardown:
        - Delete the ClusterRoleBinding, LDAP user/group, working dir, role-bindings
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ctx = _setup_ldap_oidc_role(ssh_connection, "Level1SystemOperator", "operator")
    # LIFO: register role-bindings teardown FIRST so it runs LAST (it restarts
    # keystone); cleanup runs first while keystone is still up.
    for teardown in ctx.get_teardowns():
        request.addfinalizer(teardown)

    get_logger().log_test_case_step("Operator: verify read command 'system service-parameter-list' is allowed")
    read_result = _run_stx_via_browser(ssh_connection, ctx, "system service-parameter-list")
    get_logger().log_info(f"operator read output:\n{read_result.get_output()}")
    validate_equals(read_result.is_stx_forbidden(), False, "Operator must NOT be denied 'system service-parameter-list'")

    get_logger().log_test_case_step("Operator: verify write command 'system application-apply dummy-app' is denied")
    write_result = _run_stx_via_browser(ssh_connection, ctx, "system application-apply dummy-app")
    get_logger().log_info(f"operator write output:\n{write_result.get_output()}")
    validate_equals(write_result.is_stx_forbidden(), True, "Operator must be denied 'system application-apply'")
