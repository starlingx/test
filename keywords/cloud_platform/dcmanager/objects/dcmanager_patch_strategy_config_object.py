from typing import Optional


class DcmanagerPatchStrategyConfigObject:
    """
    This class represents a dcmanager patch-strategy-config as an object.
    """

    def __init__(self) -> None:
        """Initializes a DcmanagerPatchStrategyConfigObject with default values."""
        self.cloud: Optional[str] = None
        self.storage_apply_type: Optional[str] = None
        self.worker_apply_type: Optional[str] = None
        self.max_parallel_workers: int = -1
        self.alarm_restriction_type: Optional[str] = None
        self.default_instance_action: Optional[str] = None
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None

    def set_cloud(self, cloud: str) -> None:
        """Sets the cloud of the patch-strategy-config."""
        self.cloud = cloud

    def get_cloud(self) -> Optional[str]:
        """Gets the cloud of the patch-strategy-config."""
        return self.cloud

    def set_storage_apply_type(self, storage_apply_type: str) -> None:
        """Sets the storage_apply_type of the patch-strategy-config."""
        self.storage_apply_type = storage_apply_type

    def get_storage_apply_type(self) -> Optional[str]:
        """Gets the storage_apply_type of the patch-strategy-config."""
        return self.storage_apply_type

    def set_worker_apply_type(self, worker_apply_type: str) -> None:
        """Sets the worker_apply_type of the patch-strategy-config."""
        self.worker_apply_type = worker_apply_type

    def get_worker_apply_type(self) -> Optional[str]:
        """Gets the worker_apply_type of the patch-strategy-config."""
        return self.worker_apply_type

    def set_max_parallel_workers(self, max_parallel_workers: int) -> None:
        """Sets the max_parallel_workers of the patch-strategy-config."""
        self.max_parallel_workers = max_parallel_workers

    def get_max_parallel_workers(self) -> int:
        """Gets the max_parallel_workers of the patch-strategy-config."""
        return self.max_parallel_workers

    def set_alarm_restriction_type(self, alarm_restriction_type: str) -> None:
        """Sets the alarm_restriction_type of the patch-strategy-config."""
        self.alarm_restriction_type = alarm_restriction_type

    def get_alarm_restriction_type(self) -> Optional[str]:
        """Gets the alarm_restriction_type of the patch-strategy-config."""
        return self.alarm_restriction_type

    def set_default_instance_action(self, default_instance_action: str) -> None:
        """Sets the default_instance_action of the patch-strategy-config."""
        self.default_instance_action = default_instance_action

    def get_default_instance_action(self) -> Optional[str]:
        """Gets the default_instance_action of the patch-strategy-config."""
        return self.default_instance_action

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
