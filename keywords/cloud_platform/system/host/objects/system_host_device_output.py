from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.system_host_device_object import SystemHostDeviceObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostDeviceOutput:
    """
    This class parses the output of 'system host-device-list' commands into a list of SystemHostDeviceObject
    """

    def __init__(self, system_host_device_output):
        """
        Constructor

        Args:
            system_host_device_output: String output of 'system host-device-list' command
        """

        self.system_host_devices: list[SystemHostDeviceObject] = []
        
        if isinstance(system_host_device_output, RestResponse):  # came from REST and is already in dict form
            json_object = system_host_device_output.get_json_content()
            if 'pci_devices' in json_object:
                devices = json_object['pci_devices']
            else:
                devices = [json_object]
        else: # this came from a system command and must be parsed 
            system_table_parser = SystemTableParser(system_host_device_output)
            devices = system_table_parser.get_output_values_list()

        for value in devices:

            system_host_device_object = SystemHostDeviceObject()

            if 'address' in value:
                system_host_device_object.set_address(value['address'])
            elif 'pciaddr' in value:  # value in Rest field
                system_host_device_object.set_address(value['pciaddr'])

            if 'class id' in value:
                system_host_device_object.set_class_id(value['class id'])
            elif 'pclass_id' in value:  # value in Rest field
                system_host_device_object.set_class_id(value['pclass_id'])

            if 'class name' in value:
                system_host_device_object.set_class_name(value['class name'])
            elif 'pclass' in value:  # value in Rest field
                system_host_device_object.set_class_name(value['pclass'])

            if 'device id' in value:
                system_host_device_object.set_device_id(value['device id'])
            elif 'pdevice_id' in value:  # value in Rest field
                system_host_device_object.set_device_id(value['pdevice_id'])

            if 'device name' in value:
                system_host_device_object.set_device_name(value['device name'])
            elif 'pdevice' in value:  # value in Rest field
                system_host_device_object.set_device_name(value['pdevice'])

            if 'enabled' in value:
                system_host_device_object.set_enabled(bool(value['enabled']))

            if 'name' in value:
                system_host_device_object.set_name(value['name'])

            if 'numa_node' in value:
                system_host_device_object.set_numa_node(int(value['numa_node']))

            if 'vendor id' in value:
                system_host_device_object.set_vendor_id(value['vendor id'])
            elif 'pvendor_id' in value:  # value in Rest field
                system_host_device_object.set_vendor_id(value['pvendor_id'])

            if 'vendor name' in value:
                system_host_device_object.set_vendor_name(value['vendor name'])
            elif 'pvendor' in value:  # value in Rest field
                system_host_device_object.set_vendor_name(value['pvendor'])
            

            self.system_host_devices.append(system_host_device_object)

    def has_host_n3000(self):
        """
        This function will look for a N3000 card in the list of devices
        If there is at least a device with vendor_id equals "Intel Corporation" and class_name equals
        "Processing accelerators" and device_id equals "0b30" then is considered that a N3000 was found.

        Returns: True if this host has a n3000 device.

        """
        return any(item.vendor_name == "Intel Corporation" and item.class_name == "Processing accelerators" and item.device_id == "0b30" for item in self.system_host_devices)

    def has_host_fpga(self):
        """
        This function just returns the result of has_host_n3000, because N3000 device has an FPGA chip inside it.

        Returns: True if this host has a device (N3000) with an FPGA.

        """
        return self.has_host_n3000()

    def has_host_acc100(self):
        """
        This function will look for an ACC100 card in the list of devices
        If there is at least a device with vendor_id equals "Intel Corporation" and class_name equals
        "Processing accelerators" and device_id equals "0d5c" then is considered that an ACC100 was found.

        Returns: True if this host has an ACC100 device.

        """
        return any(item.vendor_name == "Intel Corporation" and item.class_name == "Processing accelerators" and item.device_id == "0d5c" for item in self.system_host_devices)

    def has_host_acc200(self):
        """
        This function will look for an ACC200 card in the list of devices
        If there is at least a device with vendor_id equals "Intel Corporation" and class_name equals
        "Processing accelerators" and device_id equals "57c0" then is considered that an ACC200 was found.

        Returns: True if this host has an ACC200 device.

        """
        return any(item.vendor_name == "Intel Corporation" and item.class_name == "Processing accelerators" and item.device_id == "57c0" for item in self.system_host_devices)
