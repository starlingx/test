from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class SystemCTLStatusKeywords(BaseKeyword):
    """
    Keywords for systemctl status <service_name> cmds
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_status(self, service_name: str) -> list[str]:
        """
        Gets the status of the given service name
        Args:
            service_name (): the service name

        Returns: the output as a list of strings - this should be consumed by a parser for the given output type

        """
        output = self.ssh_connection.send(f'systemctl status {service_name}')
        self.validate_success_return_code(self.ssh_connection)
        return output

