"""Keywords for openstack flavor list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.flavor.object.openstack_flavor_list_output import OpenStackFlavorListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackFlavorListKeywords(BaseKeyword):
    """Class for OpenStack Flavor List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackFlavorListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_flavor_list(self) -> OpenStackFlavorListOutput:
        """Get the parsed output of the 'openstack flavor list --all' command.

        Returns:
            OpenStackFlavorListOutput: Parsed flavor list output.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack flavor list --all"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackFlavorListOutput(output)
