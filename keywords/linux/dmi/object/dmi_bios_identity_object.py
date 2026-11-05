class DmiBiosIdentityObject:
    """BIOS, system and board identity reported by the kernel under ``/sys/class/dmi/id``."""

    def __init__(self):
        """Constructor."""
        self.bios_vendor: str | None = None
        self.bios_version: str | None = None
        self.bios_date: str | None = None
        self.sys_vendor: str | None = None
        self.product_name: str | None = None
        self.product_version: str | None = None
        self.board_vendor: str | None = None
        self.board_name: str | None = None
        self.board_version: str | None = None

    def get_bios_vendor(self) -> str | None:
        """Get the BIOS vendor.

        Returns:
            str | None: BIOS vendor, or None if not reported.
        """
        return self.bios_vendor

    def set_bios_vendor(self, bios_vendor: str | None) -> None:
        """Set the BIOS vendor.

        Args:
            bios_vendor (str | None): BIOS vendor.
        """
        self.bios_vendor = bios_vendor

    def get_bios_version(self) -> str | None:
        """Get the BIOS version.

        Returns:
            str | None: BIOS version, or None if not reported.
        """
        return self.bios_version

    def set_bios_version(self, bios_version: str | None) -> None:
        """Set the BIOS version.

        Args:
            bios_version (str | None): BIOS version.
        """
        self.bios_version = bios_version

    def get_bios_date(self) -> str | None:
        """Get the BIOS release date.

        Returns:
            str | None: BIOS release date, or None if not reported.
        """
        return self.bios_date

    def set_bios_date(self, bios_date: str | None) -> None:
        """Set the BIOS release date.

        Args:
            bios_date (str | None): BIOS release date.
        """
        self.bios_date = bios_date

    def get_sys_vendor(self) -> str | None:
        """Get the system vendor.

        Returns:
            str | None: System vendor, or None if not reported.
        """
        return self.sys_vendor

    def set_sys_vendor(self, sys_vendor: str | None) -> None:
        """Set the system vendor.

        Args:
            sys_vendor (str | None): System vendor.
        """
        self.sys_vendor = sys_vendor

    def get_product_name(self) -> str | None:
        """Get the product name.

        Returns:
            str | None: Product name, or None if not reported.
        """
        return self.product_name

    def set_product_name(self, product_name: str | None) -> None:
        """Set the product name.

        Args:
            product_name (str | None): Product name.
        """
        self.product_name = product_name

    def get_product_version(self) -> str | None:
        """Get the product version.

        Returns:
            str | None: Product version, or None if not reported.
        """
        return self.product_version

    def set_product_version(self, product_version: str | None) -> None:
        """Set the product version.

        Args:
            product_version (str | None): Product version.
        """
        self.product_version = product_version

    def get_board_vendor(self) -> str | None:
        """Get the board vendor.

        Returns:
            str | None: Board vendor, or None if not reported.
        """
        return self.board_vendor

    def set_board_vendor(self, board_vendor: str | None) -> None:
        """Set the board vendor.

        Args:
            board_vendor (str | None): Board vendor.
        """
        self.board_vendor = board_vendor

    def get_board_name(self) -> str | None:
        """Get the board name.

        Returns:
            str | None: Board name, or None if not reported.
        """
        return self.board_name

    def set_board_name(self, board_name: str | None) -> None:
        """Set the board name.

        Args:
            board_name (str | None): Board name.
        """
        self.board_name = board_name

    def get_board_version(self) -> str | None:
        """Get the board version.

        Returns:
            str | None: Board version, or None if not reported.
        """
        return self.board_version

    def set_board_version(self, board_version: str | None) -> None:
        """Set the board version.

        Args:
            board_version (str | None): Board version.
        """
        self.board_version = board_version

    def to_dictionary(self) -> dict[str, str | None]:
        """Convert the identity to a serializable dictionary.

        Returns:
            dict[str, str | None]: Field name to value.
        """
        return {
            "bios_vendor": self.get_bios_vendor(),
            "bios_version": self.get_bios_version(),
            "bios_date": self.get_bios_date(),
            "sys_vendor": self.get_sys_vendor(),
            "product_name": self.get_product_name(),
            "product_version": self.get_product_version(),
            "board_vendor": self.get_board_vendor(),
            "board_name": self.get_board_name(),
            "board_version": self.get_board_version(),
        }

    def __str__(self) -> str:
        """Describe the BIOS identity.

        Returns:
            str: Vendor, version and date of the BIOS on its product.
        """
        return f"BIOS {self.get_bios_vendor()} {self.get_bios_version()} ({self.get_bios_date()}) on {self.get_sys_vendor()} {self.get_product_name()}"
