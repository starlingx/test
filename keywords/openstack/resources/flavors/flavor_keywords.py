"""Flavor CRUD keywords via OpenStack SDK."""

from typing import Dict

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

    def is_flavor_present(self, flavor_name_or_id: str) -> bool:
        """Check whether a flavor exists.

        Args:
            flavor_name_or_id (str): Flavor name or ID.

        Returns:
            bool: True if the flavor exists, False otherwise.
        """
        compute = self.openstack_connection.get_compute()
        return compute.find_flavor(flavor_name_or_id, ignore_missing=True) is not None

    def set_extra_specs(self, flavor_name_or_id: str, extra_specs: Dict[str, str]) -> None:
        """Set extra specs on a flavor.

        Args:
            flavor_name_or_id (str): Flavor name or ID.
            extra_specs (Dict[str, str]): Key-value pairs to set as extra specs
                (e.g. {'quota:disk_read_bytes_sec': '10485769'}).
        """
        get_logger().log_info(f"Setting extra specs on flavor '{flavor_name_or_id}': {extra_specs}")
        compute = self.openstack_connection.get_compute()
        flavor = compute.find_flavor(flavor_name_or_id, ignore_missing=False)
        compute.create_flavor_extra_specs(flavor.id, extra_specs)
