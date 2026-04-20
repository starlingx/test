"""Cinder get-pools output parsing."""

from typing import List

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.cinder.object.cinder_get_pools_object import CinderGetPoolsObject
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class CinderGetPoolsOutput:
    """Class for cinder get-pools --detail output."""

    def __init__(self, cinder_get_pools_output):
        """Initialize CinderGetPoolsOutput.

        Args:
            cinder_get_pools_output: Raw CLI output.
        """
        self.cinder_get_pools_objects: List[CinderGetPoolsObject] = []
        openstack_table_parser = OpenStackTableParser(cinder_get_pools_output)
        output_values = openstack_table_parser.get_output_values_list()

        current_object = CinderGetPoolsObject()
        for value in output_values:
            field = value["Property"]
            val = value["Value"]

            if field == "name" and current_object.get_name() is not None:
                self.cinder_get_pools_objects.append(current_object)
                current_object = CinderGetPoolsObject()

            if field == "name":
                current_object.set_name(val)
            elif field == "total_capacity_gb":
                current_object.set_total_capacity_gb(float(val))
            elif field == "free_capacity_gb":
                current_object.set_free_capacity_gb(float(val))
            elif field == "allocated_capacity_gb":
                current_object.set_allocated_capacity_gb(float(val))
            elif field == "max_over_subscription_ratio":
                current_object.set_max_over_subscription_ratio(float(val))
            elif field == "reserved_percentage":
                current_object.set_reserved_percentage(int(val))
            elif field == "backend_state":
                current_object.set_backend_state(val)
            elif field == "storage_protocol":
                current_object.set_storage_protocol(val)
            elif field == "volume_backend_name":
                current_object.set_volume_backend_name(val)
            elif field == "thin_provisioning_support":
                current_object.set_thin_provisioning_support(val == "True")
            elif field == "multiattach":
                current_object.set_multiattach(val == "True")
            elif field == "driver_version":
                current_object.set_driver_version(val)
            elif field == "vendor_name":
                current_object.set_vendor_name(val)
            elif field == "replication_enabled":
                current_object.set_replication_enabled(val == "True")
            elif field == "qos_support":
                current_object.set_qos_support(val == "True")
            elif field == "timestamp":
                current_object.set_timestamp(val)

        if current_object.get_name() is not None:
            self.cinder_get_pools_objects.append(current_object)

    def get_pools(self) -> List[CinderGetPoolsObject]:
        """Get the list of storage pool objects.

        Returns:
            list[CinderGetPoolsObject]: List of storage pool objects.
        """
        return self.cinder_get_pools_objects

    def get_pool_by_name(self, name: str) -> CinderGetPoolsObject:
        """Get the storage pool with the given name.

        Args:
            name (str): Pool name.

        Returns:
            CinderGetPoolsObject: The storage pool object.

        Raises:
            KeywordException: If no pool is found with the given name.
        """
        for pool in self.cinder_get_pools_objects:
            if pool.get_name() == name:
                return pool
        raise KeywordException(f"No storage pool was found with name {name}")

    def get_pool_by_backend_name(self, backend_name: str) -> CinderGetPoolsObject:
        """Get the storage pool with the given volume backend name.

        Args:
            backend_name (str): Volume backend name (e.g. ceph-rook-store).

        Returns:
            CinderGetPoolsObject: The storage pool object.

        Raises:
            KeywordException: If no pool is found with the given backend name.
        """
        for pool in self.cinder_get_pools_objects:
            if pool.get_volume_backend_name() == backend_name:
                return pool
        raise KeywordException(f"No storage pool was found with backend name {backend_name}")

    def is_pool(self, name: str) -> bool:
        """Check if a storage pool with the given name exists.

        Args:
            name (str): Pool name.

        Returns:
            bool: True if the pool exists, False otherwise.
        """
        for pool in self.cinder_get_pools_objects:
            if pool.get_name() == name:
                return True
        return False
