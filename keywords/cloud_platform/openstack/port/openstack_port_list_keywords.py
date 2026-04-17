"""Keywords for openstack port list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.port.object.openstack_port_list_output import OpenStackPortListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackPortListKeywords(BaseKeyword):
    """Class for OpenStack Port List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackPortListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_port_list(self) -> OpenStackPortListOutput:
        """Get the parsed output of the 'openstack port list' command.

        Returns:
            OpenStackPortListOutput: Parsed port list output.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack port list"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackPortListOutput(output)
