"""Keywords for sysctl operations."""

import re
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SysctlKeywords(BaseKeyword):
    """Keywords for sysctl parameter operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection: SSH connection instance
        """
        self.ssh_connection = ssh_connection

    def get_sysctl_value(self, parameter: str) -> str:
        """Get sysctl parameter value.

        Args:
            parameter: Sysctl parameter name

        Returns:
            str: Parsed parameter value
        """
        command = f"/usr/sbin/sysctl {parameter}"
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return self.parse_sysctl_output(output)

    def parse_sysctl_output(self, sysctl_output):
        """Parse sysctl output to extract clean value.
        
        Transforms: "vm.swappiness = 90\n']") -> "90" or "param = LAB\n']") -> "LAB"
        
        Args:
            sysctl_output: Raw sysctl output with formatting
            
        Returns:
            str: Clean value
        """
        # Split on '=' and get value part, then remove common formatting characters
        value_part = str(sysctl_output).split('=')[-1].strip()
        
        # Remove brackets, quotes, newlines, 'n' character, and other formatting
        clean_value = re.sub(r"[\n\r'\[\]\\n]", '', value_part).strip()
        
        return clean_value
