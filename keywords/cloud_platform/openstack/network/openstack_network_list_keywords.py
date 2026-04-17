"""Keywords for openstack network list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.network.object.openstack_network_list_output import OpenStackNetworkListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackNetworkListKeywords(BaseKeyword):
    """Class for OpenStack Network List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackNetworkListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_network_list(self) -> OpenStackNetworkListOutput:
        """Get the parsed output of the 'openstack network list' command.

        Returns:
            OpenStackNetworkListOutput: Parsed network list output.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack network list"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackNetworkListOutput(output)
