class PgIsReadyObject:
    """Represents the parsed result of a pg_isready command."""

    def __init__(self) -> None:
        """Initialize PgIsReadyObject."""
        self.host: str = ""
        self.port: str = ""
        self.status: str = ""

    def set_host(self, host: str) -> None:
        """Set the host/socket path.

        Args:
            host (str): Host or socket path.
        """
        self.host = host

    def get_host(self) -> str:
        """Get the host/socket path.

        Returns:
            str: Host or socket path.
        """
        return self.host

    def set_port(self, port: str) -> None:
        """Set the port number.

        Args:
            port (str): Port number.
        """
        self.port = port

    def get_port(self) -> str:
        """Get the port number.

        Returns:
            str: Port number.
        """
        return self.port

    def set_status(self, status: str) -> None:
        """Set the connection status.

        Args:
            status (str): Status string, e.g. "accepting connections".
        """
        self.status = status

    def get_status(self) -> str:
        """Get the connection status.

        Returns:
            str: Status string.
        """
        return self.status

    def is_accepting_connections(self) -> bool:
        """Check if status indicates accepting connections.

        Returns:
            bool: True if accepting connections.
        """
        return "accepting connections" in self.status

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: String representation.
        """
        return f"{self.host}:{self.port} - {self.status}"
