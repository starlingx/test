"""Keywords for openstack resource provider list using openstacksdk."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.resource_provider.object.openstack_resource_provider_list_output import OpenStackResourceProviderListOutput
from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection


class OpenStackResourceProviderListKeywords(BaseKeyword):
    """Class for OpenStack Resource Provider List Keywords (SDK-based)."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize OpenStackResourceProviderListKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def get_resource_provider_list(self) -> OpenStackResourceProviderListOutput:
        """Get the parsed output of resource provider list via the Placement SDK.

        Returns:
            OpenStackResourceProviderListOutput: Parsed resource provider list output.
        """
        placement = self.openstack_connection._get_service_proxy("placement")
        providers = list(placement.resource_providers())
        return OpenStackResourceProviderListOutput(providers)
