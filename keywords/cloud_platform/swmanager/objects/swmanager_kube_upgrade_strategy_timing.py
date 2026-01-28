from datetime import datetime
from typing import Optional


class SwManagerKubeUpgradeStrategyTiming:
    """Represents timing information for kube upgrade strategy phases, stages, and steps."""

    def __init__(self) -> None:
        """Initialize SwManagerKubeUpgradeStrategyTiming."""
        self._name: Optional[str] = None
        self._start_date_time: Optional[datetime] = None
        self._end_date_time: Optional[datetime] = None
        self._duration_seconds: Optional[int] = None
        self._is_stage: bool = False
        self._parent_stage: Optional[str] = None
        self._entity_names: Optional[str] = None
        self._from_version: Optional[str] = None
        self._to_version: Optional[str] = None

    def get_name(self) -> Optional[str]:
        """Get the name.

        Returns:
            Optional[str]: The name.
        """
        return self._name

    def set_name(self, name: str) -> None:
        """Set the name.

        Args:
            name (str): The name to set.
        """
        self._name = name

    def get_start_date_time(self) -> Optional[datetime]:
        """Get the start date time.

        Returns:
            Optional[datetime]: The start date time.
        """
        return self._start_date_time

    def set_start_date_time(self, start_date_time: datetime) -> None:
        """Set the start date time.

        Args:
            start_date_time (datetime): The start date time to set.
        """
        self._start_date_time = start_date_time

    def get_end_date_time(self) -> Optional[datetime]:
        """Get the end date time.

        Returns:
            Optional[datetime]: The end date time.
        """
        return self._end_date_time

    def set_end_date_time(self, end_date_time: datetime) -> None:
        """Set the end date time.

        Args:
            end_date_time (datetime): The end date time to set.
        """
        self._end_date_time = end_date_time

    def is_stage(self) -> bool:
        """Check if this timing represents a stage.

        Returns:
            bool: True if stage, False if step.
        """
        return self._is_stage

    def set_is_stage(self, is_stage: bool) -> None:
        """Set whether this timing represents a stage.

        Args:
            is_stage (bool): True if stage, False if step.
        """
        self._is_stage = is_stage

    def get_parent_stage(self) -> Optional[str]:
        """Get the parent stage name for steps.

        Returns:
            Optional[str]: Parent stage name, or None if this is a stage.
        """
        return self._parent_stage

    def set_parent_stage(self, parent_stage: str) -> None:
        """Set the parent stage name for steps.

        Args:
            parent_stage (str): The parent stage name.
        """
        self._parent_stage = parent_stage

    def get_entity_names(self) -> Optional[str]:
        """Get the entity names.

        Returns:
            Optional[str]: Entity names, or None if not set.
        """
        return self._entity_names

    def set_entity_names(self, entity_names: str) -> None:
        """Set the entity names.

        Args:
            entity_names (str): The entity names.
        """
        self._entity_names = entity_names

    def get_from_version(self) -> Optional[str]:
        """Get the from version.

        Returns:
            Optional[str]: From version, or None if not set.
        """
        return self._from_version

    def set_from_version(self, from_version: str) -> None:
        """Set the from version.

        Args:
            from_version (str): The from version.
        """
        self._from_version = from_version

    def get_to_version(self) -> Optional[str]:
        """Get the to version.

        Returns:
            Optional[str]: To version, or None if not set.
        """
        return self._to_version

    def set_to_version(self, to_version: str) -> None:
        """Set the to version.

        Args:
            to_version (str): The to version.
        """
        self._to_version = to_version

    def calculate_duration(self) -> None:
        """Calculate duration from start and end times."""
        self._duration_seconds = int((self._end_date_time - self._start_date_time).total_seconds())

    def get_duration_seconds(self) -> int:
        """Get the duration in seconds.

        Returns:
            int: The duration in seconds.
        """
        return self._duration_seconds
