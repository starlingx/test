class SoftwareDeployPrecheckItemObject:
    """
    Represents a single line/check from the 'software deploy precheck' output.

    Example line:
        'Ceph Storage Healthy: [OK]'
    """

    def __init__(self, name: str, status: str):
        """
        Constructor

        Args:
            name (str): Check name (e.g., 'Ceph Storage Healthy').
            status (str): Status string (e.g., '[OK]', '[FAIL] ...').
        """
        self._name = name
        self._status = status

    def get_name(self) -> str:
        """
        Get the check name.

        Returns:
            str: Check name.
        """
        return self._name

    def get_status(self) -> str:
        """
        Get the raw status.

        Returns:
            str: Status string as returned by the command.
        """
        return self._status

    def is_ok(self) -> bool:
        """
        Check if this item is considered OK based on its status string.

        Returns:
            bool: True if the status contains "[OK]", False otherwise.
        """
        return "[OK]" in self._status

    def __str__(self) -> str:
        """
        Return a readable string representation.

        Returns:
            str: Formatted string with name and status.
        """
        return f"{self._name}: {self._status}"

    def __repr__(self) -> str:
        """
        Return the developer-facing representation.

        Returns:
            str: Class name and field values.
        """
        return f"{self.__class__.__name__}(name={self._name}, status={self._status})"
