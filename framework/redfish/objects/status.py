class Status:
    """Represents system status information."""

    def __init__(self, health: str, health_rollup: str, state: str):
        """Initialize Status object.

        Args:
            health (str): Health status value.
            health_rollup (str): Health rollup status value.
            state (str): State value.
        """
        self.health = health
        self.health_rollup = health_rollup
        self.state = state

    def get_health(self) -> str:
        """Get health status.

        Returns:
            str: Health status value.
        """
        return self.health

    def set_health(self, health: str) -> None:
        """Set health status.

        Args:
            health (str): Health status value.
        """
        self.health = health

    def get_health_rollup(self) -> str:
        """Get health rollup status.

        Returns:
            str: Health rollup status value.
        """
        return self.health_rollup

    def set_health_rollup(self, health_rollup: str) -> None:
        """Set health rollup status.

        Args:
            health_rollup (str): Health rollup status value.
        """
        self.health_rollup = health_rollup

    def get_state(self) -> str:
        """Get state.

        Returns:
            str: State value.
        """
        return self.state

    def set_state(self, state: str) -> None:
        """Set state.

        Args:
            state (str): State value.
        """
        self.state = state
