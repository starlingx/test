"""Keywords for openstack volume list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.volume.object.openstack_volume_list_output import OpenStackVolumeListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackVolumeListKeywords(BaseKeyword):
    """Class for OpenStack Volume List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackVolumeListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_volume_list(self) -> OpenStackVolumeListOutput:
        """Get the parsed output of the 'openstack volume list --all-projects' command.

        Returns:
            OpenStackVolumeListOutput: Parsed volume list output.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack volume list --all-projects"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackVolumeListOutput(output)
