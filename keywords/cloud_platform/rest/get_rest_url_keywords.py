from config.configuration_manager import ConfigurationManager
from keywords.base_keyword import BaseKeyword


class GetRestUrlKeywords(BaseKeyword):
    """Keywords for building REST API URLs."""

    def __init__(self) -> None:
        """Initialize GetRestUrlKeywords with base URL from lab config."""
        self.rest_api_config = ConfigurationManager.get_rest_api_config()

        lab_config = ConfigurationManager.get_lab_config()

        self.base_url = f"https://{lab_config.get_floating_ip()}"
        if lab_config.is_ipv6():
            self.base_url = f"https://[{lab_config.get_floating_ip()}]"

    def get_base_url(self) -> str:
        """Return the scheme and host of the lab's REST endpoints, without a port.

        IPv6 addresses are bracketed so a port can be appended safely.

        Returns:
            str: The base URL, e.g. https://<floating_ip> or https://[<floating_ip>].
        """
        return self.base_url

    def get_keystone_url(self) -> str:
        """Return the keystone url.

        Returns:
            str: The keystone API URL.
        """
        return f"{self.base_url}:{self.rest_api_config.get_keystone_base()}"

    def get_bare_metal_url(self) -> str:
        """Return the bare metal url.

        Returns:
            str: The bare metal API URL.
        """
        return f"{self.base_url}:{self.rest_api_config.get_bare_metal_base()}"

    def get_configuration_url(self) -> str:
        """Return the configuration url.

        Returns:
            str: The configuration API URL.
        """
        return f"{self.base_url}:{self.rest_api_config.get_configuration_base()}"

    def get_fm_url(self) -> str:
        """Return the fault management url.

        Returns:
            str: The FM API URL.
        """
        return f"{self.base_url}:{self.rest_api_config.get_fm_base()}"

    def get_barbican_url(self) -> str:
        """Return the barbican url.

        Returns:
            str: The Barbican API URL.
        """
        return f"{self.base_url}:{self.rest_api_config.get_barbican_base()}"

    def get_software_update_url(self) -> str:
        """Return the software update (patching) url.

        Returns:
            str: The software update API URL.
        """
        return f"{self.base_url}:{self.rest_api_config.get_software_update_base()}"
