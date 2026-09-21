class O2DeploymentManagerObject:
    """Represents a single O2 IMS deployment manager.

    Models only the field the tests assert (`deploymentManagerId`);
    `supportedLocations` is intentionally not modelled.
    """

    def __init__(self, deployment_manager_id: str):
        """Constructor.

        Args:
            deployment_manager_id (str): The deploymentManagerId value.
        """
        self.deployment_manager_id = deployment_manager_id

    def get_deployment_manager_id(self) -> str:
        """Get the deployment manager id.

        Returns:
            str: The deploymentManagerId value.
        """
        return self.deployment_manager_id
