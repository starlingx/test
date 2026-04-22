"""Keywords for OpenStack capacity analysis across compute and storage."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.capacity.capacity_math import calculate_compute_effective
from keywords.cloud_platform.openstack.capacity.capacity_math import calculate_headroom
from keywords.cloud_platform.openstack.capacity.capacity_math import calculate_storage_effective
from keywords.cloud_platform.openstack.capacity.capacity_math import calculate_utilization_pct
from keywords.cloud_platform.openstack.capacity.capacity_math import determine_status
from keywords.cloud_platform.openstack.capacity.object.openstack_capacity_analysis_output import OpenStackCapacityAnalysisOutput
from keywords.cloud_platform.openstack.capacity.object.openstack_compute_capacity_object import OpenStackComputeCapacityObject
from keywords.cloud_platform.openstack.capacity.object.openstack_storage_capacity_object import OpenStackStorageCapacityObject
from keywords.cloud_platform.openstack.cinder.cinder_get_pools_keywords import CinderGetPoolsKeywords
from keywords.cloud_platform.openstack.resource_provider.openstack_resource_provider_inventory_list_keywords import OpenStackResourceProviderInventoryListKeywords
from keywords.cloud_platform.openstack.resource_provider.object.openstack_resource_provider_inventory_list_object import OpenStackResourceProviderInventoryListObject
from keywords.cloud_platform.openstack.resource_provider.openstack_resource_provider_list_keywords import OpenStackResourceProviderListKeywords


class OpenStackCapacityAnalysisKeywords(BaseKeyword):
    """Analyze compute and storage capacity using base collection keywords.

    Orchestrate resource provider and cinder keywords to collect raw data,
    then calculate effective capacity, headroom, utilization, and status
    for each hypervisor and storage pool.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackCapacityAnalysisKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.resource_provider_list_keywords = OpenStackResourceProviderListKeywords(ssh_connection)
        self.resource_provider_inventory_keywords = OpenStackResourceProviderInventoryListKeywords(ssh_connection)
        self.cinder_keywords = CinderGetPoolsKeywords(ssh_connection)

    def analyze_capacity(
        self,
        warning_threshold_pct: float = 70.0,
        critical_threshold_pct: float = 90.0,
    ) -> OpenStackCapacityAnalysisOutput:
        """Analyze compute and storage capacity for the entire cluster.

        Collect data from all resource providers and cinder pools, calculate
        effective capacity, headroom, utilization percentage, and status
        for each hypervisor and storage pool.

        Args:
            warning_threshold_pct (float): Utilization percentage at or above
                which a resource is classified as 'warning'. Default 70.0.
            critical_threshold_pct (float): Utilization percentage at or above
                which a resource is classified as 'critical'. Default 90.0.

        Returns:
            OpenStackCapacityAnalysisOutput: Complete capacity analysis with:
                - Per-hypervisor compute capacity (vCPUs as count, memory in MB,
                  disk in GB) including effective capacity, headroom, utilization
                  percentage, and status.
                - Per-pool storage capacity (all values in GB) including effective
                  capacity, headroom, utilization percentage, and status.
                - Aggregate headroom across all hypervisors.

        Example:
            ::

                analysis_kw = OpenStackCapacityAnalysisKeywords(ssh_connection)
                output = analysis_kw.analyze_capacity()

                # Per-hypervisor data
                for compute in output.get_compute_capacities():
                    print(compute.get_hostname())
                    print(compute.get_vcpus_headroom())       # count
                    print(compute.get_memory_mb_headroom())    # MB
                    print(compute.get_disk_gb_headroom())      # GB
                    print(compute.get_status())                # 'ok', 'warning', or 'critical'

                # Aggregate
                print(output.get_aggregate_vcpus_headroom())   # total free vCPUs

                # Storage
                for pool in output.get_storage_capacities():
                    print(pool.get_headroom_gb())               # GB
        """
        output = OpenStackCapacityAnalysisOutput()

        self._analyze_compute(output, warning_threshold_pct, critical_threshold_pct)
        self._analyze_storage(output, warning_threshold_pct, critical_threshold_pct)

        return output

    def _analyze_compute(
        self,
        output: OpenStackCapacityAnalysisOutput,
        warning_threshold_pct: float,
        critical_threshold_pct: float,
    ):
        """Collect and analyze compute capacity for all resource providers.

        Args:
            output (OpenStackCapacityAnalysisOutput): Output to populate.
            warning_threshold_pct (float): Utilization percentage for warning status.
            critical_threshold_pct (float): Utilization percentage for critical status.
        """
        provider_list_output = self.resource_provider_list_keywords.get_resource_provider_list()
        providers = provider_list_output.get_resource_providers()

        if not providers:
            get_logger().log_warning("No resource providers found, compute capacity analysis will be empty")
            return

        for provider in providers:
            inventory_output = self.resource_provider_inventory_keywords.get_resource_provider_inventory_list(provider.get_uuid())

            compute_obj = OpenStackComputeCapacityObject()
            compute_obj.set_hostname(provider.get_name())

            vcpu_inv = inventory_output.get_resource_provider_by_resource_class("VCPU")
            self._populate_vcpus_fields(compute_obj, vcpu_inv)

            mem_inv = inventory_output.get_resource_provider_by_resource_class("MEMORY_MB")
            self._populate_memory_mb_fields(compute_obj, mem_inv)

            disk_inv = inventory_output.get_resource_provider_by_resource_class("DISK_GB")
            self._populate_disk_gb_fields(compute_obj, disk_inv)

            worst_pct = max(
                compute_obj.get_vcpus_utilization_pct(),
                compute_obj.get_memory_mb_utilization_pct(),
                compute_obj.get_disk_gb_utilization_pct(),
            )
            compute_obj.set_status(determine_status(worst_pct, warning_threshold_pct, critical_threshold_pct))

            output.add_compute_capacity(compute_obj)

    def _analyze_storage(
        self,
        output: OpenStackCapacityAnalysisOutput,
        warning_threshold_pct: float,
        critical_threshold_pct: float,
    ):
        """Collect and analyze storage capacity for all cinder pools.

        Args:
            output (OpenStackCapacityAnalysisOutput): Output to populate.
            warning_threshold_pct (float): Utilization percentage for warning status.
            critical_threshold_pct (float): Utilization percentage for critical status.
        """
        pools_output = self.cinder_keywords.get_cinder_pools()
        pools = pools_output.get_pools()

        if not pools:
            get_logger().log_warning("No cinder pools found, storage capacity analysis will be empty")
            return

        for pool in pools:
            storage_obj = OpenStackStorageCapacityObject()
            storage_obj.set_pool_name(pool.get_name())
            storage_obj.set_backend_name(pool.get_volume_backend_name())

            total = pool.get_total_capacity_gb()
            allocated = pool.get_allocated_capacity_gb()
            ratio = pool.get_max_over_subscription_ratio()
            reserved_pct = pool.get_reserved_percentage()

            storage_obj.set_total_capacity_gb(total)
            storage_obj.set_free_capacity_gb(pool.get_free_capacity_gb())
            storage_obj.set_allocated_capacity_gb(allocated)
            storage_obj.set_max_over_subscription_ratio(ratio)
            storage_obj.set_reserved_percentage(reserved_pct)

            effective = calculate_storage_effective(total, ratio, reserved_pct)
            headroom = round(calculate_headroom(effective, allocated), 2)
            utilization_pct = calculate_utilization_pct(allocated, effective)

            storage_obj.set_effective_capacity_gb(effective)
            storage_obj.set_headroom_gb(headroom)
            storage_obj.set_utilization_pct(utilization_pct)
            storage_obj.set_status(determine_status(utilization_pct, warning_threshold_pct, critical_threshold_pct))

            output.add_storage_capacity(storage_obj)

    def _populate_vcpus_fields(
        self,
        compute_obj: OpenStackComputeCapacityObject,
        inventory: OpenStackResourceProviderInventoryListObject,
    ):
        """Calculate and set vCPU capacity fields on a compute object.

        Args:
            compute_obj (OpenStackComputeCapacityObject): Object to populate.
            inventory (OpenStackResourceProviderInventoryListObject): VCPU inventory data.
        """
        total = inventory.get_total()
        used = inventory.get_used()
        allocation_ratio = inventory.get_allocation_ratio()
        reserved = inventory.get_reserved()

        effective = calculate_compute_effective(total, allocation_ratio, reserved)
        if effective <= 0:
            get_logger().log_warning(f"Effective capacity is {effective} for vcpus (total={total}, ratio={allocation_ratio}, reserved={reserved})")
        headroom = calculate_headroom(effective, used)
        utilization_pct = calculate_utilization_pct(used, effective)

        compute_obj.set_vcpus_total(total)
        compute_obj.set_vcpus_used(used)
        compute_obj.set_vcpus_allocation_ratio(allocation_ratio)
        compute_obj.set_vcpus_reserved(reserved)
        compute_obj.set_vcpus_effective(effective)
        compute_obj.set_vcpus_headroom(headroom)
        compute_obj.set_vcpus_utilization_pct(utilization_pct)

    def _populate_memory_mb_fields(
        self,
        compute_obj: OpenStackComputeCapacityObject,
        inventory: OpenStackResourceProviderInventoryListObject,
    ):
        """Calculate and set memory capacity fields on a compute object.

        Args:
            compute_obj (OpenStackComputeCapacityObject): Object to populate.
            inventory (OpenStackResourceProviderInventoryListObject): MEMORY_MB inventory data.
        """
        total = inventory.get_total()
        used = inventory.get_used()
        allocation_ratio = inventory.get_allocation_ratio()
        reserved = inventory.get_reserved()

        effective = calculate_compute_effective(total, allocation_ratio, reserved)
        if effective <= 0:
            get_logger().log_warning(f"Effective capacity is {effective} for memory_mb (total={total}, ratio={allocation_ratio}, reserved={reserved})")
        headroom = calculate_headroom(effective, used)
        utilization_pct = calculate_utilization_pct(used, effective)

        compute_obj.set_memory_mb_total(total)
        compute_obj.set_memory_mb_used(used)
        compute_obj.set_memory_mb_allocation_ratio(allocation_ratio)
        compute_obj.set_memory_mb_reserved(reserved)
        compute_obj.set_memory_mb_effective(effective)
        compute_obj.set_memory_mb_headroom(headroom)
        compute_obj.set_memory_mb_utilization_pct(utilization_pct)

    def _populate_disk_gb_fields(
        self,
        compute_obj: OpenStackComputeCapacityObject,
        inventory: OpenStackResourceProviderInventoryListObject,
    ):
        """Calculate and set disk capacity fields on a compute object.

        Args:
            compute_obj (OpenStackComputeCapacityObject): Object to populate.
            inventory (OpenStackResourceProviderInventoryListObject): DISK_GB inventory data.
        """
        total = inventory.get_total()
        used = inventory.get_used()
        allocation_ratio = inventory.get_allocation_ratio()
        reserved = inventory.get_reserved()

        effective = calculate_compute_effective(total, allocation_ratio, reserved)
        if effective <= 0:
            get_logger().log_warning(f"Effective capacity is {effective} for disk_gb (total={total}, ratio={allocation_ratio}, reserved={reserved})")
        headroom = calculate_headroom(effective, used)
        utilization_pct = calculate_utilization_pct(used, effective)

        compute_obj.set_disk_gb_total(total)
        compute_obj.set_disk_gb_used(used)
        compute_obj.set_disk_gb_allocation_ratio(allocation_ratio)
        compute_obj.set_disk_gb_reserved(reserved)
        compute_obj.set_disk_gb_effective(effective)
        compute_obj.set_disk_gb_headroom(headroom)
        compute_obj.set_disk_gb_utilization_pct(utilization_pct)
