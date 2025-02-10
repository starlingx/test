from keywords.cloud_platform.system.ptp.objects.system_ptp_interface_list_object import SystemPTPInterfaceListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.python.type_converter import TypeConverter


class SystemPTPInterfaceListOutput:
    """
    This class parses the output of ptp-interface-list command into an object of type SystemPTPInterfaceListObject.
    """

    def __init__(self, system_ptp_interface_list_output):
        """
        Constructor

        Args:
        system_ptp_interface_list_output (str): Output of the system ptp-interface-list command.
        """
        self.system_ptp_interface_list_output: list[SystemPTPInterfaceListObject] = []
        system_table_parser = SystemTableParser(system_ptp_interface_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            system_ptp_interface_list_object = SystemPTPInterfaceListObject()
            if 'uuid' in value:
                system_ptp_interface_list_object.set_uuid(value['uuid'])
            
            if 'name' in value:
                system_ptp_interface_list_object.set_name(value['name'])
            
            if 'ptp_instance_name' in value:
                system_ptp_interface_list_object.set_ptp_instance_name(value['ptp_instance_name'])
            
            if 'parameters' in value:
                system_ptp_interface_list_object.set_parameters(TypeConverter.parse_string_to_list(value['parameters']))
            self.system_ptp_interface_list_output.append(system_ptp_interface_list_object)

    def get_ptp_interface_list(self) -> SystemPTPInterfaceListObject:
        """
        Returns the parsed system ptp-interface-list
        
        Returns:
        """
        return self.system_ptp_interface_list_output