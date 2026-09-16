from keywords.cloud_platform.rest.oran_o2.object.o2_deployment_manager_object import O2DeploymentManagerObject
from keywords.cloud_platform.rest.oran_o2.object.o2_rest_response import O2RestResponse


class O2DeploymentManagersOutput:
    """Parses the O2 IMS deploymentManagers list response into deployment manager objects."""

    def __init__(self, response: O2RestResponse):
        """Initialize from an O2 REST response.

        Accepts both shapes the endpoint returns: the list read yields an array of
        entries, while a detail read yields a single entry, which is normalized to
        a one-element list so both are read the same way.

        Args:
            response (O2RestResponse): The response from a deploymentManagers list
                or detail endpoint.
        """
        self.deployment_managers = []
        content = response.get_json_content() or []
        if isinstance(content, dict):
            content = [content]
        for entry in content:
            deployment_manager_id = entry.get("deploymentManagerId", "")
            if deployment_manager_id:
                self.deployment_managers.append(O2DeploymentManagerObject(deployment_manager_id))

    def get_deployment_managers(self) -> list[O2DeploymentManagerObject]:
        """Get all deployment manager objects.

        Returns:
            list[O2DeploymentManagerObject]: The parsed deployment managers.
        """
        return self.deployment_managers

    def is_empty(self) -> bool:
        """Return whether the deployment manager list is empty.

        Returns:
            bool: True if no deployment managers were parsed.
        """
        return len(self.deployment_managers) == 0

    def get_first(self) -> O2DeploymentManagerObject:
        """Get the first deployment manager.

        Returns:
            O2DeploymentManagerObject: The first deployment manager.

        Raises:
            ValueError: If the deployment manager list is empty.
        """
        if not self.deployment_managers:
            raise ValueError("No deployment managers were returned")
        return self.deployment_managers[0]
