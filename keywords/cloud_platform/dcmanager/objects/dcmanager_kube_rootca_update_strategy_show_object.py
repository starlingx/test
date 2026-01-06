class DcmanagerKubeRootcaUpdateStrategyShowObject:
    """
    This class represents a dcmanager kube-rootca-update-strategy as an object.
    """

    def __init__(self) -> None:
        """Initializes a DcmanagerKubeRootcaUpdateStrategyShowObject with default values."""
        self.strategy_type: str = None
        self.subcloud_apply_type: str = None
        self.max_parallel_subclouds: str = None
        self.stop_on_failure: str = None
        self.state: str = None
        self.created_at: str = None
        self.updated_at: str = None

    def set_strategy_type(self, strategy_type: str):
        """
        Sets the strategy type of the kube-rootca-update-strategy.

        Args:
            strategy_type (str): The strategy type to set.
        """
        self.strategy_type = strategy_type

    def get_strategy_type(self) -> str:
        """
        Gets the strategy type of the kube-rootca-update-strategy.

        Returns:
            str: The strategy type.
        """
        return self.strategy_type

    def set_subcloud_apply_type(self, subcloud_apply_type: str):
        """
        Sets the subcloud apply type of the kube-rootca-update-strategy.

        Args:
            subcloud_apply_type (str): The subcloud apply type to set.
        """
        self.subcloud_apply_type = subcloud_apply_type

    def get_subcloud_apply_type(self) -> str:
        """
        Gets the subcloud apply type of the kube-rootca-update-strategy.

        Returns:
            str: The subcloud apply type.
        """
        return self.subcloud_apply_type

    def set_max_parallel_subclouds(self, max_parallel_subclouds: str):
        """
        Sets the max parallel subclouds of the kube-rootca-update-strategy.

        Args:
            max_parallel_subclouds (str): The max parallel subclouds to set.
        """
        self.max_parallel_subclouds = max_parallel_subclouds

    def get_max_parallel_subclouds(self) -> str:
        """
        Gets the max parallel subclouds of the kube-rootca-update-strategy.

        Returns:
            str: The max parallel subclouds.
        """
        return self.max_parallel_subclouds

    def set_stop_on_failure(self, stop_on_failure: str):
        """
        Sets the stop on failure of the kube-rootca-update-strategy.

        Args:
            stop_on_failure (str): The stop on failure to set.
        """
        self.stop_on_failure = stop_on_failure

    def get_stop_on_failure(self) -> str:
        """
        Gets the stop on failure of the kube-rootca-update-strategy.

        Returns:
            str: The stop on failure.
        """
        return self.stop_on_failure

    def set_state(self, state: str):
        """
        Sets the state of the kube-rootca-update-strategy.

        Args:
            state (str): The state to set.
        """
        self.state = state

    def get_state(self) -> str:
        """
        Gets the state of the kube-rootca-update-strategy.

        Returns:
            str: The state.
        """
        return self.state

    def set_created_at(self, created_at: str):
        """
        Sets the creation timestamp of the kube-rootca-update-strategy.

        Args:
            created_at (str): The creation timestamp to set.
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Gets the creation timestamp of the kube-rootca-update-strategy.

        Returns:
            str: The creation timestamp.
        """
        return self.created_at

    def set_updated_at(self, updated_at: str):
        """
        Sets the updated timestamp of the kube-rootca-update-strategy.

        Args:
            updated_at (str): The updated timestamp to set.
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Gets the updated timestamp of the kube-rootca-update-strategy.

        Returns:
            str: The updated timestamp.
        """
        return self.updated_at
