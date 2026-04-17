"""Output for OpenStack capacity analysis results."""

from typing import List

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.capacity.object.openstack_compute_capacity_object import OpenStackComputeCapacityObject
from keywords.cloud_platform.openstack.capacity.object.openstack_storage_capacity_object import OpenStackStorageCapacityObject
from keywords.cloud_platform.openstack.capacity.capacity_math import calculate_max_vms_for_host
from datetime import datetime


class OpenStackCapacityAnalysisOutput:
    """Aggregates compute and storage capacity analysis results.

    Unlike other Output classes that parse raw CLI output, this Output
    receives pre-built Objects from the capacity analysis keyword.
    Provides collection navigation and aggregate capacity methods.
    """

    def __init__(self):
        """Initialize OpenStackCapacityAnalysisOutput with empty collections."""
        self.compute_capacity_objects: List[OpenStackComputeCapacityObject] = []
        self.storage_capacity_objects: List[OpenStackStorageCapacityObject] = []

    # --- Compute collection management ---

    def add_compute_capacity(self, compute_capacity: OpenStackComputeCapacityObject):
        """Add a compute capacity object to the collection.

        Args:
            compute_capacity (OpenStackComputeCapacityObject): Compute capacity for one hypervisor.
        """
        self.compute_capacity_objects.append(compute_capacity)

    def get_compute_capacities(self) -> List[OpenStackComputeCapacityObject]:
        """Get all compute capacity objects.

        Returns:
            List[OpenStackComputeCapacityObject]: List of compute capacity objects.
        """
        return self.compute_capacity_objects

    def get_compute_capacity_by_hostname(self, hostname: str) -> OpenStackComputeCapacityObject:
        """Get the compute capacity for a specific hypervisor.

        Args:
            hostname (str): Hypervisor hostname (e.g. compute-0).

        Returns:
            OpenStackComputeCapacityObject: Compute capacity for the hypervisor.

        Raises:
            KeywordException: If no hypervisor is found with the given hostname.
        """
        for compute in self.compute_capacity_objects:
            if compute.get_hostname() == hostname:
                return compute
        raise KeywordException(f"No compute capacity found for hostname {hostname}")

    # --- Storage collection management ---

    def add_storage_capacity(self, storage_capacity: OpenStackStorageCapacityObject):
        """Add a storage capacity object to the collection.

        Args:
            storage_capacity (OpenStackStorageCapacityObject): Storage capacity for one pool.
        """
        self.storage_capacity_objects.append(storage_capacity)

    def get_storage_capacities(self) -> List[OpenStackStorageCapacityObject]:
        """Get all storage capacity objects.

        Returns:
            List[OpenStackStorageCapacityObject]: List of storage capacity objects.
        """
        return self.storage_capacity_objects

    def get_storage_capacity_by_backend_name(self, backend_name: str) -> OpenStackStorageCapacityObject:
        """Get the storage capacity for a specific backend.

        Args:
            backend_name (str): Volume backend name (e.g. ceph-rook-store).

        Returns:
            OpenStackStorageCapacityObject: Storage capacity for the pool.

        Raises:
            KeywordException: If no pool is found with the given backend name.
        """
        for storage in self.storage_capacity_objects:
            if storage.get_backend_name() == backend_name:
                return storage
        raise KeywordException(f"No storage capacity found for backend {backend_name}")

    # --- Aggregate compute capacity ---

    def get_aggregate_vcpus_headroom(self) -> int:
        """Get the total vCPU headroom across all hypervisors.

        Returns:
            int: Aggregate vCPU headroom.
        """
        return sum(c.get_vcpus_headroom() for c in self.compute_capacity_objects)

    def get_aggregate_memory_mb_headroom(self) -> int:
        """Get the total memory headroom in MB across all hypervisors.

        Returns:
            int: Aggregate memory headroom in MB.
        """
        return sum(c.get_memory_mb_headroom() for c in self.compute_capacity_objects)

    def get_aggregate_disk_gb_headroom(self) -> int:
        """Get the total disk headroom in GB across all hypervisors.

        Returns:
            int: Aggregate disk headroom in GB.
        """
        return sum(c.get_disk_gb_headroom() for c in self.compute_capacity_objects)

    # --- Convenience methods ---

    def get_most_utilized_compute(self) -> OpenStackComputeCapacityObject:
        """Get the hypervisor with the highest utilization.

        Compares the maximum utilization percentage across vcpus, memory,
        and disk for each hypervisor.

        Returns:
            OpenStackComputeCapacityObject: The most utilized hypervisor.

        Raises:
            KeywordException: If no compute capacity objects exist.
        """
        if not self.compute_capacity_objects:
            raise KeywordException("No compute capacity objects available")
        return max(
            self.compute_capacity_objects,
            key=lambda c: max(
                c.get_vcpus_utilization_pct(),
                c.get_memory_mb_utilization_pct(),
                c.get_disk_gb_utilization_pct(),
            ),
        )

    def get_least_utilized_compute(self) -> OpenStackComputeCapacityObject:
        """Get the hypervisor with the lowest utilization.

        Compares the maximum utilization percentage across vcpus, memory,
        and disk for each hypervisor.

        Returns:
            OpenStackComputeCapacityObject: The least utilized hypervisor.

        Raises:
            KeywordException: If no compute capacity objects exist.
        """
        if not self.compute_capacity_objects:
            raise KeywordException("No compute capacity objects available")
        return min(
            self.compute_capacity_objects,
            key=lambda c: max(
                c.get_vcpus_utilization_pct(),
                c.get_memory_mb_utilization_pct(),
                c.get_disk_gb_utilization_pct(),
            ),
        )

    def calculate_max_vms_for_flavor(self, flavor_vcpus: int, flavor_ram_mb: int, flavor_disk_gb: int) -> int:
        """Calculate the maximum number of VMs that can be deployed for a given flavor.

        Iterate over all hypervisors, calculate how many VMs of the given
        flavor fit on each one, and sum the totals.

        Args:
            flavor_vcpus (int): Number of vCPUs required per VM.
            flavor_ram_mb (int): Memory in MB required per VM.
            flavor_disk_gb (int): Disk in GB required per VM.

        Returns:
            int: Maximum number of VMs that can be deployed across the cluster.
        """
        total = 0
        for compute in self.compute_capacity_objects:
            total += calculate_max_vms_for_host(
                compute.get_vcpus_headroom(),
                compute.get_memory_mb_headroom(),
                compute.get_disk_gb_headroom(),
                flavor_vcpus,
                flavor_ram_mb,
                flavor_disk_gb,
            )
        return total

    def get_imbalance_ratio(self) -> float:
        """Get the difference in utilization between the most and least utilized hypervisors.

        Compare the peak utilization (max of vCPU, memory, disk) of the
        most and least utilized hypervisors.

        Returns:
            float: Difference in utilization percentage points.
                0.0 if there is one or fewer hypervisors.

        Example:
            Most utilized at 80%, least at 5% -> returns 75.0
        """
        if len(self.compute_capacity_objects) <= 1:
            return 0.0
        most_utilized = self.get_most_utilized_compute()
        least_utilized = self.get_least_utilized_compute()
        max_util = max(
            most_utilized.get_vcpus_utilization_pct(),
            most_utilized.get_memory_mb_utilization_pct(),
            most_utilized.get_disk_gb_utilization_pct(),
        )
        min_util = max(
            least_utilized.get_vcpus_utilization_pct(),
            least_utilized.get_memory_mb_utilization_pct(),
            least_utilized.get_disk_gb_utilization_pct(),
        )
        return round(max_util - min_util, 2)

    def is_imbalanced(self, threshold: float = 30.0) -> bool:
        """Check if the cluster has significant imbalance between hypervisors.

        Args:
            threshold (float): Maximum acceptable difference in utilization
                percentage points. Default is 30.0.

        Returns:
            bool: True if imbalance ratio exceeds the threshold.
        """
        return self.get_imbalance_ratio() >= threshold

    def calculate_max_vms_per_host(
        self,
        flavor_vcpus: int,
        flavor_ram_mb: int,
        flavor_disk_gb: int,
    ) -> dict:
        """Calculate the maximum VMs per host for a given flavor.

        Args:
            flavor_vcpus (int): Number of vCPUs required per VM.
            flavor_ram_mb (int): Memory in MB required per VM.
            flavor_disk_gb (int): Disk in GB required per VM.

        Returns:
            dict: Mapping of hostname to maximum VM count on that host.
        """
        result = {}
        for compute in self.compute_capacity_objects:
            result[compute.get_hostname()] = calculate_max_vms_for_host(
                compute.get_vcpus_headroom(),
                compute.get_memory_mb_headroom(),
                compute.get_disk_gb_headroom(),
                flavor_vcpus,
                flavor_ram_mb,
                flavor_disk_gb,
            )
        return result

    def calculate_loading_table(
        self,
        flavor_vcpus: int,
        flavor_ram_mb: int,
        flavor_disk_gb: int,
        step: int = 10,
    ) -> dict:
        """Generate a loading table showing VM count at each utilization percentage.

        Args:
            flavor_vcpus (int): Number of vCPUs required per VM.
            flavor_ram_mb (int): Memory in MB required per VM.
            flavor_disk_gb (int): Disk in GB required per VM.
            step (int): Percentage step size. Default 10.

        Returns:
            dict: Mapping of load percentage to VM count.
                Example: {10: 22, 20: 44, ..., 100: 221}
        """
        max_vms = self.calculate_max_vms_for_flavor(flavor_vcpus, flavor_ram_mb, flavor_disk_gb)
        table = {}
        for pct in range(step, 101, step):
            table[pct] = int(max_vms * pct / 100)
        return table

    def get_hypervisor_count(self) -> int:
        """Get the number of hypervisors in the analysis.

        Returns:
            int: Number of hypervisors.
        """
        return len(self.compute_capacity_objects)

    def to_json(self) -> dict:
        """Serialize the capacity analysis results to a dictionary.

        Returns:
            dict: Capacity analysis data including timestamp, compute
                and storage details, and aggregate headroom.
        """
        compute_list = []
        for compute in self.compute_capacity_objects:
            compute_dict = {
                "hostname": compute.get_hostname(),
                "vcpus": {
                    "total": compute.get_vcpus_total(),
                    "used": compute.get_vcpus_used(),
                    "allocation_ratio": compute.get_vcpus_allocation_ratio(),
                    "reserved": compute.get_vcpus_reserved(),
                    "effective": compute.get_vcpus_effective(),
                    "headroom": compute.get_vcpus_headroom(),
                    "utilization_pct": compute.get_vcpus_utilization_pct(),
                },
                "memory_mb": {
                    "total": compute.get_memory_mb_total(),
                    "used": compute.get_memory_mb_used(),
                    "allocation_ratio": compute.get_memory_mb_allocation_ratio(),
                    "reserved": compute.get_memory_mb_reserved(),
                    "effective": compute.get_memory_mb_effective(),
                    "headroom": compute.get_memory_mb_headroom(),
                    "utilization_pct": compute.get_memory_mb_utilization_pct(),
                },
                "disk_gb": {
                    "total": compute.get_disk_gb_total(),
                    "used": compute.get_disk_gb_used(),
                    "allocation_ratio": compute.get_disk_gb_allocation_ratio(),
                    "reserved": compute.get_disk_gb_reserved(),
                    "effective": compute.get_disk_gb_effective(),
                    "headroom": compute.get_disk_gb_headroom(),
                    "utilization_pct": compute.get_disk_gb_utilization_pct(),
                },
                "status": compute.get_status(),
            }
            compute_list.append(compute_dict)

        storage_list = []
        for storage in self.storage_capacity_objects:
            storage_dict = {
                "pool_name": storage.get_pool_name(),
                "backend_name": storage.get_backend_name(),
                "total_capacity_gb": storage.get_total_capacity_gb(),
                "free_capacity_gb": storage.get_free_capacity_gb(),
                "allocated_capacity_gb": storage.get_allocated_capacity_gb(),
                "max_over_subscription_ratio": storage.get_max_over_subscription_ratio(),
                "reserved_percentage": storage.get_reserved_percentage(),
                "effective_capacity_gb": storage.get_effective_capacity_gb(),
                "headroom_gb": storage.get_headroom_gb(),
                "utilization_pct": storage.get_utilization_pct(),
                "status": storage.get_status(),
            }
            storage_list.append(storage_dict)

        return {
            "timestamp": datetime.now().isoformat(),
            "hypervisor_count": self.get_hypervisor_count(),
            "compute": compute_list,
            "storage": storage_list,
            "aggregate": {
                "vcpus_headroom": self.get_aggregate_vcpus_headroom(),
                "memory_mb_headroom": self.get_aggregate_memory_mb_headroom(),
                "disk_gb_headroom": self.get_aggregate_disk_gb_headroom(),
            },
        }

    def __str__(self) -> str:
        """Return human-readable capacity analysis summary.

        Returns:
            str: Multi-line capacity summary.
        """
        lines = [f"Capacity Analysis ({self.get_hypervisor_count()} hypervisors, {len(self.storage_capacity_objects)} storage pools)"]
        lines.append("--- Compute ---")
        for compute in self.compute_capacity_objects:
            lines.append(f"  {compute}")
        lines.append(f"  Aggregate headroom: {self.get_aggregate_vcpus_headroom()} vCPUs, {self.get_aggregate_memory_mb_headroom()} MB RAM, {self.get_aggregate_disk_gb_headroom()} GB disk")
        lines.append("--- Storage ---")
        for storage in self.storage_capacity_objects:
            lines.append(f"  {storage}")
        return "\n".join(lines)
