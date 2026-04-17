"""Keywords for openstack resource provider list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.resource_provider.object.openstack_resource_provider_list_output import OpenStackResourceProviderListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackResourceProviderListKeywords(BaseKeyword):
    """Class for OpenStack Resource Provider List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackResourceProviderListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_resource_provider_list(self) -> OpenStackResourceProviderListOutput:
        """Get the parsed output of the 'openstack resource provider list' command.

        Returns:
            OpenStackResourceProviderListOutput: Parsed resource provider list output.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack resource provider list"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackResourceProviderListOutput(output)
