"""Keywords for openstack resource provider inventory list CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.resource_provider.object.openstack_resource_provider_inventory_list_output import OpenStackResourceProviderInventoryListOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackResourceProviderInventoryListKeywords(BaseKeyword):
    """Class for OpenStack Resource Provider Inventory List Keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackResourceProviderInventoryListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_resource_provider_inventory_list(self, provider_uuid: str) -> OpenStackResourceProviderInventoryListOutput:
        """Get the parsed output of the 'openstack resource provider inventory list' command.

        Args:
            provider_uuid (str): UUID of the resource provider.

        Returns:
            OpenStackResourceProviderInventoryListOutput: Parsed resource provider inventory list output.
        """
        output = self.ssh_connection.send(source_admin_openrc(f"openstack resource provider inventory list {provider_uuid}"))
        self.validate_success_return_code(self.ssh_connection)
        return OpenStackResourceProviderInventoryListOutput(output)
