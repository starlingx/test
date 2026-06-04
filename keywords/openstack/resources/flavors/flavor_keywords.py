"""Flavor CRUD keywords via OpenStack SDK."""

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.flavors.object.flavor_list_output import FlavorListOutput


class FlavorKeywords(BaseKeyword):
    """CRUD operations for Nova flavors via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize FlavorKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def list_flavors(self) -> FlavorListOutput:
        """List all flavors.

        Returns:
            FlavorListOutput: Parsed flavor collection.
        """
        raw_flavors = [f.to_dict() for f in self.openstack_connection.get_compute().flavors()]
        return FlavorListOutput(raw_flavors)

    def create_flavor(self, flavor_name: str, ram: int, vcpus: int, disk: int) -> FlavorListOutput:
        """Create a flavor.

        Args:
            flavor_name (str): Flavor name.
            ram (int): RAM in MB.
            vcpus (int): Number of vCPUs.
            disk (int): Disk size in GB.

        Returns:
            FlavorListOutput: Parsed output containing the created flavor.
        """
        get_logger().log_info(f"Creating flavor '{flavor_name}' (ram={ram}, vcpus={vcpus}, disk={disk})")
        flavor = self.openstack_connection.get_compute().create_flavor(name=flavor_name, ram=ram, vcpus=vcpus, disk=disk)
        return FlavorListOutput([flavor.to_dict()])

    def delete_flavor(self, flavor_name_or_id: str) -> None:
        """Delete a flavor.

        Args:
            flavor_name_or_id (str): Flavor name or ID.
        """
        get_logger().log_info(f"Deleting flavor '{flavor_name_or_id}'")
        compute = self.openstack_connection.get_compute()
        flavor = compute.find_flavor(flavor_name_or_id, ignore_missing=False)
        compute.delete_flavor(flavor.id)
