from typing import Optional


class DcmanagerSubcloudGroupObject:
    """
    This class represents a dcmanager subcloud-group as an object.
    """

    def __init__(self) -> None:
        """Initializes a DcmanagerSubcloudGroupObject with default values."""
        self.id: int = -1
        self.name: Optional[str] = None
        self.description: Optional[str] = None
        self.update_apply_type: Optional[str] = None
        self.max_parallel_subclouds: int = -1
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None

    def set_id(self, group_id: int) -> None:
        """Sets the ID of the subcloud group."""
        self.id = group_id

    def get_id(self) -> int:
        """Gets the ID of the subcloud group."""
        return self.id

    def set_name(self, name: str) -> None:
        """Sets the name of the subcloud group."""
        self.name = name

    def get_name(self) -> Optional[str]:
        """Gets the name of the subcloud group."""
        return self.name

    def set_description(self, description: str) -> None:
        """Sets the description of the subcloud group."""
        self.description = description

    def get_description(self) -> Optional[str]:
        """Gets the description of the subcloud group."""
        return self.description

    def set_update_apply_type(self, update_apply_type: str) -> None:
        """Sets the update apply type of the subcloud group."""
        self.update_apply_type = update_apply_type

    def get_update_apply_type(self) -> Optional[str]:
        """Gets the update apply type of the subcloud group."""
        return self.update_apply_type

    def set_max_parallel_subclouds(self, max_parallel_subclouds: int) -> None:
        """Sets the maximum number of parallel subclouds."""
        self.max_parallel_subclouds = max_parallel_subclouds

    def get_max_parallel_subclouds(self) -> int:
        """Gets the maximum number of parallel subclouds."""
        return self.max_parallel_subclouds

    def set_created_at(self, created_at: str) -> None:
        """Sets the creation timestamp of the subcloud group."""
        self.created_at = created_at

    def get_created_at(self) -> Optional[str]:
        """Gets the creation timestamp of the subcloud group."""
        return self.created_at

    def set_updated_at(self, updated_at: str) -> None:
        """Sets the last updated timestamp of the subcloud group."""
        self.updated_at = updated_at

    def get_updated_at(self) -> Optional[str]:
        """Gets the last updated timestamp of the subcloud group."""
        return self.updated_at
