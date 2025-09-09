class ComputerSystemReset:
    """Represents computer system reset action."""

    def __init__(self, reset_type_allowable_values: list, target: str):
        """Initialize ComputerSystemReset object.

        Args:
            reset_type_allowable_values (list): List of allowable reset types.
            target (str): Target URL for reset action.
        """
        self.reset_type_allowable_values = reset_type_allowable_values
        self.target = target

    def get_reset_type_allowable_values(self) -> list:
        """Get reset type allowable values.

        Returns:
            list: List of allowable reset types.
        """
        return self.reset_type_allowable_values

    def set_reset_type_allowable_values(self, reset_type_allowable_values: list) -> None:
        """Set reset type allowable values.

        Args:
            reset_type_allowable_values (list): List of allowable reset types.
        """
        self.reset_type_allowable_values = reset_type_allowable_values

    def get_target(self) -> str:
        """Get target URL.

        Returns:
            str: Target URL for reset action.
        """
        return self.target

    def set_target(self, target: str) -> None:
        """Set target URL.

        Args:
            target (str): Target URL for reset action.
        """
        self.target = target
