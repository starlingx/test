"""Parsed result of a software CLI command run as an OIDC-authenticated user."""

from framework.logging.automation_logger import get_logger


class SoftwareOidcCommandResult:
    """Holds the outcome of a software CLI command run via OIDC authentication.

    Detects three states:
    - forbidden: Server returned 403 / Not allowed (role denied)
    - auth_error: OIDC auth failed (invalid token, missing credentials)
    - succeeded: Command completed without any errors
    """

    FORBIDDEN_PATTERNS = ["Forbidden", "The requested action is not authorized", "Status: 403", "Not allowed"]
    AUTH_ERROR_PATTERNS = [
        "Invalid Identity credentials",
        "You must provide a username",
        "Unable to get OIDC token",
        "Either OIDC token or OIDC user is missing",
        "Failed OIDC validation",
    ]

    def __init__(self, command: str, raw_output: str) -> None:
        """Parse raw output for forbidden/auth error indicators.

        Args:
            command (str): The software command that was executed.
            raw_output (str): Raw output from the SSH command.
        """
        self.command = command
        self.raw_output = raw_output
        self.forbidden = any(pat in raw_output for pat in self.FORBIDDEN_PATTERNS)
        has_auth_error = any(pat in raw_output for pat in self.AUTH_ERROR_PATTERNS)
        self.succeeded = not self.forbidden and not has_auth_error

        if has_auth_error:
            get_logger().log_error(f"OIDC auth error in '{command}': {raw_output[:200]}")

    def is_forbidden(self) -> bool:
        """Check if the command was denied (403/Forbidden).

        Returns:
            bool: True if output contains a forbidden/not-allowed indicator.
        """
        return self.forbidden

    def is_successful(self) -> bool:
        """Check if the command succeeded (no forbidden, no auth error).

        Returns:
            bool: True if no error indicators found.
        """
        return self.succeeded

    def get_raw_output(self) -> str:
        """Get raw CLI output.

        Returns:
            str: The raw output string.
        """
        return self.raw_output

    def get_command(self) -> str:
        """Get the command that was executed.

        Returns:
            str: The software CLI command string.
        """
        return self.command

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: String representation of this result.
        """
        cmd = self.command[:60]
        status = "OK" if self.succeeded else ("FORBIDDEN" if self.forbidden else "FAILED")
        return f"[{status}] {cmd}"
