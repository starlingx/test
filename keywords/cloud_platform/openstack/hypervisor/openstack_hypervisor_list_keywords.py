"""Keywords for openstack hypervisor list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.hypervisor.object.openstack_hypervisor_list_output import OpenStackHypervisorListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackHypervisorListKeywords(BaseKeyword):
    """Class for OpenStack Hypervisor List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackHypervisorListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_hypervisor_list(self) -> OpenStackHypervisorListOutput:
        """Get the parsed output of the 'openstack hypervisor list --long' command.

        Returns:
            OpenStackHypervisorListOutput: Parsed hypervisor list output.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack hypervisor list --long"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackHypervisorListOutput(output)
