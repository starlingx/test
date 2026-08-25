class StorageCapabilities:
    """
    Class for storage capabilities
    """

    def __init__(self):
        self.deployment_model = None
        self.failure_domain = None
        self.replication: int = -1
        self.min_replication: int = -1
        self.has_long_running_operations: bool = False

    def set_replication(self, replication: int):
        """
        Setter for replication

        Args:
            replication(int): replication number

        Returns: None
        """
        self.replication = replication

    def get_replication(self) -> int:
        """
        Getter for replication

        Returns:
            int: replication number
        """
        return self.replication

    def set_min_replication(self, min_replication: int):
        """
        Setter for min_replication

        Args:
            min_replication (int): min_replication number

        Returns: None
        """
        self.min_replication = min_replication

    def get_min_replication(self) -> int:
        """
        Getter for min_replication

        Returns:
            int: min_replication number
        """
        return self.min_replication

    def set_deployment_model(self, deployment_model: str):
        """
        Setter for deployment_model

        Args:
            deployment_model (str): deployment_model

        Returns: None
        """
        self.deployment_model = deployment_model

    def get_deployment_model(self) -> str:
        """
        Getter for deployment_model

        Returns:
            str: deployment_model
        """
        return self.deployment_model

    def set_failure_domain(self, failure_domain: str):
        """
        Setter for failure_domain

        Args:
            failure_domain (str): failure_domain (e.g. 'host', 'osd')

        Returns: None
        """
        self.failure_domain = failure_domain

    def get_failure_domain(self) -> str:
        """
        Getter for failure_domain

        Returns:
            str: failure_domain
        """
        return self.failure_domain

    def set_has_long_running_operations(self, has_long_running_operations: bool):
        """
        Setter for has_long_running_operations

        Args:
            has_long_running_operations (bool): has_long_running_operations

        Returns: None
        """
        self.has_long_running_operations = has_long_running_operations

    def get_has_long_running_operations(self) -> bool:
        """
        Getter for has_long_running_operations

        Returns:
            bool: has_long_running_operations
        """
        return self.has_long_running_operations
