from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlFileDeleteKeywords(BaseKeyword):
    """
    Keywords for delete file resources
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection object.
        """
        self.ssh_connection = ssh_connection

    def delete_resources(self, file_path: str) -> str:
        """
        Deletes the dashboard resources

        Args:
            file_path (str): the file path

        Returns:
            str: the output

        """
        output = self.ssh_connection.send(export_k8s_config(f"kubectl delete -f {file_path}"))
        self.validate_success_return_code(self.ssh_connection)

        return output
