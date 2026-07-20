"""Software deploy select keywords."""

from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SoftwareDeploySelectKeywords(BaseKeyword):
    """Keywords for the 'software deploy select' command.

    Attributes:
        ssh_connection (SSHConnection): An instance of an SSH connection.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def deploy_select(self, release: str) -> None:
        """Select a release for deployment via 'software deploy select <release>'.

        This selects all metapackages associated with the given release,
        transitioning them from 'available' to 'deploy-selected'.

        Args:
            release (str): The release ID to select (e.g., 'starlingx-12.00.0').

        Raises:
            KeywordException: If release is empty.
            AssertionError: If the SSH command returns a non-zero exit code.
        """
        if not release:
            raise KeywordException("Missing release ID for software deploy select")
        get_logger().log_info(f"Selecting release for deployment: {release}")
        output = self.ssh_connection.send(source_openrc(f"software deploy select {release}"), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("Deploy select output:\n" + "\n".join(output))

    def deploy_select_metapackages(self, metapackages: List[str]) -> None:
        """Select specific metapackages for deployment via 'software deploy select <pkg1> <pkg2> ...'.

        Args:
            metapackages (List[str]): One or more metapackage release names to select
                (e.g., ['base_12.00.0', 'infra_12.00.0']).

        Raises:
            KeywordException: If the metapackages list is empty.
            AssertionError: If the SSH command returns a non-zero exit code.
        """
        if not metapackages:
            raise KeywordException("Metapackages list must not be empty for software deploy select")
        packages_str = " ".join(metapackages)
        get_logger().log_info(f"Selecting metapackages for deployment: {packages_str}")
        output = self.ssh_connection.send(source_openrc(f"software deploy select {packages_str}"), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("Deploy select output:\n" + "\n".join(output))
