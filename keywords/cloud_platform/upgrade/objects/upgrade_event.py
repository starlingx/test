from datetime import datetime


class UpgradeEvent:
    """
    Class for upgrade event object
    """

    def __init__(self, event_name: str, retry: int, operation: str, entry: str, is_upgrade: bool, is_patch: bool):
        """
        Constructor for UpgradeEvent

        Args:
            event_name (str): Name of the upgrade event
            retry (int): Retry count for the operation
            operation (str): Type of operation being performed
            entry (str): Entity being upgraded
            is_upgrade (bool): Whether this is an upgrade operation
            is_patch (bool): Whether this is a patch operation
        """
        self.event_name = event_name
        self.retry = retry
        self.operation: str = operation
        self.entity = entry
        self.is_upgrade = is_upgrade
        self.is_patch = is_patch

        self.upgrade_event_id: int = -1
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.is_rollback: bool = False
        self.duration: int = 0
        self.from_version: str = ""
        self.to_version: str = ""
        self.snapshot: bool = False
        self.subcloud: str = ""
        self.build_id: str = ""

    def get_event_name(self) -> str:
        """
        Getter for event name

        Returns:
            str: The event name
        """
        return self.event_name

    def get_retry(self) -> int:
        """
        Getter for retry count

        Returns:
            int: The retry count
        """
        return self.retry

    def get_operation(self) -> str:
        """
        Getter for operation type

        Returns:
            str: The operation type
        """
        return self.operation

    def get_entity(self) -> str:
        """
        Getter for entity

        Returns:
            str: The entity being upgraded
        """
        return self.entity

    def get_upgrade_event_id(self) -> int:
        """
        Getter for upgrade event ID

        Returns:
            int: The upgrade event ID
        """
        return self.upgrade_event_id

    def set_upgrade_event_id(self, upgrade_event_id: int):
        """
        Setter for upgrade event ID

        Args:
            upgrade_event_id (int): The upgrade event ID
        """
        self.upgrade_event_id = upgrade_event_id

    def get_duration(self) -> int:
        """
        Getter for duration

        Returns:
            int: The duration in seconds
        """
        return self.duration

    def set_duration(self, duration: int):
        """
        Setter for duration

        Args:
            duration (int): The duration in seconds
        """
        self.duration = duration

    def get_from_version(self) -> str:
        """
        Getter for from version

        Returns:
            str: The source version
        """
        return self.from_version

    def set_from_version(self, from_version: str):
        """
        Setter for from version

        Args:
            from_version (str): The source version
        """
        self.from_version = from_version

    def get_to_version(self) -> str:
        """
        Getter for to version

        Returns:
            str: The target version
        """
        return self.to_version

    def set_to_version(self, to_version: str):
        """
        Setter for to version

        Args:
            to_version (str): The target version
        """
        self.to_version = to_version
