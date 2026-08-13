"""Keywords for retrieving host PV information via REST API."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.bare_metal.pvs.objects.host_pv_output import HostPvOutput
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetHostPvsKeywords(BaseKeyword):
    """Keywords for retrieving host physical volume information via REST API."""

    def __init__(self):
        """Initialize GetHostPvsKeywords with configuration URL."""
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_host_pvs(self, host_id: str) -> HostPvOutput:
        """Get host physical volumes using the REST API.

        Args:
            host_id (str): The UUID of the host.

        Returns:
            HostPvOutput: Parsed PV output with HostPvObject list.
        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/ihosts/{host_id}/ipvs")
        self.validate_success_status_code(response)
        return HostPvOutput(response)
