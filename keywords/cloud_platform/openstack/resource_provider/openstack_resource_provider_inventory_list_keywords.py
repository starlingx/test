"""Keywords for openstack resource provider inventory list using openstacksdk."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.resource_provider.object.openstack_resource_provider_inventory_list_output import OpenStackResourceProviderInventoryListOutput
from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection


class OpenStackResourceProviderInventoryListKeywords(BaseKeyword):
    """Class for OpenStack Resource Provider Inventory List Keywords (SDK-based)."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize OpenStackResourceProviderInventoryListKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def get_resource_provider_inventory_list(self, provider_uuid: str) -> OpenStackResourceProviderInventoryListOutput:
        """Get the parsed output of resource provider inventory list via Placement SDK.

        The Placement SDK proxy does not expose a high-level method for
        listing inventories, so we use the authenticated session's GET
        against the Placement REST API directly.

        Args:
            provider_uuid (str): UUID of the resource provider.

        Returns:
            OpenStackResourceProviderInventoryListOutput: Parsed resource provider inventory list output.
        """
        conn = self.openstack_connection._openstack_connection.get_connection()

        inventories = conn.placement.get(
            f"/resource_providers/{provider_uuid}/inventories"
        )
        if inventories.status_code >= 400:
            raise KeywordException(
                f"Failed to get inventories for provider {provider_uuid}: "
                f"HTTP {inventories.status_code}"
            )
        inventories = inventories.json()

        usages_response = conn.placement.get(
            f"/resource_providers/{provider_uuid}/usages"
        )
        if usages_response.status_code >= 400:
            raise KeywordException(
                f"Failed to get usages for provider {provider_uuid}: "
                f"HTTP {usages_response.status_code}"
            )
        usages = usages_response.json().get("usages", {})

        return OpenStackResourceProviderInventoryListOutput(inventories, usages)
