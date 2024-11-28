from keywords.cloud_platform.system.datanetwork.objects.system_datanetwork_object import SystemDatanetworkObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser
from framework.exceptions.keyword_exception import KeywordException


class SystemDatanetworkShowOutput:
    """
    This class parses the output of 'system datanetwork-list' commands into a list of SystemDatanetworkObjects
    """

    def __init__(self, system_datanetwork_show_output):
        """
        Constructor

        Args:
            system_datanetwork_show_output: String output of 'system datanetwork-list' command
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_datanetwork_show_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        self.system_datanetwork_object = SystemDatanetworkObject()
        if 'id' in output_values:
            self.system_datanetwork_object.set_id(output_values['id'])
        if 'name' in output_values:
            self.system_datanetwork_object.set_name(output_values['name'])
        if 'uuid' in output_values:
            self.system_datanetwork_object.set_uuid(output_values['uuid'])
        if 'network_type' in output_values:
            self.system_datanetwork_object.set_network_type(output_values['network_type'])
        if 'mtu' in output_values:
            self.system_datanetwork_object.set_mtu(output_values['mtu'])
        if 'description' in output_values:
            self.system_datanetwork_object.set_description(output_values['description'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_datanetwork_object(self) -> [SystemDatanetworkObject]:
        """
        Returns the list of SystemDatanetworkObject object
        Returns:

        """
        return self.system_datanetwork_object
