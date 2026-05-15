"""Object representing the result of a single FM CLI command executed via OIDC authentication."""


class FmOidcCommandResultObject:
    """Holds the outcome of one FM CLI command run as an OIDC-authenticated user."""

    def __init__(self) -> None:
        """Constructor."""
        self.command = ""
        self.raw_output = ""
        self.succeeded = False
        self.forbidden = False

    def set_command(self, command: str) -> None:
        """Set the FM CLI command that was executed.

        Args:
            command (str): The FM CLI command string.
        """
        self.command = command

    def get_command(self) -> str:
        """Get the FM CLI command that was executed.

        Returns:
            str: The FM CLI command string.
        """
        return self.command

    def set_raw_output(self, raw_output: str) -> None:
        """Set the raw CLI output.

        Args:
            raw_output (str): The raw output from the command.
        """
        self.raw_output = raw_output

    def get_raw_output(self) -> str:
        """Get the raw CLI output.

        Returns:
            str: The raw output from the command.
        """
        return self.raw_output

    def set_succeeded(self, succeeded: bool) -> None:
        """Set whether the command succeeded.

        Args:
            succeeded (bool): True if the command completed without authorization error.
        """
        self.succeeded = succeeded

    def get_succeeded(self) -> bool:
        """Get whether the command succeeded.

        Returns:
            bool: True if the command completed without authorization error.
        """
        return self.succeeded

    def set_forbidden(self, forbidden: bool) -> None:
        """Set whether the command was denied with a Forbidden error.

        Args:
            forbidden (bool): True if the output contained a Forbidden/unauthorized error.
        """
        self.forbidden = forbidden

    def get_forbidden(self) -> bool:
        """Get whether the command was denied with a Forbidden error.

        Returns:
            bool: True if the output contained a Forbidden/unauthorized error.
        """
        return self.forbidden

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: String representation of this result.
        """
        cmd = self.get_command()[:60]
        status = "OK" if self.get_succeeded() else ("FORBIDDEN" if self.get_forbidden() else "FAILED")
        return f"[{status}] {cmd}"
