"""Keywords for cinder get-pools using openstacksdk."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.cinder.object.cinder_get_pools_output import CinderGetPoolsOutput
from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection


class CinderGetPoolsKeywords(BaseKeyword):
    """Class for Cinder Get Pools Keywords (SDK-based)."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize CinderGetPoolsKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def get_cinder_pools(self) -> CinderGetPoolsOutput:
        """Get the parsed output of cinder backend pools via the Block Storage SDK.

        Returns:
            CinderGetPoolsOutput: Parsed cinder pools output.
        """
        block_storage = self.openstack_connection.get_block_storage()
        pools = list(block_storage.backend_pools(details=True))
        return CinderGetPoolsOutput(pools)
