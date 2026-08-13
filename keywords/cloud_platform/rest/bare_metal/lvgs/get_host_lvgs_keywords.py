"""Keywords for retrieving host LVG information via REST API."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.bare_metal.lvgs.objects.host_lvg_output import HostLvgOutput
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetHostLvgsKeywords(BaseKeyword):
    """Keywords for retrieving host LVG information via REST API."""

    def __init__(self):
        """Initialize GetHostLvgsKeywords with configuration URL."""
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_host_lvgs(self, host_id: str) -> HostLvgOutput:
        """Get host LVGs using the REST API.

        Args:
            host_id (str): The UUID of the host.

        Returns:
            HostLvgOutput: Parsed LVG output with HostLvgObject list.
        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/ihosts/{host_id}/ilvgs")
        self.validate_success_status_code(response)
        return HostLvgOutput(response)
