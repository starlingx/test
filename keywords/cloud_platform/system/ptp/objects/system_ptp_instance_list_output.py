from keywords.cloud_platform.system.ptp.objects.system_ptp_instance_list_object import SystemPTPInstanceListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemPTPInstanceListOutput:
    """
    This class parses the output of ptp-instance-list command into an object of type SystemPTPInstanceListObject.
    """

    def __init__(self, system_ptp_instance_list_output):
        """
        Constructor

        Args:
        system_ptp_instance_list_output (str): Output of the system ptp-instance-list command.
        """
        self.system_ptp_instance_list_output: list[SystemPTPInstanceListObject] = []
        system_table_parser = SystemTableParser(system_ptp_instance_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            system_ptp_instance_list_object = SystemPTPInstanceListObject()
            if 'uuid' in value:
                system_ptp_instance_list_object.set_uuid(value['uuid'])
            
            if 'name' in value:
                system_ptp_instance_list_object.set_name(value['name'])
            
            if 'service' in value:
                system_ptp_instance_list_object.set_service(value['service'])
            self.system_ptp_instance_list_output.append(system_ptp_instance_list_object)

    def get_ptp_instance_list(self) -> list[SystemPTPInstanceListObject]:
        """
        Returns the parsed system ptp-instance-list object
        
        Returns:
        """
        return self.system_ptp_instance_list_output
