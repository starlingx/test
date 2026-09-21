from config.configuration_manager import ConfigurationManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords

# Path prefix for the O2 IMS infrastructure inventory API.
O2_INVENTORY_PATH = "/o2ims-infrastructureInventory"


class GetO2UrlKeywords(BaseKeyword):
    """Keywords for building O2 IMS API URLs."""

    def __init__(self) -> None:
        """Initialize with the base URL derived from lab and O2 IMS config."""
        # The port is always stated explicitly: the SSH-tunnel client treats a
        # portless URL as remote port 443, which would tunnel to the wrong port.
        self.served_port = ConfigurationManager.get_o2ims_config().get_served_port()
        self.base_url = f"{GetRestUrlKeywords().get_base_url()}:{self.served_port}"

    def get_base_url(self) -> str:
        """Return the O2 IMS base URL, including the explicit served port.

        Returns:
            str: The base URL, e.g. https://<floating_ip>:30205.
        """
        return self.base_url

    def get_inventory_url(self) -> str:
        """Return the O2 IMS infrastructure inventory base URL.

        Returns:
            str: The inventory base URL, e.g. https://<floating_ip>:30205/o2ims-infrastructureInventory.
        """
        return f"{self.base_url}{O2_INVENTORY_PATH}"

    def get_inventory_endpoint_url(self, endpoint_suffix: str) -> str:
        """Return the URL for an inventory endpoint under the inventory path.

        Args:
            endpoint_suffix (str): The suffix to append after the inventory path,
                for example 'api_versions' or 'v1/resourcePools'. A leading slash
                is optional.

        Returns:
            str: The full endpoint URL.
        """
        return self._build_inventory_endpoint_url(self.base_url, endpoint_suffix)

    def get_local_inventory_endpoint_url(self, endpoint_suffix: str) -> str:
        """Return a controller-local inventory endpoint URL for on-controller curl.

        The O2 API is a controller-side NodePort reached by executing curl on the
        controller, so the request targets the controller's own loopback rather
        than the floating IP.

        Args:
            endpoint_suffix (str): The suffix to append after the inventory path,
                for example 'api_versions' or 'v1/resourcePools'. A leading slash
                is optional.

        Returns:
            str: The full controller-local endpoint URL.
        """
        return self._build_inventory_endpoint_url(f"https://localhost:{self.served_port}", endpoint_suffix)

    def _build_inventory_endpoint_url(self, base_url: str, endpoint_suffix: str) -> str:
        """Join a base URL, the inventory path and an endpoint suffix.

        Args:
            base_url (str): Scheme, host and port to build on, with no trailing slash.
            endpoint_suffix (str): The suffix to append after the inventory path. A
                leading slash is optional.

        Returns:
            str: The full endpoint URL.
        """
        suffix = endpoint_suffix.lstrip("/")
        return f"{base_url}{O2_INVENTORY_PATH}/{suffix}"
