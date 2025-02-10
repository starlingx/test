from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.ptp.objects.system_ptp_interface_object import SystemPTPInterfaceObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser
from keywords.python.type_converter import TypeConverter


class SystemPTPInterfaceOutput:
    """
    This class parses the output of ptp-interface command into an object of type SystemPTPInterfaceObject.
    """

    def __init__(self, system_ptp_interface_output):
        """
        Constructor

        Args:
        system_ptp_interface_output (str): Output of the system ptp-interface command.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_ptp_interface_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        self.system_ptp_interface_object = SystemPTPInterfaceObject()

        if 'uuid' not in output_values:
            raise KeywordException(f"The output line {output_values} was not valid because it is missing an 'uuid'.")
        self.system_ptp_interface_object.set_uuid(output_values['uuid'])
        
        if 'name' in output_values:
            self.system_ptp_interface_object.set_name(output_values['name'])
        
        if 'interface_names' in output_values:
            self.system_ptp_interface_object.set_interface_names(TypeConverter.parse_string_to_list(output_values['interface_names']))
        
        if 'ptp_instance_name' in output_values:
            self.system_ptp_interface_object.set_ptp_instance_name(output_values['ptp_instance_name'])
        
        if 'parameters' in output_values:
            self.system_ptp_interface_object.set_parameters(TypeConverter.parse_string_to_list(output_values['parameters']))

    def get_ptp_interface(self) -> SystemPTPInterfaceObject:
        """
        Returns the parsed system ptp-interface
        
        Returns:
        """
        return self.system_ptp_interface_object