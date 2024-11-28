from keywords.cloud_platform.system.datanetwork.objects.system_datanetwork_object import SystemDatanetworkObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemDatanetworkListOutput:
    """
    This class parses the output of 'system datanetwork-list' commands into a list of SystemDatanetworkObjects
    """

    def __init__(self, system_datanetwork_list_output: str):
        """
        Constructor

        Args:
            system_datanetwork_list_output: String output of 'system datanetwork-list' command
        """

        self.system_datanetworks: [SystemDatanetworkObject] = []
        system_table_parser = SystemTableParser(system_datanetwork_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:

            system_datanetwork_object = SystemDatanetworkObject()

            if 'name' in value:
                system_datanetwork_object.set_name(value['name'])
            if 'uuid' in value:
                system_datanetwork_object.set_uuid(value['uuid'])
            if 'network_type' in value:
                system_datanetwork_object.set_network_type(value['network_type'])
            if 'mtu' in value:
                system_datanetwork_object.set_mtu(int(value['mtu']))

            self.system_datanetworks.append(system_datanetwork_object)

    def get_system_datanetwork_objects(self) -> [SystemDatanetworkObject]:
        """
        Returns the list of SystemDatanetworkObject objects
        Returns:

        """
        return self.system_datanetworks

    def get_system_datanetwork(self, datanetwork_name: str) -> SystemDatanetworkObject:
        """
        Get system datanetwork
        Args:
            datanetwork_name (): the datanetwork_name

        Returns:

        """
        datanetwork_list = list(filter(lambda datanetwork: datanetwork.get_name() == datanetwork_name, self.system_datanetworks))
        if datanetwork_list:
            # should only be one
            return datanetwork_list[0]
        return None
