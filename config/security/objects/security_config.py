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
