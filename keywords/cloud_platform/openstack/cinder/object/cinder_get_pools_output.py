"""Cinder get-pools output parsing."""

from typing import List

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.cinder.object.cinder_get_pools_object import CinderGetPoolsObject


def _to_bool(value) -> bool:
    """Safely convert a value to bool.

    The Cinder API may return boolean fields as strings ("True"/"False")
    depending on the storage backend driver. Python's bool("False") is True,
    so we need explicit string handling.

    Args:
        value: A bool, string, or other value to convert.

    Returns:
        bool: The boolean interpretation of the value.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


class CinderGetPoolsOutput:
    """Class for cinder get-pools output via OpenStack SDK."""

    def __init__(self, sdk_pools: list):
        """Initialize CinderGetPoolsOutput from openstacksdk backend pool objects.

        Args:
            sdk_pools (list): List of backend pool objects from
                connection.block_storage.backend_pools(details=True).
        """
        self.cinder_get_pools_objects: List[CinderGetPoolsObject] = []

        for pool in sdk_pools:
            pool_object = CinderGetPoolsObject()

            pool_object.set_name(pool.get("name", ""))

            capabilities = pool.get("capabilities", pool)

            pool_object.set_total_capacity_gb(float(capabilities.get("total_capacity_gb", 0)))
            pool_object.set_free_capacity_gb(float(capabilities.get("free_capacity_gb", 0)))
            pool_object.set_allocated_capacity_gb(float(capabilities.get("allocated_capacity_gb", 0)))
            pool_object.set_max_over_subscription_ratio(float(capabilities.get("max_over_subscription_ratio", 1.0)))
            pool_object.set_reserved_percentage(int(capabilities.get("reserved_percentage", 0)))
            pool_object.set_volume_backend_name(capabilities.get("volume_backend_name", ""))
            pool_object.set_storage_protocol(capabilities.get("storage_protocol", ""))
            pool_object.set_backend_state(capabilities.get("backend_state", ""))
            pool_object.set_thin_provisioning_support(_to_bool(capabilities.get("thin_provisioning_support", False)))
            pool_object.set_multiattach(_to_bool(capabilities.get("multiattach", False)))
            pool_object.set_driver_version(capabilities.get("driver_version", ""))
            pool_object.set_vendor_name(capabilities.get("vendor_name", ""))
            pool_object.set_replication_enabled(_to_bool(capabilities.get("replication_enabled", False)))
            pool_object.set_qos_support(_to_bool(capabilities.get("QoS_support", False)))
            pool_object.set_timestamp(capabilities.get("timestamp", ""))

            self.cinder_get_pools_objects.append(pool_object)

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
