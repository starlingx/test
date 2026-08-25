class CephOsdTreeObject:
    """Represents a single OSD entry from the 'ceph osd tree' output.

    Each object corresponds to one 'osd.<id>' row in the tree, capturing its
    numeric id, runtime status (up/down), and the host it belongs to.
    """

    def __init__(self):
        self.osd_id = -1
        self.name = None
        self.status = None
        self.host = None

    def set_osd_id(self, osd_id: int) -> None:
        """Setter for the OSD numeric id.

        Args:
            osd_id (int): The OSD id (e.g. 0 for 'osd.0').
        """
        self.osd_id = osd_id

    def get_osd_id(self) -> int:
        """Getter for the OSD numeric id.

        Returns:
            int: The OSD id.
        """
        return self.osd_id

    def set_name(self, name: str) -> None:
        """Setter for the OSD name.

        Args:
            name (str): The OSD name (e.g. 'osd.0').
        """
        self.name = name

    def get_name(self) -> str:
        """Getter for the OSD name.

        Returns:
            str: The OSD name.
        """
        return self.name

    def set_status(self, status: str) -> None:
        """Setter for the OSD runtime status.

        Args:
            status (str): The OSD status ('up' or 'down').
        """
        self.status = status

    def get_status(self) -> str:
        """Getter for the OSD runtime status.

        Returns:
            str: The OSD status ('up' or 'down').
        """
        return self.status

    def set_host(self, host: str) -> None:
        """Setter for the host the OSD belongs to.

        Args:
            host (str): The host name (e.g. 'storage-0').
        """
        self.host = host

    def get_host(self) -> str:
        """Getter for the host the OSD belongs to.

        Returns:
            str: The host name.
        """
        return self.host

    def is_up(self) -> bool:
        """Check whether this OSD is up.

        Returns:
            bool: True if the OSD status is 'up', False otherwise.
        """
        return self.status == "up"

    def __str__(self) -> str:
        """Human-readable representation for logging.

        Returns:
            str: A summary of the OSD id, name, status and host.
        """
        return f"CephOsdTreeObject(osd_id={self.osd_id}, name={self.name}, status={self.status}, host={self.host})"
