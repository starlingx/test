"""Keywords for sysinv REST API endpoints without dedicated keyword classes."""

from framework.rest.rest_response import RestResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetSysinvEndpointKeywords(BaseKeyword):
    """Keywords for sysinv endpoints that don't have dedicated keyword classes."""

    def __init__(self):
        """Initialize with configuration URL."""
        self.base_url = GetRestUrlKeywords().get_configuration_url()

    def get_addrpools(self) -> RestResponse:
        """GET /addrpools.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/addrpools")
        self.validate_success_status_code(response)
        return response

    def get_storage_ceph(self) -> RestResponse:
        """GET /storage_ceph.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/storage_ceph")
        self.validate_success_status_code(response)
        return response

    def get_storage_lvm(self) -> RestResponse:
        """GET /storage_lvm.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/storage_lvm")
        self.validate_success_status_code(response)
        return response

    def get_ceph_mon(self) -> RestResponse:
        """GET /ceph_mon.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/ceph_mon")
        self.validate_success_status_code(response)
        return response

    def get_controller_fs(self) -> RestResponse:
        """GET /controller_fs.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/controller_fs")
        self.validate_success_status_code(response)
        return response

    def get_drbdconfig(self) -> RestResponse:
        """GET /drbdconfig.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/drbdconfig")
        self.validate_success_status_code(response)
        return response

    def get_health(self) -> RestResponse:
        """GET /health.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/health")
        self.validate_success_status_code(response)
        return response

    def get_health_upgrade(self) -> RestResponse:
        """GET /health/upgrade.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/health/upgrade")
        self.validate_success_status_code(response)
        return response

    def get_idns(self) -> RestResponse:
        """GET /idns.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/idns")
        self.validate_success_status_code(response)
        return response

    def get_iextoam(self) -> RestResponse:
        """GET /iextoam.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/iextoam")
        self.validate_success_status_code(response)
        return response

    def get_ihosts_bulk_export(self) -> RestResponse:
        """GET /ihosts/bulk_export.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/ihosts/bulk_export")
        self.validate_success_status_code(response)
        return response

    def get_intp(self) -> RestResponse:
        """GET /intp.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/intp")
        self.validate_success_status_code(response)
        return response

    def get_istors(self) -> RestResponse:
        """GET /istors.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/istors")
        self.validate_success_status_code(response)
        return response

    def get_remotelogging(self) -> RestResponse:
        """GET /remotelogging.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/remotelogging")
        self.validate_success_status_code(response)
        return response

    def get_sdn_controller(self) -> RestResponse:
        """GET /sdn_controller.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/sdn_controller")
        self.validate_success_status_code(response)
        return response

    def get_lldp_agents(self) -> RestResponse:
        """GET /lldp_agents.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/lldp_agents")
        self.validate_success_status_code(response)
        return response

    def get_lldp_neighbours(self) -> RestResponse:
        """GET /lldp_neighbours.

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/lldp_neighbours")
        self.validate_success_status_code(response)
        return response

    def get_root(self) -> RestResponse:
        """GET / (API root).

        Returns:
            RestResponse: The validated response.
        """
        response = CloudRestClient().get(f"{self.base_url}/")
        self.validate_success_status_code(response)
        return response
