"""Kubernetes Systems CRD object."""


class KubectlSystemsObject:
    """Represents a Kubernetes Systems CRD entry from 'kubectl get systems'."""

    def __init__(self, name: str):
        """Constructor.

        Args:
            name (str): Name of the system.
        """
        self.name = name
        self.mode = None
        self.type = None
        self.version = None
        self.insync = None
        self.scope = None
        self.reconciled = None

    def get_name(self) -> str:
        """Get system name.

        Returns:
            str: System name.
        """
        return self.name

    def set_mode(self, mode: str) -> None:
        """Set system mode.

        Args:
            mode (str): System mode (e.g., "simplex", "duplex").
        """
        self.mode = mode

    def get_mode(self) -> str:
        """Get system mode.

        Returns:
            str: System mode.
        """
        return self.mode

    def set_type(self, system_type: str) -> None:
        """Set system type.

        Args:
            system_type (str): System type (e.g., "all-in-one", "standard").
        """
        self.type = system_type

    def get_type(self) -> str:
        """Get system type.

        Returns:
            str: System type.
        """
        return self.type

    def set_version(self, version: str) -> None:
        """Set system version.

        Args:
            version (str): System version.
        """
        self.version = version

    def get_version(self) -> str:
        """Get system version.

        Returns:
            str: System version.
        """
        return self.version

    def set_insync(self, insync: str) -> None:
        """Set insync status.

        Args:
            insync (str): Insync status ("true" or "false").
        """
        self.insync = insync

    def get_insync(self) -> str:
        """Get insync status.

        Returns:
            str: Insync status.
        """
        return self.insync

    def set_scope(self, scope: str) -> None:
        """Set system scope.

        Args:
            scope (str): Scope (e.g., "bootstrap").
        """
        self.scope = scope

    def get_scope(self) -> str:
        """Get system scope.

        Returns:
            str: System scope.
        """
        return self.scope

    def set_reconciled(self, reconciled: str) -> None:
        """Set reconciled status.

        Args:
            reconciled (str): Reconciled status ("true" or "false").
        """
        self.reconciled = reconciled

    def get_reconciled(self) -> str:
        """Get reconciled status.

        Returns:
            str: Reconciled status.
        """
        return self.reconciled

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable system info.
        """
        return f"System({self.name}, mode={self.mode}, reconciled={self.reconciled}, insync={self.insync})"
