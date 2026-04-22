"""Keywords for openstack floating ip list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.floating_ip.object.openstack_floating_ip_list_output import OpenStackFloatingIpListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackFloatingIpListKeywords(BaseKeyword):
    """Class for OpenStack Floating IP List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackFloatingIpListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_floating_ip_list(self) -> OpenStackFloatingIpListOutput:
        """Get the parsed output of the 'openstack floating ip list' command.

        Returns:
            OpenStackFloatingIpListOutput: Parsed floating ip list output.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack floating ip list"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackFloatingIpListOutput(output)
