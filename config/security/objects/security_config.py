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
