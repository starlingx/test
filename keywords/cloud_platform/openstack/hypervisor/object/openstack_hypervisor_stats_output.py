"""OpenStack hypervisor stats output parsing."""

from keywords.cloud_platform.openstack.hypervisor.object.openstack_hypervisor_stats_object import OpenStackHypervisorStatsObject
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class OpenStackHypervisorStatsOutput:
    """Class for openstack hypervisor stats output."""

    def __init__(self, openstack_hypervisor_stats_output):
        """Initialize OpenStackHypervisorStatsOutput.

        Args:
            openstack_hypervisor_stats_output: Raw CLI output to parse.
        """
        self.openstack_hypervisor_stats_object = OpenStackHypervisorStatsObject()
        openstack_table_parser = OpenStackTableParser(openstack_hypervisor_stats_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            field = value["Field"]
            val = int(value["Value"])

            if field == "count":
                self.openstack_hypervisor_stats_object.set_count(val)
            elif field == "current_workload":
                self.openstack_hypervisor_stats_object.set_current_workload(val)
            elif field == "disk_available_least":
                self.openstack_hypervisor_stats_object.set_disk_available_least(val)
            elif field == "free_disk_gb":
                self.openstack_hypervisor_stats_object.set_free_disk_gb(val)
            elif field == "free_ram_mb":
                self.openstack_hypervisor_stats_object.set_free_ram_mb(val)
            elif field == "local_gb":
                self.openstack_hypervisor_stats_object.set_local_gb(val)
            elif field == "local_gb_used":
                self.openstack_hypervisor_stats_object.set_local_gb_used(val)
            elif field == "memory_mb":
                self.openstack_hypervisor_stats_object.set_memory_mb(val)
            elif field == "memory_mb_used":
                self.openstack_hypervisor_stats_object.set_memory_mb_used(val)
            elif field == "running_vms":
                self.openstack_hypervisor_stats_object.set_running_vms(val)
            elif field == "vcpus":
                self.openstack_hypervisor_stats_object.set_vcpus(val)
            elif field == "vcpus_used":
                self.openstack_hypervisor_stats_object.set_vcpus_used(val)

    def get_hypervisor_stats_object(self) -> OpenStackHypervisorStatsObject:
        """Get the hypervisor stats object.

        Returns:
            OpenStackHypervisorStatsObject: The parsed hypervisor stats.
        """
        return self.openstack_hypervisor_stats_object
