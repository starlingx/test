from typing import Optional


class KubeHostUpgradeObject:
    """Represents the output of a 'system kube-host-upgrade' vertical table row.

    Typical output:
    +-----------------------+-------------------------+
    | Property              | Value                   |
    +-----------------------+-------------------------+
    | control_plane_version | v1.29.2                 |
    | hostname              | controller-0            |
    | id                    | 1                       |
    | kubelet_version       | v1.29.2                 |
    | personality           | controller              |
    | status                | upgrading-control-plane |
    | target_version        | v1.30.6                 |
    +-----------------------+-------------------------+
    """

    def __init__(self) -> None:
        """Initializes a KubeHostUpgradeObject with default values."""
        self.control_plane_version: Optional[str] = None
        self.hostname: Optional[str] = None
        self.id: Optional[str] = None
        self.kubelet_version: Optional[str] = None
        self.personality: Optional[str] = None
        self.status: Optional[str] = None
        self.target_version: Optional[str] = None

    def get_control_plane_version(self) -> Optional[str]:
        """Getter for control_plane_version.

        Returns:
            Optional[str]: The control plane kubernetes version.
        """
        return self.control_plane_version

    def set_control_plane_version(self, control_plane_version: str) -> None:
        """Setter for control_plane_version.

        Args:
            control_plane_version (str): The control plane kubernetes version.
        """
        self.control_plane_version = control_plane_version

    def get_hostname(self) -> Optional[str]:
        """Getter for hostname.

        Returns:
            Optional[str]: The hostname.
        """
        return self.hostname

    def set_hostname(self, hostname: str) -> None:
        """Setter for hostname.

        Args:
            hostname (str): The hostname.
        """
        self.hostname = hostname

    def get_id(self) -> Optional[str]:
        """Getter for id.

        Returns:
            Optional[str]: The host id.
        """
        return self.id

    def set_id(self, id: str) -> None:
        """Setter for id.

        Args:
            id (str): The host id.
        """
        self.id = id

    def get_kubelet_version(self) -> Optional[str]:
        """Getter for kubelet_version.

        Returns:
            Optional[str]: The kubelet kubernetes version.
        """
        return self.kubelet_version

    def set_kubelet_version(self, kubelet_version: str) -> None:
        """Setter for kubelet_version.

        Args:
            kubelet_version (str): The kubelet kubernetes version.
        """
        self.kubelet_version = kubelet_version

    def get_personality(self) -> Optional[str]:
        """Getter for personality.

        Returns:
            Optional[str]: The host personality.
        """
        return self.personality

    def set_personality(self, personality: str) -> None:
        """Setter for personality.

        Args:
            personality (str): The host personality.
        """
        self.personality = personality

    def get_status(self) -> Optional[str]:
        """Getter for status.

        Returns:
            Optional[str]: The host upgrade status.
        """
        return self.status

    def set_status(self, status: str) -> None:
        """Setter for status.

        Args:
            status (str): The host upgrade status.
        """
        self.status = status

    def get_target_version(self) -> Optional[str]:
        """Getter for target_version.

        Returns:
            Optional[str]: The target kubernetes version.
        """
        return self.target_version

    def set_target_version(self, target_version: str) -> None:
        """Setter for target_version.

        Args:
            target_version (str): The target kubernetes version.
        """
        self.target_version = target_version

    def __str__(self) -> str:
        """Returns a human-readable string representation.

        Returns:
            str: String representation of the kube host upgrade object.
        """
        return f"KubeHostUpgradeObject(" f"hostname={self.hostname}, " f"id={self.id}, " f"personality={self.personality}, " f"control_plane_version={self.control_plane_version}, " f"kubelet_version={self.kubelet_version}, " f"target_version={self.target_version}, " f"status={self.status})"
