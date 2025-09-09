class Boot:
    """Represents system boot configuration."""

    def __init__(self, boot_source_override_enabled: str, boot_source_override_target: str, boot_order: list):
        """Initialize Boot object.

        Args:
            boot_source_override_enabled (str): Boot source override enabled status.
            boot_source_override_target (str): Boot source override target.
            boot_order (list): Boot order list.
        """
        self.boot_source_override_enabled = boot_source_override_enabled
        self.boot_source_override_target = boot_source_override_target
        self.boot_order = boot_order

    def get_boot_source_override_enabled(self) -> str:
        """Get boot source override enabled status.

        Returns:
            str: Boot source override enabled status.
        """
        return self.boot_source_override_enabled

    def set_boot_source_override_enabled(self, value: str) -> None:
        """Set boot source override enabled status.

        Args:
            value (str): Boot source override enabled status.
        """
        self.boot_source_override_enabled = value

    def get_boot_source_override_target(self) -> str:
        """Get boot source override target.

        Returns:
            str: Boot source override target.
        """
        return self.boot_source_override_target

    def set_boot_source_override_target(self, value: str) -> None:
        """Set boot source override target.

        Args:
            value (str): Boot source override target.
        """
        self.boot_source_override_target = value

    def get_boot_order(self) -> list:
        """Get boot order.

        Returns:
            list: Boot order list.
        """
        return self.boot_order
