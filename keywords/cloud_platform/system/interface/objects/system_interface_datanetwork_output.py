from keywords.cloud_platform.system.interface.objects.system_interface_datanetwork_object import SystemInterfaceDatanetworkObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemInterfaceDatanetworkOutput:
    """
    This class parses the output of 'system interface-datanetwork-list' commands into a list of SystemInterfaceDatanetworkObjects
    """

    def __init__(self, system_interface_datanetwork_output: str):
        """
        Constructor

        Args:
            system_interface_datanetwork_output: String output of 'system interface-datanetwork-list' command
        """

        self.system_interface_datanetworks: [SystemInterfaceDatanetworkObject] = []
        system_table_parser = SystemTableParser(system_interface_datanetwork_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:

            system_interface_datanetwork_object = SystemInterfaceDatanetworkObject()

            if 'uuid' in value:
                system_interface_datanetwork_object.set_uuid(value['uuid'])

            if 'hostname' in value:
                system_interface_datanetwork_object.set_hostname(value['hostname'])

            if 'ifname' in value:
                system_interface_datanetwork_object.set_ifname(value['ifname'])

            if 'datanetwork_name' in value:
                system_interface_datanetwork_object.set_datanetwork_name(value['datanetwork_name'])

            self.system_interface_datanetworks.append(system_interface_datanetwork_object)

    def get_system_interface_datanetwork_objects(self) -> [SystemInterfaceDatanetworkObject]:
        """
        Returns the list of SystemInterfaceDatanetworkObject objects
        Returns:

        """
        return self.system_interface_datanetworks

    def get_system_interface_datanetwork_by_interface_name(self, interface_name: str) -> SystemInterfaceDatanetworkObject:
        """
        Get system interface datanetwork by the interface name
        Args:
            interface_name (): the interface name

        Returns:

        """
        interface_datanetwork_list = list(filter(lambda datanetwork: datanetwork.get_ifname() == interface_name, self.system_interface_datanetworks))
        if interface_datanetwork_list:
            # should only be one
            return interface_datanetwork_list[0]
        return None

    def get_system_interface_datanetwork_by_datanetwork_name(self, datanetwork_name: str) -> SystemInterfaceDatanetworkObject:
        """
        Get system datanetwork by the datanetwork name
        Args:
            datanetwork_name (): the datanetwork name

        Returns:

        """
        interface_datanetwork_list = list(filter(lambda datanetwork: datanetwork.get_datanetwork_name() == datanetwork_name, self.system_interface_datanetworks))
        if interface_datanetwork_list:
            # should only be one
            return interface_datanetwork_list[0]
        return None
