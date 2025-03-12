from typing import Optional


class DcmanagerStrategyStepObject:
    """
    This class represents a dcmanager strategy-step as an object.
    """

    def __init__(self) -> None:
        """Initializes a DcmanagerStrategyStepObject with default values."""
        self.cloud: Optional[str] = None
        self.stage: Optional[int] = None
        self.state: Optional[str] = None
        self.details: Optional[str] = None
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None

    def set_cloud(self, cloud: str) -> None:
        """Sets the cloud of the strategy-step."""
        self.cloud = cloud

    def get_cloud(self) -> Optional[str]:
        """Gets the cloud of the strategy-step."""
        return self.cloud

    def set_stage(self, stage: int) -> None:
        """Sets the stage of the strategy-step."""
        self.stage = stage

    def get_stage(self) -> Optional[int]:
        """Gets the stage of the strategy-step."""
        return self.stage

    def set_state(self, state: str) -> None:
        """Sets the state of the strategy-step."""
        self.state = state

    def get_state(self) -> Optional[str]:
        """Gets the state of the strategy-step."""
        return self.state

    def set_details(self, details: str) -> None:
        """Sets the details of the strategy-step."""
        self.details = details

    def get_details(self) -> Optional[str]:
        """Gets the details of the strategy-step."""
        return self.details

    def set_started_at(self, started_at: str) -> None:
        """Sets the started_at of the strategy-step."""
        self.started_at = started_at

    def get_started_at(self) -> Optional[str]:
        """Gets the started_at of the strategy-step."""
        return self.started_at

    def set_finished_at(self, finished_at: str) -> None:
        """Sets the finished_at of the strategy-step."""
        self.finished_at = finished_at

    def get_finished_at(self) -> Optional[str]:
        """Gets the finished_at of the strategy-step."""
        return self.finished_at

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
