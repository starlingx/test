from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from keywords.cloud_platform.system.host.objects.system_host_disk_output import SystemHostDiskOutput


class GetHostDisksKeywords(BaseKeyword):
    """Keywords for retrieving host disk information via REST API."""

    def __init__(self):
        """Initialize GetHostDisksKeywords with bare metal URL."""
        self.bare_metal_base_url = GetRestUrlKeywords().get_bare_metal_url()

    def get_disks(self, host_id: str) -> SystemHostDiskOutput:
        """Get host disks using the REST API.

        Args:
            host_id (str): The UUID or ID of the host to retrieve disks for.

        Returns:
            SystemHostDiskOutput: Object containing the host's disk information.
        """
        response = CloudRestClient().get(f"{self.bare_metal_base_url}/ihosts/{host_id}/idisks")
        self.validate_success_status_code(response)
        system_host_disk_output = SystemHostDiskOutput(response)

        return system_host_disk_output
