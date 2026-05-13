"""Output parser for FM CLI commands executed via OIDC authentication."""

from typing import Union

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.fault_management.fm_oidc.object.fm_oidc_command_result_object import FmOidcCommandResultObject

FORBIDDEN_MSG = "Forbidden"
NOT_AUTHORIZED_MSG = "The requested action is not authorized"
INVALID_CREDENTIALS_MSG = "Invalid Identity credentials"
MUST_PROVIDE_USERNAME_MSG = "You must provide a username"
UNABLE_OIDC_TOKEN_MSG = "Unable to get OIDC token"
AUTH_ERROR_MSGS = [INVALID_CREDENTIALS_MSG, MUST_PROVIDE_USERNAME_MSG, UNABLE_OIDC_TOKEN_MSG]


class FmOidcCommandResultOutput:
    """Parses raw FM CLI output into an FmOidcCommandResultObject.

    Detects three states:
    - forbidden: FM server returned 403 Forbidden (role denied)
    - auth_error: OIDC auth failed (invalid token, missing credentials)
    - succeeded: command completed without any errors
    """

    def __init__(self, command: str, raw_output: Union[str, list[str]]) -> None:
        """Constructor.

        Args:
            command (str): The FM CLI command that was executed.
            raw_output (Union[str, list[str]]): Raw output from the SSH command.
        """
        if isinstance(raw_output, list):
            raw_output = "\n".join(raw_output)
        self._result = FmOidcCommandResultObject()
        self._result.set_command(command)
        self._result.set_raw_output(raw_output)
        is_forbidden = FORBIDDEN_MSG in raw_output or NOT_AUTHORIZED_MSG in raw_output
        has_auth_error = any(msg in raw_output for msg in AUTH_ERROR_MSGS)
        self._result.set_forbidden(is_forbidden)
        self._result.set_succeeded(not is_forbidden and not has_auth_error)

        if has_auth_error:
            get_logger().log_error(f"OIDC auth error in '{command}': {raw_output[:200]}")

    def get_result(self) -> FmOidcCommandResultObject:
        """Get the parsed command result.

        Returns:
            FmOidcCommandResultObject: The parsed result object.
        """
        return self._result

    def is_forbidden(self) -> bool:
        """Check if the command was denied with 403 Forbidden.

        Returns:
            bool: True if the output contained a Forbidden/unauthorized error.
        """
        return self._result.get_forbidden()

    def is_successful(self) -> bool:
        """Check if the command succeeded (no Forbidden, no auth errors).

        Returns:
            bool: True if the command completed without any errors.
        """
        return self._result.get_succeeded()

    def get_raw_output(self) -> str:
        """Get the raw CLI output.

        Returns:
            str: The raw output string.
        """
        return self._result.get_raw_output()
