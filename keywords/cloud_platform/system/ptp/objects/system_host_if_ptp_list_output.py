from keywords.cloud_platform.system.ptp.objects.system_host_if_ptp_list_object import SystemHostIfPTPListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.python.type_converter import TypeConverter


class SystemHostIfPTPListOutput:
    """
    This class parses the output of 'host-if-ptp-list' command into an object of type SystemHostIfPTPListObject.
    """

    def __init__(self, system_host_if_ptp_list_output):
        """
        Constructor

        Args:
        system_host_if_ptp_list_output (str): Output of the 'system host-if-ptp-list' command.
        """
        self.system_host_if_ptp_list_output: list[SystemHostIfPTPListObject] = []
        system_table_parser = SystemTableParser(system_host_if_ptp_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            system_host_if_ptp_list_object = SystemHostIfPTPListObject()
            if 'uuid' in value:
                system_host_if_ptp_list_object.set_uuid(value['uuid'])
            
            if 'ptp_instance_name' in value:
                system_host_if_ptp_list_object.set_ptp_instance_name(value['ptp_instance_name'])
            
            if 'interface_names' in value:
                system_host_if_ptp_list_object.set_interface_names(TypeConverter.parse_string_to_list(value['interface_names']))
            self.system_host_if_ptp_list_output.append(system_host_if_ptp_list_object)

    def get_host_if_ptp_list(self) -> list[SystemHostIfPTPListObject]:
        """
        Returns the parsed system host-if-ptp-list object
        
        Returns:
        """
        return self.system_host_if_ptp_list_output
