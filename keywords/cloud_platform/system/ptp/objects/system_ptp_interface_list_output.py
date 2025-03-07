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

    def get_ptp_interface_list(self) -> list[SystemPTPInterfaceListObject]:
        """
        Returns the parsed system ptp-interface-list
        
        Returns:
            list[SystemPTPInterfaceListObject] : List representation of system ptp-interface-list objects
        """
        return self.system_ptp_interface_list_output

    def get_ptp_interface_parameters(self, ptp_interface_obj : SystemPTPInterfaceListObject) -> str :
        """
        Returns the ptp interface parameters for the specified name

        Args:
            ptp_interface_obj : PTP interface object
        
        Returns:
            str : ptp interface parameters
        
        Example : 'cmdline_opts=-s xxxx -O -37 -m' boundary_clock_jbod=1 domainNumber=24
        """        
        return " ".join(map(lambda parameter: f"'{parameter}'" if " " in parameter else parameter, ptp_interface_obj.get_parameters()))