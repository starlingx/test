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
    in, and 'system host-list' returns controller hosts.

    Steps:
        - Create an LDAP user and set the default oidc-username-claim
        - Create a cluster-admin ClusterRoleBinding for the issuer-prefixed username
        - Run 'system host-list' in the background (starts the OAM listener)
        - Select the LDAP connector and complete the DEX-native login via Selenium
        - Validate the command output contains controller hosts
    Teardown:
        - Delete the ClusterRoleBinding, the LDAP user, and the working dir
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    dex_config = ConfigurationManager.get_security_config().get_dex_connector_config()
    test_user = dex_config.get_test_user()
    admin_password = lab_config.get_admin_credentials().get_password()

    ldap_keywords = LdapKeywords(ssh_connection, admin_password)
    dex_keywords = DexConnectorKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    oidc_setup = OidcSetupKeywords(ssh_connection)

    oam_ip = lab_config.get_floating_ip()
    # Local LDAP DEX connector id from the framework LDAP override template.
    ldap_connector_id = "ldap-1"
    # LDAP group mapped to a keystone role via the identity/stx role-bindings.
    # Platform ('system') commands are authorized through keystone, so the OIDC
    # user must belong to a group that is bound to a keystone role (admin here).
    group_name = "Level1SystemAdmin"
    stx_role = "admin"

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_teardown_step("Cleaning up test resources")
        KubectlCreateClusterRoleBindingKeywords(ssh).delete_clusterrolebinding(test_user.get_crb_name())
        ldap_cleanup = LdapKeywords(ssh, admin_password)
        ldap_cleanup.delete_user(test_user.get_username())
        ldap_cleanup.delete_group(group_name)
        FileKeywords(ssh).delete_directory(dex_config.get_working_dir())

    get_logger().log_test_case_step("Create LDAP user, group, and add user to group")
    ldap_keywords.create_user(test_user.get_username(), test_user.get_password(), user_role=test_user.get_role())
    ldap_keywords.add_mail_attribute(test_user.get_username(), test_user.get_email())
    ldap_keywords.create_group(group_name)
    ldap_keywords.add_user_to_group(test_user.get_username(), group_name)

    get_logger().log_test_case_step("Configure the Local LDAP DEX connector (ldap-1) and re-apply oidc-auth-apps")
    _apply_ldap_dex_override(ssh_connection, dex_config)
    dex_keywords.set_oidc_username_claim(dex_config.get_oidc_username_claim().get_default())

    get_logger().log_test_case_step(f"Set up identity/stx role-bindings ({group_name} -> {stx_role}) for keystone authorization")
    role_bindings_teardown = oidc_setup.setup_role_bindings(group_name, stx_role)
    # Register teardowns so finalizers run in the correct order (LIFO): the
    # role-bindings teardown re-applies identity params and restarts keystone, so
    # it must run LAST. Register it FIRST here so it executes after 'cleanup'
    # (which needs keystone up to delete the keystone user).
    request.addfinalizer(role_bindings_teardown)
    request.addfinalizer(cleanup)

    # CRB must use the issuer-prefixed username: kube-apiserver resolves OIDC users as <issuer>#<claim_value>
    bracketed_ip = f"[{oam_ip}]" if ":" in oam_ip else oam_ip
    oidc_issuer = f"https://{bracketed_ip}:30556/dex"
    crb_keywords.create_clusterrolebinding_for_user(test_user.get_crb_name(), "cluster-admin", f"{oidc_issuer}#{test_user.get_username()}")

    login_url = f"http://{bracketed_ip}:8000/"

    get_logger().log_test_case_step("Run 'system host-list' with browser-based OIDC login via LDAP connector")
    result = StxOidcLoginKeywords(ssh_connection).run_stx_command_with_browser_login(
        stx_cli_cmd="system host-list",
        login_url=login_url,
        oam_ip=oam_ip,
        username=test_user.get_username(),
        password=test_user.get_password(),
        connector=ldap_connector_id,
        is_keycloak=False,
        totp_secret=None,
    )
    get_logger().log_info(f"system host-list output:\n{result.get_output()}")

    get_logger().log_test_case_step("Validate 'system host-list' returned controller hosts")
    validate_equals("controller" in result.get_output(), True, "system host-list should return controller hosts after LDAP OIDC browser login")
