from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.system_host_if_object import SystemHostInterfaceObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.python.type_converter import TypeConverter


class SystemHostInterfaceOutput:
    """
    This class parses the output of 'system host-if-list' commands into a list of SystemHostDiskObject
    """

    def __init__(self, system_host_interface_output):
        """
        Constructor

        Args:
            system_host_interface_output: String output of 'system host-if-list' command

        """
        self.system_host_interfaces: list[SystemHostInterfaceObject] = []
        
        if isinstance(system_host_interface_output, RestResponse):  # came from REST and is already in dict form
            json_object = system_host_interface_output.get_json_content()
            if 'iinterfaces' in json_object:
                interfaces = json_object['iinterfaces']
            else:
                interfaces = [json_object]
        else: # this came from a system command and must be parsed 
            system_table_parser = SystemTableParser(system_host_interface_output)
            interfaces = system_table_parser.get_output_values_list()

        for value in interfaces:

            system_host_interface_object = SystemHostInterfaceObject()

            if 'uuid' in value:
                system_host_interface_object.set_uuid(value['uuid'])

            if 'name' in value:
                system_host_interface_object.set_name(value['name'])
            elif 'ifname' in value:  # value in Rest field
                system_host_interface_object.set_name(value['ifname'])

            if 'class' in value:
                system_host_interface_object.set_if_class(value['class'])
            elif 'ifclass' in value:  # value in Rest field
                system_host_interface_object.set_if_class(value['ifclass'])

            if 'type' in value:
                system_host_interface_object.set_type(value['type'])
            elif 'iftype' in value:  # value in Rest field
                system_host_interface_object.set_type(value['iftype'])

            if 'vlan_id' in value:
                system_host_interface_object.set_vlan_id(value['vlan_id'])

            if 'ports' in value:
                system_host_interface_object.set_ports(TypeConverter.parse_string_to_list(value['ports']))

            if 'uses i/f' in value:
                system_host_interface_object.set_uses_if(TypeConverter.parse_string_to_list(value['uses i/f']))
            elif 'uses' in value:  # value in Rest field
                system_host_interface_object.set_uses_if(value['uses'])

            if 'used by i/f' in value:
                system_host_interface_object.set_used_by_if(TypeConverter.parse_string_to_list(value['used by i/f']))
            elif 'used_by' in value:  # value in Rest field
                system_host_interface_object.set_used_by_if(value['used_by'])

            if 'attributes' in value:
                system_host_interface_object.set_attributes(TypeConverter.parse_string_to_dict(value['attributes']))

            self.system_host_interfaces.append(system_host_interface_object)

    def has_ae_interface(self) -> bool:
        """
        This function will look for at least one Aggregated Ethernet (AE) network interface type and return True if that
        interface is found in the list of interfaces.

        Returns True if there is at least one Aggregated Ethernet (AE) network interface type in the list of interfaces,
        and False otherwise.

        """
        return any(item.get_type() == "ae" for item in self.system_host_interfaces)

    def has_bond_interface(self) -> bool:
        """
        This function will look for at least one Bond network interface and return True if that
        interface is found in the list of interfaces.

        A Bond network interface is an Aggregated Ethernet (AE) whose AE_MODE is 802.3ad.
        Also known as LACP (Link Aggregation Control Protocol), this mode allows link aggregation according to the
        IEEE 802.3ad standard, distributing traffic across multiple physical interfaces based on a balancing algorithm.

        Returns True if there is at least one Bond network interface in the list of interfaces, and False otherwise.

        """
        return any((item.get_type() == "ae" and item.get_attributes().get("AE_MODE") == "803.3ad") for item in self.system_host_interfaces)

    def get_physical_interface_count(self) -> int:
        """
        This function counts the number of physical interfaces on this host by counting the objects in the interface
        list where the 'type' is 'ethernet'.

        Returns: The number of physical interfaces on this host.

        """
        return len([item for item in self.system_host_interfaces if item.type == "ethernet"])

    def has_minimum_number_physical_interface(self, min_num_physical_interface) -> bool:
        """
        This function verifies if this host has at least <min_num_physical_interface> network interfaces.

        Returns: True if this host has at least <min_num_physical_interface> network interfaces, False otherwise.

        """
        return self.get_physical_interface_count() >= min_num_physical_interface

    def get_interfaces_by_class(self, if_class: str) -> [SystemHostInterfaceObject]:
        """
        Gets all interfaces with the given class
        Args:
            if_class (): the if_class

        Returns:

        """
        return list(filter(lambda item: item.get_if_class() == if_class, self.system_host_interfaces))
