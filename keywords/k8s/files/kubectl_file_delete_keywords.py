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

    def delete_resources(self, file_path: str, validate: bool = True) -> str:
        """
        Deletes the dashboard resources

        Args:
            file_path (str): the file path
            validate (bool): Enable validation. Defaults to True.

        Returns:
            str: the output

        """
        cmd = f"kubectl delete -f {file_path}"

        if not validate:
            cmd += " --validate=false"

        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output
