from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class LnKeywords(BaseKeyword):
    """Keywords for ln command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize ln keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def create_symbolic_link_to_a_file(self, source_path: str, link_path: str) -> None:
        """Create a symbolic link to a file.

        Args:
            source_path (str): Path to the source file.
            link_path (str): Path where the symbolic link will be created.
        """
        self.ssh_connection.send(f"ln -sf {source_path} {link_path}")
        self.validate_success_return_code(self.ssh_connection)
