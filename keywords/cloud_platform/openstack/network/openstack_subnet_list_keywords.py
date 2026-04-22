"""Keywords for openstack subnet list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.network.object.openstack_subnet_list_output import OpenStackSubnetListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackSubnetListKeywords(BaseKeyword):
    """Class for OpenStack Subnet List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackSubnetListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_subnet_list(self) -> OpenStackSubnetListOutput:
        """Get the parsed output of the 'openstack subnet list' command.

        Returns:
            OpenStackSubnetListOutput: Parsed subnet list output.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack subnet list"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackSubnetListOutput(output)
