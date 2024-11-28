from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.system_host_port_object import SystemHostPortObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostPortOutput:
    """
    This class parses the output of 'system host-port-list' commands into a list of SystemHostPortObject
    """

    def __init__(self, system_host_port_output):
        """
        Constructor

        Args:
            system_host_port_output: String output of 'system host-port-list' command
        """

        self.system_host_ports: list[SystemHostPortObject] = []

        if isinstance(system_host_port_output, RestResponse):  # came from REST and is already in dict form
            json_object = system_host_port_output.get_json_content()
            if 'ports' in json_object:
                ports = json_object['ports']
            else:
                ports = [json_object]
        else:
            system_table_parser = SystemTableParser(system_host_port_output)
            ports = system_table_parser.get_output_values_list()

        for value in ports:

            system_host_port_object = SystemHostPortObject()

            if 'uuid' in value:
                system_host_port_object.set_uuid(value['uuid'])

            if 'name' in value:
                system_host_port_object.set_name(value['name'])

            if 'type' in value:
                system_host_port_object.set_port_type(value['type'])

            if 'pci address' in value:
                system_host_port_object.set_pci_address(value['pci address'])
            elif 'pciaddr' in value:  # rest api value
                system_host_port_object.set_pci_address(value['pciaddr'])

            if 'device' in value:
                system_host_port_object.set_device(int(value['device']))
            elif 'dev_id' in value:  # rest api value
                system_host_port_object.set_device(int(value['dev_id']))

            if 'processor' in value:
                system_host_port_object.set_processor(int(value['processor']))
            elif 'numa_node' in value:  # rest api value
                system_host_port_object.set_processor(int(value['numa_node']))

            if 'accelerated' in value:
                system_host_port_object.set_accelerated(bool(value['accelerated']))
            elif 'dpdksupport' in value:  # rest api value
                system_host_port_object.set_accelerated(bool(value['dpdksupport']))

            if 'device type' in value:
                system_host_port_object.set_device_type(value['device type'])
            elif 'pdevice' in value:  # rest api value
                system_host_port_object.set_device_type(value['pdevice'])

            self.system_host_ports.append(system_host_port_object)

    def has_host_columbiaville(self):
        """
        This function will look for a Columbiaville network adapter in the list of ports.
        If there is at least a port with port_type equals "ethernet" and device_type  starting with
        "Ethernet Controller E810" then is considered that a Columbiaville network adapter was found.

        Returns: True if this host has a Columbiaville network adapter.

        """
        return any(item.get_port_type() == "ethernet" and item.get_device_type().startswith("Ethernet Controller E810") for item in self.system_host_ports)
