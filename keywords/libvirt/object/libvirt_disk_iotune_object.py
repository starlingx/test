from typing import Optional


class LibvirtDiskIotuneObject:
    """Represents the I/O throttle values extracted from a VM's libvirt XML.

    Maps to the <iotune> block inside <disk> in the virsh dumpxml output:
        <iotune>
            <read_bytes_sec>10485769</read_bytes_sec>
            <write_bytes_sec>419430400</write_bytes_sec>
            <total_bytes_sec>0</total_bytes_sec>
            <read_iops_sec>200</read_iops_sec>
            <write_iops_sec>5000</write_iops_sec>
            <total_iops_sec>0</total_iops_sec>
        </iotune>
    """

    def __init__(self):
        self.read_bytes_sec: Optional[int] = None
        self.write_bytes_sec: Optional[int] = None
        self.total_bytes_sec: Optional[int] = None
        self.read_iops_sec: Optional[int] = None
        self.write_iops_sec: Optional[int] = None
        self.total_iops_sec: Optional[int] = None

    def set_read_bytes_sec(self, value: int) -> None:
        """Setter for read_bytes_sec.

        Args:
            value (int): Read bytes per second throttle.
        """
        self.read_bytes_sec = value

    def get_read_bytes_sec(self) -> Optional[int]:
        """Getter for read_bytes_sec.

        Returns:
            Optional[int]: Read bytes per second throttle, or None if not set.
        """
        return self.read_bytes_sec

    def set_write_bytes_sec(self, value: int) -> None:
        """Setter for write_bytes_sec.

        Args:
            value (int): Write bytes per second throttle.
        """
        self.write_bytes_sec = value

    def get_write_bytes_sec(self) -> Optional[int]:
        """Getter for write_bytes_sec.

        Returns:
            Optional[int]: Write bytes per second throttle, or None if not set.
        """
        return self.write_bytes_sec

    def set_total_bytes_sec(self, value: int) -> None:
        """Setter for total_bytes_sec.

        Args:
            value (int): Total bytes per second throttle.
        """
        self.total_bytes_sec = value

    def get_total_bytes_sec(self) -> Optional[int]:
        """Getter for total_bytes_sec.

        Returns:
            Optional[int]: Total bytes per second throttle, or None if not set.
        """
        return self.total_bytes_sec

    def set_read_iops_sec(self, value: int) -> None:
        """Setter for read_iops_sec.

        Args:
            value (int): Read IOPS throttle.
        """
        self.read_iops_sec = value

    def get_read_iops_sec(self) -> Optional[int]:
        """Getter for read_iops_sec.

        Returns:
            Optional[int]: Read IOPS throttle, or None if not set.
        """
        return self.read_iops_sec

    def set_write_iops_sec(self, value: int) -> None:
        """Setter for write_iops_sec.

        Args:
            value (int): Write IOPS throttle.
        """
        self.write_iops_sec = value

    def get_write_iops_sec(self) -> Optional[int]:
        """Getter for write_iops_sec.

        Returns:
            Optional[int]: Write IOPS throttle, or None if not set.
        """
        return self.write_iops_sec

    def set_total_iops_sec(self, value: int) -> None:
        """Setter for total_iops_sec.

        Args:
            value (int): Total IOPS throttle.
        """
        self.total_iops_sec = value

    def get_total_iops_sec(self) -> Optional[int]:
        """Getter for total_iops_sec.

        Returns:
            Optional[int]: Total IOPS throttle, or None if not set.
        """
        return self.total_iops_sec

    def __str__(self) -> str:
        """Human-readable representation for logging.

        Returns:
            str: Summary of all iotune values.
        """
        return (
            f"LibvirtDiskIotuneObject("
            f"read_bytes={self.read_bytes_sec}, write_bytes={self.write_bytes_sec}, "
            f"total_bytes={self.total_bytes_sec}, read_iops={self.read_iops_sec}, "
            f"write_iops={self.write_iops_sec}, total_iops={self.total_iops_sec})"
        )
