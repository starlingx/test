from typing import Optional


class DcmanagerPatchStrategyObject:
    """
    This class represents a dcmanager patch-strategy as an object.
    """

    def __init__(self) -> None:
        """Initializes a DcmanagerPatchStrategyObject with default values."""
        self.strategy_type: Optional[str] = None
        self.subcloud_apply_type: Optional[str] = None
        self.max_parallel_subclouds: Optional[int] = None
        self.stop_on_failure: Optional[bool] = None
        self.upload_only: Optional[bool] = None
        self.state: Optional[str] = None
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None

    def set_strategy_type(self, strategy_type: str) -> None:
        """Sets the strategy_type of the patch-strategy."""
        self.strategy_type = strategy_type

    def get_strategy_type(self) -> Optional[str]:
        """Gets the strategy_type of the patch-strategy."""
        return self.strategy_type

    def set_subcloud_apply_type(self, subcloud_apply_type: str) -> None:
        """Sets the subcloud_apply_type of the patch-strategy."""
        self.subcloud_apply_type = subcloud_apply_type

    def get_subcloud_apply_type(self) -> Optional[str]:
        """Gets the subcloud_apply_type of the patch-strategy."""
        return self.subcloud_apply_type

    def set_max_parallel_subclouds(self, max_parallel_subclouds: int) -> None:
        """Sets the max_parallel_subclouds of the patch-strategy."""
        self.max_parallel_subclouds = max_parallel_subclouds

    def get_max_parallel_subclouds(self) -> Optional[int]:
        """Gets the max_parallel_subclouds of the patch-strategy."""
        return self.max_parallel_subclouds

    def set_stop_on_failure(self, stop_on_failure: bool) -> None:
        """Sets the stop_on_failure of the patch-strategy."""
        self.stop_on_failure = stop_on_failure

    def get_stop_on_failure(self) -> bool:
        """Gets the stop_on_failure of the patch-strategy."""
        return self.stop_on_failure

    def set_upload_only(self, upload_only: bool) -> None:
        """Sets the upload_only of the patch-strategy."""
        self.upload_only = upload_only

    def get_upload_only(self) -> Optional[bool]:
        """Gets the upload_only of the patch-strategy."""
        return self.upload_only

    def set_state(self, state: str) -> None:
        """Sets the state of the patch-strategy."""
        self.state = state

    def get_state(self) -> Optional[str]:
        """Gets the state of the patch-strategy."""
        return self.state

    def set_created_at(self, created_at: str) -> None:
        """Sets the creation timestamp of the patch-strategy-config."""
        self.created_at = created_at

    def get_created_at(self) -> Optional[str]:
        """Gets the creation timestamp of the patch-strategy-config."""
        return self.created_at

    def set_updated_at(self, updated_at: str) -> None:
        """Sets the last updated timestamp of the patch-strategy-config."""
        self.updated_at = updated_at

    def get_updated_at(self) -> Optional[str]:
        """Gets the last updated timestamp of the patch-strategy-config."""
        return self.updated_at
