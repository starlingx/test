from typing import Optional


class DcmanagerPrestageStrategyObject:
    """This class represents a dcmanager prestage-strategy as an object."""

    def __init__(self) -> None:
        """Initializes a DcmanagerPrestageStrategyObject with default values."""
        self.strategy_type: Optional[str] = None
        self.subcloud_apply_type: Optional[str] = None
        self.max_parallel_subclouds: Optional[int] = None
        self.stop_on_failure: Optional[bool] = None
        self.prestage_software_version: Optional[str] = None
        self.state: Optional[str] = None
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None

    def set_strategy_type(self, strategy_type: str) -> None:
        """Sets the strategy_type of the prestage-strategy."""
        self.strategy_type = strategy_type

    def get_strategy_type(self) -> Optional[str]:
        """Gets the strategy_type of the prestage-strategy."""
        return self.strategy_type

    def set_subcloud_apply_type(self, subcloud_apply_type: str) -> None:
        """Sets the subcloud_apply_type of the prestage-strategy."""
        self.subcloud_apply_type = subcloud_apply_type

    def get_subcloud_apply_type(self) -> Optional[str]:
        """Gets the subcloud_apply_type of the prestage-strategy."""
        return self.subcloud_apply_type

    def set_max_parallel_subclouds(self, max_parallel_subclouds: int) -> None:
        """Sets the max_parallel_subclouds of the prestage-strategy."""
        self.max_parallel_subclouds = max_parallel_subclouds

    def get_max_parallel_subclouds(self) -> Optional[int]:
        """Gets the max_parallel_subclouds of the prestage-strategy."""
        return self.max_parallel_subclouds

    def set_prestage_software_version(self, prestage_software_version: str) -> None:
        """Sets the prestage_software_version of the prestage-strategy."""
        self.prestage_software_version = prestage_software_version

    def get_prestage_software_version(self) -> Optional[str]:
        """Gets the prestage_software_version of the prestage-strategy."""
        return self.prestage_software_version

    def set_stop_on_failure(self, stop_on_failure: bool) -> None:
        """Sets the stop_on_failure of the prestage-strategy."""
        self.stop_on_failure = stop_on_failure

    def get_stop_on_failure(self) -> Optional[bool]:
        """Gets the stop_on_failure of the prestage-strategy."""
        return self.stop_on_failure

    def set_state(self, state: str) -> None:
        """Sets the state of the prestage-strategy."""
        self.state = state

    def get_state(self) -> Optional[str]:
        """Gets the state of the prestage-strategy."""
        return self.state

    def set_created_at(self, created_at: str) -> None:
        """Sets the creation timestamp of the prestage-strategy."""
        self.created_at = created_at

    def get_created_at(self) -> Optional[str]:
        """Gets the creation timestamp of the prestage-strategy."""
        return self.created_at

    def set_updated_at(self, updated_at: str) -> None:
        """Sets the last updated timestamp of the prestage-strategy."""
        self.updated_at = updated_at

    def get_updated_at(self) -> Optional[str]:
        """Gets the last updated timestamp of the prestage-strategy."""
        return self.updated_at
