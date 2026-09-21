from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.oran_o2.o2_rest_client import O2RestClient
from keywords.cloud_platform.rest.oran_o2.o2_url_keywords import GetO2UrlKeywords
from keywords.cloud_platform.rest.oran_o2.object.o2_api_versions_output import O2ApiVersionsOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_deployment_managers_output import O2DeploymentManagersOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_ocloud_root_output import O2OcloudRootOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_resource_pools_output import O2ResourcePoolsOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_resource_types_output import O2ResourceTypesOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_resources_output import O2ResourcesOutput


class O2InventoryKeywords(BaseKeyword):
    """Keywords for O2 IMS infrastructure inventory GET operations.

    Each method issues a single authenticated GET through the O2 client (which
    executes mTLS curl on the controller), validates the response status, and
    returns the typed Output.

    A detail read returns the same Output type as the corresponding list read,
    holding the single entry, so both are read through the same getters. Tests
    that need a specific error status use the negative keywords instead, which
    return the raw response.
    """

    def __init__(self, o2_rest_client: O2RestClient):
        """Constructor.

        Args:
            o2_rest_client (O2RestClient): Client that executes the requests on the
                controller with the client certificate and Bearer token.
        """
        self.o2_rest_client = o2_rest_client
        self.url_keywords = GetO2UrlKeywords()

    def get_api_versions(self) -> O2ApiVersionsOutput:
        """Get the O2 IMS API versions.

        Returns:
            O2ApiVersionsOutput: Parsed api_versions output.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url("api_versions"))
        self.validate_success_status_code(response)
        return O2ApiVersionsOutput(response)

    def get_ocloud_root(self) -> O2OcloudRootOutput:
        """Get the O2 IMS O-Cloud root.

        Returns:
            O2OcloudRootOutput: Parsed O-Cloud root output.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url("v1/"))
        self.validate_success_status_code(response)
        return O2OcloudRootOutput(response)

    def get_resource_types(self) -> O2ResourceTypesOutput:
        """List the O2 IMS resource types.

        Returns:
            O2ResourceTypesOutput: Parsed resourceTypes list output.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url("v1/resourceTypes"))
        self.validate_success_status_code(response)
        return O2ResourceTypesOutput(response)

    def get_resource_type(self, resource_type_id: str) -> O2ResourceTypesOutput:
        """Get a single O2 IMS resource type.

        Args:
            resource_type_id (str): The resourceTypeId to retrieve.

        Returns:
            O2ResourceTypesOutput: Parsed output holding the requested resource type.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url(f"v1/resourceTypes/{resource_type_id}"))
        self.validate_success_status_code(response)
        return O2ResourceTypesOutput(response)

    def get_resource_pools(self) -> O2ResourcePoolsOutput:
        """List the O2 IMS resource pools.

        Returns:
            O2ResourcePoolsOutput: Parsed resourcePools list output.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url("v1/resourcePools"))
        self.validate_success_status_code(response)
        return O2ResourcePoolsOutput(response)

    def get_resource_pool(self, resource_pool_id: str) -> O2ResourcePoolsOutput:
        """Get a single O2 IMS resource pool.

        Args:
            resource_pool_id (str): The resourcePoolId to retrieve.

        Returns:
            O2ResourcePoolsOutput: Parsed output holding the requested resource pool.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url(f"v1/resourcePools/{resource_pool_id}"))
        self.validate_success_status_code(response)
        return O2ResourcePoolsOutput(response)

    def get_resources(self, resource_pool_id: str) -> O2ResourcesOutput:
        """List the O2 IMS resources within a resource pool.

        Args:
            resource_pool_id (str): The resourcePoolId whose resources to list.

        Returns:
            O2ResourcesOutput: Parsed resources list output.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url(f"v1/resourcePools/{resource_pool_id}/resources"))
        self.validate_success_status_code(response)
        return O2ResourcesOutput(response)

    def get_resource(self, resource_pool_id: str, resource_id: str) -> O2ResourcesOutput:
        """Get a single O2 IMS resource within a resource pool.

        Args:
            resource_pool_id (str): The resourcePoolId containing the resource.
            resource_id (str): The resourceId to retrieve.

        Returns:
            O2ResourcesOutput: Parsed output holding the requested resource.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url(f"v1/resourcePools/{resource_pool_id}/resources/{resource_id}"))
        self.validate_success_status_code(response)
        return O2ResourcesOutput(response)

    def get_deployment_managers(self) -> O2DeploymentManagersOutput:
        """List the O2 IMS deployment managers.

        Returns:
            O2DeploymentManagersOutput: Parsed deploymentManagers list output.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url("v1/deploymentManagers"))
        self.validate_success_status_code(response)
        return O2DeploymentManagersOutput(response)

    def get_deployment_manager(self, deployment_manager_id: str) -> O2DeploymentManagersOutput:
        """Get a single O2 IMS deployment manager.

        Args:
            deployment_manager_id (str): The deploymentManagerId to retrieve.

        Returns:
            O2DeploymentManagersOutput: Parsed output holding the requested deployment manager.
        """
        response = self.o2_rest_client.get(self.url_keywords.get_local_inventory_endpoint_url(f"v1/deploymentManagers/{deployment_manager_id}"))
        self.validate_success_status_code(response)
        return O2DeploymentManagersOutput(response)
