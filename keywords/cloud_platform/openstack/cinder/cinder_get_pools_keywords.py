"""Keywords for cinder get-pools CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.cinder.object.cinder_get_pools_output import CinderGetPoolsOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class CinderGetPoolsKeywords(BaseKeyword):
    """Class for Cinder Get Pools Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize CinderGetPoolsKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_cinder_pools(self) -> CinderGetPoolsOutput:
        """Get the parsed output of the 'cinder get-pools --detail' command.

        Returns:
            CinderGetPoolsOutput: Parsed cinder pools output.
        """
        output = self.ssh_connection.send(source_admin_openrc("cinder get-pools --detail"))
        self.validate_success_return_code(self.ssh_connection)
        return CinderGetPoolsOutput(output)
