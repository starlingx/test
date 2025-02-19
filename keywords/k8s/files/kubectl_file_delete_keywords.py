from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlFileDeleteKeywords(BaseKeyword):
    """
    Keywords for delete file resources
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def delete_resources(self, file_path: str) -> str:
        """
        Deletes the dashboard resources
        Args:
            file_path (): the file path

        Returns: the output

        """
        output = self.ssh_connection.send(export_k8s_config(f"kubectl delete -f {file_path}"))
        self.validate_success_return_code(self.ssh_connection)

        return output
