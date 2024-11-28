from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.host.objects.system_host_cpu_object import SystemHostCPUObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemHostCPUShowOutput:
    """
    This class parses the output of 'system host-cpu-show' commands into a SystemHostCPUObject
    """

    def __init__(self, system_host_cpu_output):
        """
        Constructor

        Args:
            system_host_cpu_output: String output of 'system host-cpu-show' command
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_host_cpu_output)
        output_values = system_vertical_table_parser.get_output_values_dict()
        if 'uuid' not in output_values:
            raise KeywordException(f"The output line {output_values} was not valid because it is missing an 'uuid'.")
        self.system_host_cpu_object = SystemHostCPUObject(output_values['uuid'])

        if 'logical_core' in output_values:
            self.system_host_cpu_object.set_log_core(output_values['logical_core'])

        if 'processor (numa_node)' in output_values:
            self.system_host_cpu_object.set_processor(int(output_values['processor (numa_node)']))

        if 'physical_core' in output_values:
            self.system_host_cpu_object.set_phy_core(int(output_values['physical_core']))

        if 'thread' in output_values:
            self.system_host_cpu_object.set_thread(int(output_values['thread']))

        if 'assigned_function' in output_values:
            self.system_host_cpu_object.set_assigned_function(output_values['assigned_function'])

        if 'processor_model' in output_values:
            self.system_host_cpu_object.set_processor_model(output_values['processor_model'])

        if 'processor_family' in output_values:
            self.system_host_cpu_object.set_processor_family(int(output_values['processor_family']))

        if 'capabilities' in output_values:
            self.system_host_cpu_object.set_capabilities(output_values['capabilities'])

        if 'ihost_uuid' in output_values:
            self.system_host_cpu_object.set_ihost_uuid(output_values['ihost_uuid'])

        if 'inode_uuid' in output_values:
            self.system_host_cpu_object.set_inode_uuid(output_values['inode_uuid'])

        if 'created_at' in output_values:
            self.system_host_cpu_object.set_created_at(output_values['created_at'])

        if 'updated_at' in output_values:
            self.system_host_cpu_object.set_updated_at(output_values['updated_at'])

    def get_host_cpu_show(self):
        return self.system_host_cpu_object