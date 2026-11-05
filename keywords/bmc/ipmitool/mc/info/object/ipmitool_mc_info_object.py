class IPMIToolMcInfoObject:
    """BMC identity and firmware reported by ``ipmitool mc info``."""

    def __init__(self):
        """Constructor."""
        self.device_id: str | None = None
        self.device_revision: str | None = None
        self.firmware_revision: str | None = None
        self.ipmi_version: str | None = None
        self.manufacturer_id: str | None = None
        self.manufacturer_name: str | None = None
        self.product_id: str | None = None
        self.product_name: str | None = None

    def get_device_id(self) -> str | None:
        """Get the BMC device ID.

        Returns:
            str | None: Device ID, or None if not reported.
        """
        return self.device_id

    def set_device_id(self, device_id: str | None) -> None:
        """Set the BMC device ID.

        Args:
            device_id (str | None): Device ID.
        """
        self.device_id = device_id

    def get_device_revision(self) -> str | None:
        """Get the BMC device revision.

        Returns:
            str | None: Device revision, or None if not reported.
        """
        return self.device_revision

    def set_device_revision(self, device_revision: str | None) -> None:
        """Set the BMC device revision.

        Args:
            device_revision (str | None): Device revision.
        """
        self.device_revision = device_revision

    def get_firmware_revision(self) -> str | None:
        """Get the BMC firmware revision.

        Returns:
            str | None: Firmware revision, or None if not reported.
        """
        return self.firmware_revision

    def set_firmware_revision(self, firmware_revision: str | None) -> None:
        """Set the BMC firmware revision.

        Args:
            firmware_revision (str | None): Firmware revision.
        """
        self.firmware_revision = firmware_revision

    def get_ipmi_version(self) -> str | None:
        """Get the IPMI specification version the BMC implements.

        Returns:
            str | None: IPMI version, or None if not reported.
        """
        return self.ipmi_version

    def set_ipmi_version(self, ipmi_version: str | None) -> None:
        """Set the IPMI specification version the BMC implements.

        Args:
            ipmi_version (str | None): IPMI version.
        """
        self.ipmi_version = ipmi_version

    def get_manufacturer_id(self) -> str | None:
        """Get the BMC manufacturer ID.

        Returns:
            str | None: Manufacturer ID, or None if not reported.
        """
        return self.manufacturer_id

    def set_manufacturer_id(self, manufacturer_id: str | None) -> None:
        """Set the BMC manufacturer ID.

        Args:
            manufacturer_id (str | None): Manufacturer ID.
        """
        self.manufacturer_id = manufacturer_id

    def get_manufacturer_name(self) -> str | None:
        """Get the BMC manufacturer name.

        Returns:
            str | None: Manufacturer name, or None if not reported.
        """
        return self.manufacturer_name

    def set_manufacturer_name(self, manufacturer_name: str | None) -> None:
        """Set the BMC manufacturer name.

        Args:
            manufacturer_name (str | None): Manufacturer name.
        """
        self.manufacturer_name = manufacturer_name

    def get_product_id(self) -> str | None:
        """Get the BMC product ID.

        Returns:
            str | None: Product ID, or None if not reported.
        """
        return self.product_id

    def set_product_id(self, product_id: str | None) -> None:
        """Set the BMC product ID.

        Args:
            product_id (str | None): Product ID.
        """
        self.product_id = product_id

    def get_product_name(self) -> str | None:
        """Get the BMC product name.

        Returns:
            str | None: Product name, or None if not reported.
        """
        return self.product_name

    def set_product_name(self, product_name: str | None) -> None:
        """Set the BMC product name.

        Args:
            product_name (str | None): Product name.
        """
        self.product_name = product_name

    def to_dictionary(self) -> dict[str, str | None]:
        """Convert the BMC information to a serializable dictionary.

        Returns:
            dict[str, str | None]: Field name to value.
        """
        return {
            "device_id": self.get_device_id(),
            "device_revision": self.get_device_revision(),
            "firmware_revision": self.get_firmware_revision(),
            "ipmi_version": self.get_ipmi_version(),
            "manufacturer_id": self.get_manufacturer_id(),
            "manufacturer_name": self.get_manufacturer_name(),
            "product_id": self.get_product_id(),
            "product_name": self.get_product_name(),
        }

    def __str__(self) -> str:
        """Describe the BMC.

        Returns:
            str: Manufacturer and firmware revision.
        """
        return f"BMC {self.get_manufacturer_name()} firmware {self.get_firmware_revision()} (IPMI {self.get_ipmi_version()})"
