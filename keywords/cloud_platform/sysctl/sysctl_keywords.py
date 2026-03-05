"""Keywords for sysctl operations."""

import re

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class SysctlKeywords(BaseKeyword):
    """Keywords for sysctl parameter operations."""

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def _cleanup_string(self, input: str | list) -> str:
        """Cleanup string output from sysctl.

        Args:
            input (str | list): Input string

        Returns:
            str: Cleaned up string
        """
        if isinstance(input, list):
            raw_input = "\n".join(input).strip()
        else:
            raw_input = input

        raw_input = re.sub(r"\n\s*\n", "\n", raw_input)
        raw_input = re.sub(r"[ \t]+", " ", raw_input)
        raw_input = raw_input.strip()
        cleaned = raw_input.encode("utf-8").decode("unicode-escape")
        return cleaned

    def get_sysctl_value(self, parameter: str) -> str:
        """Get sysctl parameter value.

        Args:
            parameter (str): Sysctl parameter name
        Returns:
            str: Parsed parameter value
        """
        command = f"/usr/sbin/sysctl {parameter}"
        sysctl_output = self.ssh_connection.send_as_sudo(command)
        self.validate_success_return_code(self.ssh_connection)
        if isinstance(sysctl_output, list):
            sysctl_output = sysctl_output[0]
        sysctl_output = self._cleanup_string(sysctl_output)
        _, _, value_part = sysctl_output.rpartition("=")
        return value_part.strip()

    def get_sysctl_value_fails(self, parameter: str) -> None:
        """Get sysctl parameter value and expect it to fail.

        Args:
            parameter (str): Sysctl parameter name
        """
        command = f"/usr/sbin/sysctl {parameter}"
        self.ssh_connection.send_as_sudo(command)
        self.validate_cmd_rejection_return_code(self.ssh_connection)

    def get_all_sysctl_parameters(self) -> dict[str, str]:
        """Get all sysctl parameters.

        Returns:
            dict[str, str]: Dictionary of all sysctl parameters
        """
        command = "/usr/sbin/sysctl -a"
        sysctl_output = self._cleanup_string(self.ssh_connection.send_as_sudo(command))
        self.validate_success_return_code(self.ssh_connection)

        parameters: dict[str, str] = {}
        for line in sysctl_output.splitlines():
            if "=" in line:
                name, value = line.split("=", 1)
                parameters[name.strip()] = value.strip()
        return parameters

    def get_multiple_sysctl_values(self, parameter_list: list[str]) -> dict[str, str]:
        """Get multiple sysctl parameter values.

        Args:
            parameter_list (list[str]): List of sysctl parameter names

        Returns:
            dict[str, str]: Dictionary of sysctl parameter values
        """
        parameter_str = " ".join(parameter_list)
        command = f"/usr/sbin/sysctl {parameter_str}"
        sysctl_output = self._cleanup_string(self.ssh_connection.send_as_sudo(command))
        self.validate_success_return_code(self.ssh_connection)

        parameters: dict[str, str] = {}
        for line in sysctl_output.splitlines():
            if "=" in line:
                name_part, _, value_part = line.rpartition("=")
                if name_part.rsplit(None, 1):
                    name_part = name_part.rsplit(None, 1)[-1]
                parameters[name_part.strip()] = value_part.strip()
        return parameters
