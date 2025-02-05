from keywords.cloud_platform.system.ptp.objects.system_host_if_ptp_assign_object import SystemHostIfPTPAssignObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.python.type_converter import TypeConverter


class SystemHostIfPTPAssignOutput:
    """
    This class parses the output of 'host-if-ptp-assign' and 'host-if-ptp-remove' command into an object of type SystemHostIfPTPAssignObject.
    """

    def __init__(self, system_host_if_ptp_assign_output):
        """
        Constructor

        Args:
        system_host_if_ptp_assign_output (str): Output of the 'system host-if-ptp-assign' and 'system host-if-ptp-remove' command.
        """
        self.system_host_if_ptp_assign_output: list[SystemHostIfPTPAssignObject] = []
        system_table_parser = SystemTableParser(system_host_if_ptp_assign_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            system_host_if_ptp_assign_object = SystemHostIfPTPAssignObject()
            if 'uuid' in value:
                system_host_if_ptp_assign_object.set_uuid(value['uuid'])
            
            if 'name' in value:
                system_host_if_ptp_assign_object.set_name(value['name'])
            
            if 'ptp_instance_name' in value:
                system_host_if_ptp_assign_object.set_ptp_instance_name(value['ptp_instance_name'])
            
            if 'parameters' in value:
                system_host_if_ptp_assign_object.set_parameters(TypeConverter.parse_string_to_list(value['parameters']))
            self.system_host_if_ptp_assign_output.append(system_host_if_ptp_assign_object)

    def get_host_if_ptp_assign_and_remove(self) -> list[SystemHostIfPTPAssignObject]:
        """Returns the parsed system host-if-ptp-assign and system host-if-ptp-remove object
        
        Returns:
        """
        return self.system_host_if_ptp_assign_output
