from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.ptp.objects.system_ptp_parameter_object import SystemPTPParameterObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemPTPParameterOutput:
    """
    This class parses the output of ptp-parameter command into an object of type SystemPTPParameterObject.
    """

    def __init__(self, system_ptp_parameter_output):
        """
        Constructor

        Args:
        system_ptp_parameter_output (str): Output of the system ptp-parameter command.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_ptp_parameter_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        self.system_ptp_parameter_object = SystemPTPParameterObject()

        if 'uuid' not in output_values:
            raise KeywordException(f"The output line {output_values} was not valid because it is missing an 'uuid'.")
        self.system_ptp_parameter_object.set_uuid(output_values['uuid'])
        
        if 'name' in output_values:
            self.system_ptp_parameter_object.set_name(output_values['name'])
        
        if 'value' in output_values:
            self.system_ptp_parameter_object.set_value(output_values['value'])
        
    def get_ptp_parameter(self) -> SystemPTPParameterObject:
        """
        Returns the parsed system ptp-parameter
        
        Returns:
        """
        return self.system_ptp_parameter_object