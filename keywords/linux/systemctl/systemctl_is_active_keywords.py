from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class SystemCTLIsActiveKeywords(BaseKeyword):
    """
    Class for "systemctl is-active" keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller
        """
        self.ssh_connection = ssh_connection

    def is_active(self, service_name: str) -> str:
        """
        Checks if the service is active using  "systemctl is-active <service_name>"

        Args:
            service_name (str): The name of the service

        Returns:
            str: 'active' or 'inactive'
        """
        output = self.ssh_connection.send(f"systemctl is-active {service_name}")
        self.validate_success_return_code(self.ssh_connection)

        # output is a List of 1 string. "active/n"
        output_string = ""
        if output and len(output) > 0:
            output_string = output[0].strip()
        else:
            raise "Output is expected to be a List with one element."

        return output_string
