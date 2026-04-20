"""Keywords for openstack volume type list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.volume.object.openstack_volume_type_list_output import OpenStackVolumeTypeListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackVolumeTypeListKeywords(BaseKeyword):
    """Class for OpenStack Volume Type List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackVolumeTypeListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_volume_type_list(self) -> OpenStackVolumeTypeListOutput:
        """Get the parsed output of the 'openstack volume type list' command.

        Returns:
            OpenStackVolumeTypeListOutput: Parsed volume type list output.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack volume type list"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackVolumeTypeListOutput(output)
