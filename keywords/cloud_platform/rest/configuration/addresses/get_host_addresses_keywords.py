from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.configuration.addresses.objects.host_address_output import HostAddressOutput
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetHostAddressesKeywords(BaseKeyword):
    """Keywords for retrieving host address information via REST API."""

    def __init__(self):
        """Initialize GetHostAddressesKeywords with configuration URL."""
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_host_addresses(self, host_id: str) -> HostAddressOutput:
        """Get host addresses using the REST API.

        Args:
            host_id (str): The UUID or ID of the host to retrieve addresses for.

        Returns:
            HostAddressOutput: Object containing the host's address information.
        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/ihosts/{host_id}/addresses")
        self.validate_success_status_code(response)
        host_address_output = HostAddressOutput(response)
        return host_address_output
