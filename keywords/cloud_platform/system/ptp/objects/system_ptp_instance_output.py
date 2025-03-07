from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.ptp.objects.system_ptp_instance_object import SystemPTPInstanceObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser
from keywords.python.type_converter import TypeConverter


class SystemPTPInstanceOutput:
    """
    This class parses the output of ptp-instance command into an object of type SystemPTPInstanceObject.
    """

    def __init__(self, system_ptp_instance_output):
        """
        Constructor

        Args:
        system_ptp_instance_output (str): Output of the system ptp-instance command.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_ptp_instance_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        self.system_ptp_instance_object = SystemPTPInstanceObject()

        if 'uuid' not in output_values:
            raise KeywordException(f"The output line {output_values} was not valid because it is missing an 'uuid'.")
        self.system_ptp_instance_object.set_uuid(output_values['uuid'])
        
        if 'name' in output_values:
            self.system_ptp_instance_object.set_name(output_values['name'])
        
        if 'service' in output_values:
            self.system_ptp_instance_object.set_service(output_values['service'])
        
        if 'hostnames' in output_values:
            self.system_ptp_instance_object.set_hostnames(TypeConverter.parse_string_to_list(output_values['hostnames']))
        
        if 'parameters' in output_values:
            self.system_ptp_instance_object.set_parameters(TypeConverter.parse_string_to_list(output_values['parameters']))

    def get_ptp_instance(self) -> SystemPTPInstanceObject:
        """
        Returns the parsed system ptp-instance
        
        Returns:
        """
        return self.system_ptp_instance_object
    
    def get_ptp_instance_parameters(self) -> str:
        """
        Returns the parameters of the parsed system ptp-instance
        
        Returns:
            str : ptp instance parameters

        Example : 'cmdline_opts=-s xxxx -O -37 -m' boundary_clock_jbod=1 domainNumber=24
        """
        return " ".join(map(lambda parameter: f"'{parameter}'" if " " in parameter else parameter, self.system_ptp_instance_object.get_parameters()))