"""Data object representing KubeVirt version information from a cluster."""

from typing import Optional


class KubeVirtVersionObject:
    """Holds KubeVirt version fields parsed from the KubeVirt custom resource.

    When KubeVirt is not installed (no CR exists), ``is_installed()`` returns
    False and all version getters return None.
    """

    def __init__(self) -> None:
        """Initialize with default not-installed state."""
        self.installed: bool = False
        self.observed_version: Optional[str] = None
        self.target_version: Optional[str] = None
        self.operator_version: Optional[str] = None

    def __str__(self) -> str:
        """Return string representation of the KubeVirt version state."""
        if not self.installed:
            return "KubeVirtVersionObject(installed=False)"
        return (
            f"KubeVirtVersionObject(installed=True, "
            f"observed={self.observed_version}, "
            f"target={self.target_version}, "
            f"operator={self.operator_version})"
        )

    def is_installed(self) -> bool:
        """Return True if KubeVirt CR exists on the cluster.

        Returns:
            bool: True if installed, False otherwise.
        """
        return self.installed

    def set_installed(self, installed: bool) -> None:
        """Set the installed state.

        Args:
            installed (bool): Whether KubeVirt is installed.
        """
        self.installed = installed

    def get_observed_version(self) -> Optional[str]:
        """Get the observed KubeVirt runtime version.

        Returns:
            str: Version string (e.g. 'v1.7.0') or None if not installed.
        """
        return self.observed_version

    def set_observed_version(self, version: str) -> None:
        """Set the observed KubeVirt runtime version.

        Args:
            version (str): The observed version string.
        """
        self.observed_version = version

    def get_target_version(self) -> Optional[str]:
        """Get the target KubeVirt version.

        Returns:
            str: Target version string or None if not installed.
        """
        return self.target_version

    def set_target_version(self, version: str) -> None:
        """Set the target KubeVirt version.

        Args:
            version (str): The target version string.
        """
        self.target_version = version

    def get_operator_version(self) -> Optional[str]:
        """Get the KubeVirt operator version.

        Returns:
            str: Operator version string or None if not installed.
        """
        return self.operator_version

    def set_operator_version(self, version: str) -> None:
        """Set the KubeVirt operator version.

        Args:
            version (str): The operator version string.
        """
        self.operator_version = version
