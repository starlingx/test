from framework.redfish.objects.status import Status


class TrustedModule:
    """Represents a trusted module."""

    def __init__(self, firmware_version: str, interface_type: str, status: Status):
        """Initialize TrustedModule object.

        Args:
            firmware_version (str): Firmware version.
            interface_type (str): Interface type.
            status (Status): Trusted module status object.
        """
        self.firmware_version = firmware_version
        self.interface_type = interface_type
        self.status = status

    def get_firmware_version(self) -> str:
        """Get firmware version.

        Returns:
            str: Firmware version.
        """
        return self.firmware_version

    def set_firmware_version(self, firmware_version: str) -> None:
        """Set firmware version.

        Args:
            firmware_version (str): Firmware version.
        """
        self.firmware_version = firmware_version

    def get_interface_type(self) -> str:
        """Get interface type.

        Returns:
            str: Interface type.
        """
        return self.interface_type

    def set_interface_type(self, interface_type: str) -> None:
        """Set interface type.

        Args:
            interface_type (str): Interface type.
        """
        self.interface_type = interface_type

    def get_status(self) -> Status:
        """Get trusted module status.

        Returns:
            Status: Trusted module status object.
        """
        return self.status

    def set_status(self, status: Status) -> None:
        """Set trusted module status.

        Args:
            status (Status): Trusted module status object.
        """
        self.status = status
