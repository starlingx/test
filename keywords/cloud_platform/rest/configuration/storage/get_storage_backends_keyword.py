from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords
from keywords.cloud_platform.system.storage.objects.system_storage_backend_output import SystemStorageBackendOutput


class GetStorageBackendKeywords(BaseKeyword):
    """Keywords for retrieving storage backend information via REST API."""

    def __init__(self):
        """Initialize GetStorageBackendKeywords with configuration URL."""
        self.configuration_base_url = GetRestUrlKeywords().get_configuration_url()

    def get_storage_backends(self) -> SystemStorageBackendOutput:
        """Get storage backends using the REST API.

        Returns:
            SystemStorageBackendOutput: Object containing storage backend information.
        """
        response = CloudRestClient().get(f"{self.configuration_base_url}/storage_backend")
        self.validate_success_status_code(response)
        storage_output = SystemStorageBackendOutput(response)

        return storage_output
