from keywords.cloud_platform.system.ptp.objects.system_ptp_parameter_object import SystemPTPParameterObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemPTPParameterListOutput:
    """
    This class parses the output of ptp-parameter-list command into an object of type SystemPTPParameterListObject.
    """

    def __init__(self, system_ptp_parameter_list_output):
        """
        Constructor

        Args:
        system_ptp_parameter_list_output (str): Output of the system ptp-parameter-list command.
        """
        self.system_ptp_parameter_list_output: list[SystemPTPParameterObject] = []
        system_table_parser = SystemTableParser(system_ptp_parameter_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            system_ptp_parameter_object = SystemPTPParameterObject()
            if 'uuid' in value:
                system_ptp_parameter_object.set_uuid(value['uuid'])
            
            if 'name' in value:
                system_ptp_parameter_object.set_name(value['name'])
            
            if 'value' in value:
                system_ptp_parameter_object.set_value(value['value'])
            self.system_ptp_parameter_list_output.append(system_ptp_parameter_object)

    def get_ptp_parameter_list(self) -> list[SystemPTPParameterObject]:
        """
        Returns the parsed system ptp-parameter-list object
        
        Returns:
        """
        return self.system_ptp_parameter_list_output
