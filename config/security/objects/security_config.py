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
