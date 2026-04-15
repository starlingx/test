import json5


class SecurityConfig:
    """Class to hold configuration for Security tests."""

    def __init__(self, config: str):
        """Initialize security configuration.

        Args:
            config (str): Path to configuration file.
        """
        with open(config) as json_data:
            security_dict = json5.load(json_data)
        self.domain_name = security_dict["domain_name"]
        self.stepca_server_url = security_dict["stepca_server_url"]
        self.stepca_server_issuer = security_dict["stepca_server_issuer"]

        # Nginx ingress configuration
        nginx_config = security_dict.get("nginx_ingress", {})
        self.nginx_https_test = nginx_config.get("https_test", {})
        self.nginx_http_test = nginx_config.get("http_test", {})
        self.nginx_external_ca_test = nginx_config.get("external_ca_test", {})

        # Portieris configuration
        portieris_config = security_dict.get("portieris", {})
        self.portieris_registry_hostname = portieris_config.get("registry_server_hostname", "")
        self.portieris_registry_port = portieris_config.get("registry_server_port", "")
        self.portieris_trust_server = portieris_config.get("trust_server", "")
        self.portieris_signed_image_name = portieris_config.get("signed_image_name", "")
        self.portieris_unsigned_image_name = portieris_config.get("unsigned_image_name", "")
        self.portieris_registry_credentials = portieris_config.get("registry_credentials", {})
        self.portieris_registry_ca_cert = portieris_config.get("registry_ca_cert", "")

        # OIDC Keycloak configuration
        oidc_keycloak_config = security_dict.get("oidc_keycloak", {})
        self.oidc_keycloak_remote_user_home = oidc_keycloak_config.get("remote_user_home", "")
        self.oidc_keycloak_working_dir = oidc_keycloak_config.get("working_dir", f"{self.oidc_keycloak_remote_user_home}/oidc-keycloak/")
        self.oidc_keycloak_namespace = oidc_keycloak_config.get("namespace", "kube-system")
        self.oidc_keycloak_upstream_idp_ca_secret_name = oidc_keycloak_config.get("upstream_idp_ca_secret_name", "oidc-upstream-idp-ca")
        self.oidc_keycloak_upstream_idp_ca_filename = oidc_keycloak_config.get("upstream_idp_ca_filename", "upstream-ca.crt")
        self.oidc_keycloak_client_id = oidc_keycloak_config.get("client_id", "")
        self.oidc_keycloak_client_secret = oidc_keycloak_config.get("client_secret", "")
        self.oidc_keycloak_external_idp_issuer_url = oidc_keycloak_config.get("external_idp_issuer_url", "")
        self.oidc_keycloak_ca_cert = oidc_keycloak_config.get("keycloak_ca_cert", "")
        self.oidc_keycloak_oidc_auth_apps_certificate_secret_name = oidc_keycloak_config.get("oidc_auth_apps_certificate_secret_name", "oidc-auth-apps-certificate")
        crb_config = oidc_keycloak_config.get("cluster_role_binding", {})
        self.oidc_keycloak_crb_binding_name = crb_config.get("binding_name", "crb_binding_name")
        self.oidc_keycloak_crb_cluster_role = crb_config.get("cluster_role", "cluster-admin")
        self.oidc_keycloak_crb_group = crb_config.get("group", "crb_group")
        self.oidc_keycloak_system_local_ca_cert_filename = oidc_keycloak_config.get("system_local_ca_cert_filename", "system-local-ca.crt")
        self.oidc_keycloak_kubeconfig_filename = oidc_keycloak_config.get("kubeconfig_filename", "local-oidc-login-kubeconfig.yml")
        self.oidc_keycloak_remote_kubeconfig_filename = oidc_keycloak_config.get("remote_kubeconfig_filename", "remote-oidc-login-kubeconfig.yml")
        self.oidc_keycloak_kubelogin_download_url = oidc_keycloak_config.get("kubelogin_download_url", "")
        self.oidc_keycloak_login_port = oidc_keycloak_config.get("oidc_login_port", 8000)
        self.oidc_keycloak_invalid_issuer_url = oidc_keycloak_config.get("invalid_issuer_url", "https://invalid-issuer.example.com/realms/nonexistent")
        self.oidc_keycloak_admin_username = oidc_keycloak_config.get("admin", {}).get("username", "admin")
        self.oidc_keycloak_admin_password = oidc_keycloak_config.get("admin", {}).get("password", "admin")
        test_user_config = oidc_keycloak_config.get("test_user", {})
        self.oidc_keycloak_test_username = test_user_config.get("username", "")
        self.oidc_keycloak_test_password = test_user_config.get("password", "")
        self.oidc_keycloak_test_totp_secret = test_user_config.get("totp_secret", "")
        admin2_user_config = oidc_keycloak_config.get("admin2_user", {})
        self.oidc_keycloak_admin2_username = admin2_user_config.get("username", "")
        self.oidc_keycloak_admin2_password = admin2_user_config.get("password", "")
        self.oidc_keycloak_admin2_totp_secret = admin2_user_config.get("totp_secret", "")
        operator_user_config = oidc_keycloak_config.get("operator_user", {})
        self.oidc_keycloak_operator_username = operator_user_config.get("username", "")
        self.oidc_keycloak_operator_password = operator_user_config.get("password", "")
        self.oidc_keycloak_operator_totp_secret = operator_user_config.get("totp_secret", "")
        operator_rbac_config = oidc_keycloak_config.get("operator_rbac", {})
        self.oidc_keycloak_operator_cluster_role_name = operator_rbac_config.get("cluster_role_name", "cluster-operator")
        self.oidc_keycloak_operator_crb_binding_name = operator_rbac_config.get("binding_name", "wrcp-operator-binding")
        self.oidc_keycloak_operator_crb_group = operator_rbac_config.get("group", "/wrcp-operator")
        guard_user_config = oidc_keycloak_config.get("guard_user", {})
        self.oidc_keycloak_guard_username = guard_user_config.get("username", "")
        self.oidc_keycloak_guard_password = guard_user_config.get("password", "")
        self.oidc_keycloak_guard_totp_secret = guard_user_config.get("totp_secret", "")
        disabled_user_config = oidc_keycloak_config.get("disabled_user", {})
        self.oidc_keycloak_disabled_username = disabled_user_config.get("username", "")
        self.oidc_keycloak_disabled_password = disabled_user_config.get("password", "")
        self.oidc_keycloak_disabled_totp_secret = disabled_user_config.get("totp_secret", "")
        guard_rbac_config = oidc_keycloak_config.get("guard_rbac", {})
        self.oidc_keycloak_guard_cluster_role_name = guard_rbac_config.get("cluster_role_name", "cluster-guard")
        self.oidc_keycloak_guard_crb_binding_name = guard_rbac_config.get("binding_name", "wrcp-guard-binding")
        self.oidc_keycloak_guard_crb_group = guard_rbac_config.get("group", "/wrcp-guard")
        self.oidc_keycloak_connector_id = oidc_keycloak_config.get("connector_id", "keycloak")
        self.oidc_keycloak_redirect_uri = oidc_keycloak_config.get("redirect_uri", "")
        static_client_config = oidc_keycloak_config.get("static_client", {})
        self.oidc_keycloak_static_client_id = static_client_config.get("id", "stx-oidc-client-app")
        self.oidc_keycloak_static_client_name = static_client_config.get("name", "STX OIDC Client app")
        self.oidc_keycloak_static_client_secret = static_client_config.get("secret", "")
        self.oidc_keycloak_static_client_redirect_uris = static_client_config.get("redirect_uris", [])

    def get_domain_name(self) -> str:
        """Getter for the domain name.

        Returns:
            str: The domain name.
        """
        return self.domain_name

    def get_stepca_server_url(self) -> str:
        """Getter for the stepca server URL.

        Returns:
            str: StepCA server URL.
        """
        return self.stepca_server_url

    def get_stepca_server_issuer(self) -> str:
        """Getter for the stepca server issuer.

        Returns:
            str: StepCA server issuer.
        """
        return self.stepca_server_issuer

    def get_portieris_registry_hostname(self) -> str:
        """Getter for Portieris registry hostname.

        Returns:
            str: Registry hostname.
        """
        return self.portieris_registry_hostname

    def get_portieris_registry_port(self) -> str:
        """Getter for Portieris registry port.

        Returns:
            str: Registry port.
        """
        return self.portieris_registry_port

    def get_portieris_registry_server(self) -> str:
        """Getter for Portieris registry server (hostname:port).

        Returns:
            str: Registry server in hostname:port format.
        """
        return f"{self.portieris_registry_hostname}:{self.portieris_registry_port}"

    def get_portieris_trust_server(self) -> str:
        """Getter for Portieris trust server.

        Returns:
            str: Trust server URL.
        """
        return self.portieris_trust_server

    def get_portieris_signed_image_name(self) -> str:
        """Getter for Portieris signed image name.

        Returns:
            str: Signed image name.
        """
        return self.portieris_signed_image_name

    def get_portieris_registry_username(self) -> str:
        """Getter for Portieris registry username.

        Returns:
            str: Registry username.
        """
        return self.portieris_registry_credentials.get("username", "registry_username")

    def get_portieris_registry_password(self) -> str:
        """Getter for Portieris registry password.

        Returns:
            str: Registry password.
        """
        return self.portieris_registry_credentials.get("password", "registry_password")

    def get_portieris_unsigned_image_name(self) -> str:
        """Getter for Portieris unsigned image name.

        Returns:
            str: Unsigned image name.
        """
        return self.portieris_unsigned_image_name

    def get_portieris_registry_ca_cert(self) -> str:
        """Getter for Portieris registry CA certificate.

        Returns:
            str: Registry CA certificate content.
        """
        return self.portieris_registry_ca_cert

    def get_nginx_https_host_name(self) -> str:
        """Getter for nginx HTTPS test host name.

        Returns:
            str: Host name for HTTPS test.
        """
        return self.nginx_https_test.get("host_name", "konoha.rei")

    def get_nginx_https_key_file(self) -> str:
        """Getter for nginx HTTPS test key file.

        Returns:
            str: Key file name.
        """
        return self.nginx_https_test.get("key_file", "key.crt")

    def get_nginx_https_cert_file(self) -> str:
        """Getter for nginx HTTPS test cert file.

        Returns:
            str: Certificate file name.
        """
        return self.nginx_https_test.get("cert_file", "cert.crt")

    def get_nginx_https_tls_secret_name(self) -> str:
        """Getter for nginx HTTPS test TLS secret name.

        Returns:
            str: TLS secret name.
        """
        return self.nginx_https_test.get("tls_secret_name", "kanoha-secret")

    def get_nginx_https_namespace(self) -> str:
        """Getter for nginx HTTPS test namespace.

        Returns:
            str: Namespace for HTTPS test.
        """
        return self.nginx_https_test.get("namespace", "pvtest")

    def get_nginx_http_namespace(self) -> str:
        """Getter for nginx HTTP test namespace.

        Returns:
            str: Namespace for HTTP test.
        """
        return self.nginx_http_test.get("namespace", "pvtest")

    def get_nginx_external_ca_stepca_issuer(self) -> str:
        """Getter for nginx external CA test stepca issuer.

        Returns:
            str: StepCA issuer name.
        """
        return self.nginx_external_ca_test.get("stepca_issuer", "stepca-issuer")

    def get_nginx_external_ca_pod_name(self) -> str:
        """Getter for nginx external CA test pod name.

        Returns:
            str: Pod name.
        """
        return self.nginx_external_ca_test.get("pod_name", "kuard")

    def get_nginx_external_ca_cert(self) -> str:
        """Getter for nginx external CA test certificate name.

        Returns:
            str: Certificate name.
        """
        return self.nginx_external_ca_test.get("cert", "kuard-ingress-tls")

    def get_nginx_external_ca_deploy_app_file_name(self) -> str:
        """Getter for nginx external CA test deploy app file name.

        Returns:
            str: Deploy app file name.
        """
        return self.nginx_external_ca_test.get("deploy_app_file_name", "deploy_app.yaml")

    def get_nginx_external_ca_global_policy_file_name(self) -> str:
        """Getter for nginx external CA test global policy file name.

        Returns:
            str: Global policy file name.
        """
        return self.nginx_external_ca_test.get("global_policy_file_name", "global_policy.yaml")

    def get_nginx_external_ca_kuard_file_name(self) -> str:
        """Getter for nginx external CA test kuard file name.

        Returns:
            str: Kuard file name.
        """
        return self.nginx_external_ca_test.get("kuard_file_name", "kuard.yaml")

    def get_nginx_external_ca_namespace(self) -> str:
        """Getter for nginx external CA test namespace.

        Returns:
            str: Namespace for external CA test.
        """
        return self.nginx_external_ca_test.get("namespace", "pvtest")

    def get_nginx_external_ca_tls_secret_name(self) -> str:
        """Getter for nginx external CA test TLS secret name.

        Returns:
            str: TLS secret name.
        """
        return self.nginx_external_ca_test.get("tls_secret_name", "kuard-ingress-tls")

    def get_oidc_keycloak_remote_user_home(self) -> str:
        """Getter for the remote user home directory.

        Returns:
            str: Remote user home directory path.
        """
        return self.oidc_keycloak_remote_user_home

    def get_oidc_keycloak_working_dir(self) -> str:
        """Getter for OIDC Keycloak working directory on the remote host.

        Returns:
            str: Working directory path.
        """
        return self.oidc_keycloak_working_dir

    def get_oidc_keycloak_namespace(self) -> str:
        """Getter for the Kubernetes namespace used by OIDC Keycloak secrets.

        Returns:
            str: Kubernetes namespace.
        """
        return self.oidc_keycloak_namespace

    def get_oidc_keycloak_upstream_idp_ca_secret_name(self) -> str:
        """Getter for the upstream IdP CA secret name.

        Returns:
            str: Secret name for the upstream IdP CA certificate.
        """
        return self.oidc_keycloak_upstream_idp_ca_secret_name

    def get_oidc_keycloak_upstream_idp_ca_filename(self) -> str:
        """Getter for the upstream IdP CA certificate filename used as the secret key.

        Returns:
            str: Filename for the upstream CA certificate.
        """
        return self.oidc_keycloak_upstream_idp_ca_filename

    def get_oidc_keycloak_ca_cert(self) -> str:
        """Getter for the Keycloak CA certificate PEM content.

        Returns:
            str: PEM-encoded Keycloak CA certificate.
        """
        return self.oidc_keycloak_ca_cert

    def get_oidc_keycloak_client_id(self) -> str:
        """Getter for the Keycloak OIDC client ID.

        Returns:
            str: Keycloak OIDC client ID.
        """
        return self.oidc_keycloak_client_id

    def get_oidc_keycloak_client_secret(self) -> str:
        """Getter for the Keycloak OIDC client secret.

        Returns:
            str: Keycloak OIDC client secret.
        """
        return self.oidc_keycloak_client_secret

    def get_oidc_keycloak_external_idp_issuer_url(self) -> str:
        """Getter for the Keycloak realm issuer URL.

        Returns:
            str: Keycloak external IdP issuer URL.
        """
        return self.oidc_keycloak_external_idp_issuer_url

    def get_oidc_keycloak_oidc_auth_apps_certificate_secret_name(self) -> str:
        """Getter for the OIDC auth apps TLS certificate secret name.

        Returns:
            str: Secret name for the OIDC auth apps TLS certificate.
        """
        return self.oidc_keycloak_oidc_auth_apps_certificate_secret_name

    def get_oidc_keycloak_crb_binding_name(self) -> str:
        """Getter for the ClusterRoleBinding name.

        Returns:
            str: ClusterRoleBinding name.
        """
        return self.oidc_keycloak_crb_binding_name

    def get_oidc_keycloak_crb_cluster_role(self) -> str:
        """Getter for the cluster role to bind.

        Returns:
            str: Cluster role name.
        """
        return self.oidc_keycloak_crb_cluster_role

    def get_oidc_keycloak_crb_group(self) -> str:
        """Getter for the group to bind the cluster role to.

        Returns:
            str: Group name.
        """
        return self.oidc_keycloak_crb_group

    def get_oidc_keycloak_system_local_ca_cert_filename(self) -> str:
        """Getter for the system-local-ca certificate filename.

        Returns:
            str: Filename for the system-local-ca certificate.
        """
        return self.oidc_keycloak_system_local_ca_cert_filename

    def get_oidc_keycloak_kubeconfig_filename(self) -> str:
        """Getter for the local OIDC login kubeconfig filename.

        Returns:
            str: Filename for the local OIDC login kubeconfig.
        """
        return self.oidc_keycloak_kubeconfig_filename

    def get_oidc_keycloak_remote_kubeconfig_filename(self) -> str:
        """Getter for the remote OIDC login kubeconfig filename.

        Returns:
            str: Filename for the remote OIDC login kubeconfig.
        """
        return self.oidc_keycloak_remote_kubeconfig_filename

    def get_oidc_keycloak_kubelogin_download_url(self) -> str:
        """Getter for the kubelogin plugin download URL.

        Returns:
            str: Download URL for the kubelogin zip release.
        """
        return self.oidc_keycloak_kubelogin_download_url

    def get_oidc_keycloak_login_port(self) -> int:
        """Getter for the OIDC login browser port.

        Returns:
            int: Port number for the OIDC login browser URL.
        """
        return self.oidc_keycloak_login_port

    def get_oidc_keycloak_invalid_issuer_url(self) -> str:
        """Getter for the invalid issuer URL used in negative authentication tests.

        Returns:
            str: Invalid OIDC issuer URL.
        """
        return self.oidc_keycloak_invalid_issuer_url

    def get_oidc_keycloak_admin_username(self) -> str:
        """Getter for the Keycloak admin username.

        Returns:
            str: Keycloak admin username.
        """
        return self.oidc_keycloak_admin_username

    def get_oidc_keycloak_admin_password(self) -> str:
        """Getter for the Keycloak admin password.

        Returns:
            str: Keycloak admin password.
        """
        return self.oidc_keycloak_admin_password

    def get_oidc_keycloak_test_username(self) -> str:
        """Getter for the Keycloak test user username.

        Returns:
            str: Test user username.
        """
        return self.oidc_keycloak_test_username

    def get_oidc_keycloak_test_password(self) -> str:
        """Getter for the Keycloak test user password.

        Returns:
            str: Test user password.
        """
        return self.oidc_keycloak_test_password

    def get_oidc_keycloak_test_totp_secret(self) -> str:
        """Getter for the Keycloak test user TOTP secret.

        Returns:
            str: Base32-encoded TOTP secret for the test user.
        """
        return self.oidc_keycloak_test_totp_secret

    def get_oidc_keycloak_admin2_username(self) -> str:
        """Getter for the Keycloak admin2 user username.

        Returns:
            str: Admin2 user username.
        """
        return self.oidc_keycloak_admin2_username

    def get_oidc_keycloak_admin2_password(self) -> str:
        """Getter for the Keycloak admin2 user password.

        Returns:
            str: Admin2 user password.
        """
        return self.oidc_keycloak_admin2_password

    def get_oidc_keycloak_admin2_totp_secret(self) -> str:
        """Getter for the Keycloak admin2 user TOTP secret.

        Returns:
            str: Base32-encoded TOTP secret for the admin2 user.
        """
        return self.oidc_keycloak_admin2_totp_secret

    def get_oidc_keycloak_connector_id(self) -> str:
        """Getter for the DEX connector ID.

        Returns:
            str: DEX connector ID.
        """
        return self.oidc_keycloak_connector_id

    def get_oidc_keycloak_redirect_uri(self) -> str:
        """Getter for the DEX callback redirect URI.

        Returns:
            str: DEX callback redirect URI.
        """
        return self.oidc_keycloak_redirect_uri

    def get_oidc_keycloak_static_client_id(self) -> str:
        """Getter for the static OIDC client ID.

        Returns:
            str: Static OIDC client ID.
        """
        return self.oidc_keycloak_static_client_id

    def get_oidc_keycloak_static_client_name(self) -> str:
        """Getter for the static OIDC client name.

        Returns:
            str: Static OIDC client name.
        """
        return self.oidc_keycloak_static_client_name

    def get_oidc_keycloak_static_client_secret(self) -> str:
        """Getter for the static OIDC client secret.

        Returns:
            str: Static OIDC client secret.
        """
        return self.oidc_keycloak_static_client_secret

    def get_oidc_keycloak_static_client_redirect_uris(self) -> list[str]:
        """Getter for the static OIDC client redirect URIs.

        Returns:
            list[str]: List of redirect URIs for the static OIDC client.
        """
        return self.oidc_keycloak_static_client_redirect_uris

    def get_oidc_keycloak_operator_username(self) -> str:
        """Getter for the Keycloak operator user username.

        Returns:
            str: Operator user username.
        """
        return self.oidc_keycloak_operator_username

    def get_oidc_keycloak_operator_password(self) -> str:
        """Getter for the Keycloak operator user password.

        Returns:
            str: Operator user password.
        """
        return self.oidc_keycloak_operator_password

    def get_oidc_keycloak_operator_totp_secret(self) -> str:
        """Getter for the Keycloak operator user TOTP secret.

        Returns:
            str: Base32-encoded TOTP secret for the operator user.
        """
        return self.oidc_keycloak_operator_totp_secret

    def get_oidc_keycloak_operator_cluster_role_name(self) -> str:
        """Getter for the operator ClusterRole name.

        Returns:
            str: Operator ClusterRole name.
        """
        return self.oidc_keycloak_operator_cluster_role_name

    def get_oidc_keycloak_operator_crb_binding_name(self) -> str:
        """Getter for the operator ClusterRoleBinding name.

        Returns:
            str: Operator ClusterRoleBinding name.
        """
        return self.oidc_keycloak_operator_crb_binding_name

    def get_oidc_keycloak_operator_crb_group(self) -> str:
        """Getter for the operator group to bind the cluster role to.

        Returns:
            str: Operator group name.
        """
        return self.oidc_keycloak_operator_crb_group

    def get_oidc_keycloak_guard_username(self) -> str:
        """Getter for the Keycloak guard user username.

        Returns:
            str: Guard user username.
        """
        return self.oidc_keycloak_guard_username

    def get_oidc_keycloak_guard_password(self) -> str:
        """Getter for the Keycloak guard user password.

        Returns:
            str: Guard user password.
        """
        return self.oidc_keycloak_guard_password

    def get_oidc_keycloak_guard_totp_secret(self) -> str:
        """Getter for the Keycloak guard user TOTP secret.

        Returns:
            str: Base32-encoded TOTP secret for the guard user.
        """
        return self.oidc_keycloak_guard_totp_secret

    def get_oidc_keycloak_guard_cluster_role_name(self) -> str:
        """Getter for the guard ClusterRole name.

        Returns:
            str: Guard ClusterRole name.
        """
        return self.oidc_keycloak_guard_cluster_role_name

    def get_oidc_keycloak_guard_crb_binding_name(self) -> str:
        """Getter for the guard ClusterRoleBinding name.

        Returns:
            str: Guard ClusterRoleBinding name.
        """
        return self.oidc_keycloak_guard_crb_binding_name

    def get_oidc_keycloak_guard_crb_group(self) -> str:
        """Getter for the guard group to bind the cluster role to.

        Returns:
            str: Guard group name.
        """
        return self.oidc_keycloak_guard_crb_group

    def get_oidc_keycloak_disabled_username(self) -> str:
        """Getter for the Keycloak disabled user username.

        Returns:
            str: Disabled user username.
        """
        return self.oidc_keycloak_disabled_username

    def get_oidc_keycloak_disabled_password(self) -> str:
        """Getter for the Keycloak disabled user password.

        Returns:
            str: Disabled user password.
        """
        return self.oidc_keycloak_disabled_password

    def get_oidc_keycloak_disabled_totp_secret(self) -> str:
        """Getter for the Keycloak disabled user TOTP secret.

        Returns:
            str: Base32-encoded TOTP secret for the disabled user.
        """
        return self.oidc_keycloak_disabled_totp_secret
