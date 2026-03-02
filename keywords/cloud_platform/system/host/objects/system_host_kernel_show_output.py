from keywords.cloud_platform.system.host.objects.system_host_kernel_show_object import SystemHostKernelShowObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemHostKernelShowOutput:
    """
    This class parses the output of 'system host-kernel-show' commands into a SystemHostKernelShowObject

    """

    def __init__(self, system_host_kernel_output: str):
        """
        Constructor

        Args:
            system_host_kernel_output(str): String output of 'system host-kernel-show' command
        """
        system_vertical_table_parser = SystemVerticalTableParser(system_host_kernel_output)
        output_values = system_vertical_table_parser.get_output_values_dict()
        self.system_host_kernel_object = SystemHostKernelShowObject()

        if "hostname" in output_values:
            self.system_host_kernel_object.set_hostname(output_values["hostname"])

        if "kernel_provisioned" in output_values:
            self.system_host_kernel_object.set_kernel_provisioned(output_values["kernel_provisioned"])

        if "kernel_running" in output_values:
            self.system_host_kernel_object.set_kernel_running(output_values["kernel_running"])

    def get_host_kernel_show(self):
        """Getter for hostname"""
        return self.system_host_kernel_object
