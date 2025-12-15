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


    def delete_resources(self, file_path: str, ignore_not_found: bool = False, validate: bool = True) -> str:

        """
        Deletes the dashboard resources

        Args:
            file_path (str): the file path
            validate (bool): Enable validation. Defaults to True.
            ignore_not_found (bool): whether to ignore not found errors
        Returns:
            str: the output
        """

        cmd = f"kubectl delete -f {file_path}"

        if not validate:
            cmd += " --validate=false"

        if ignore_not_found:
            cmd += " --ignore-not-found=true"

        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output
