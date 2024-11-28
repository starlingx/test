from keywords.cloud_platform.system.host.objects.system_host_port_show_object import SystemHostPortShowObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemHostPortShowOutput:
    """
    This class parses the output of 'system host-port-show' commands into a SystemHostPortShowObject
    """

    def __init__(self, system_host_port_output):
        """
        Constructor

        Args:
            system_host_port_output: String output of 'system host-port-show' command
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_host_port_output)
        output_values = system_vertical_table_parser.get_output_values_dict()
        self.system_host_port_object = SystemHostPortShowObject()

        if 'name' in output_values:
            self.system_host_port_object.set_name(output_values['name'])

        if 'namedisplay' in output_values:
            self.system_host_port_object.set_name_display(output_values['namedisplay'])

        if 'type' in output_values:
            self.system_host_port_object.set_type(output_values['type'])

        if 'pciaddr' in output_values:
            self.system_host_port_object.set_type(output_values['pciaddr'])

        if 'dev_id' in output_values:
            self.system_host_port_object.set_dev_id(int(output_values['dev_id']))

        if 'processor' in output_values:
            self.system_host_port_object.set_processor(int(output_values['processor']))

        if 'sriov_totalvfs' in output_values:
            self.system_host_port_object.set_sriov_totalvfs(output_values['sriov_totalvfs'])

        if 'sriov_numvfs' in output_values:
            self.system_host_port_object.set_sriov_numvfs(int(output_values['sriov_numvfs']))

        if 'sriov_vfs_pci_address' in output_values:
            self.system_host_port_object.set_sriov_vfs_pci_address(output_values['sriov_vfs_pci_address'])

        if 'sriov_vf_driver' in output_values:
            self.system_host_port_object.set_sriov_vf_driver(output_values['sriov_vf_driver'])

        if 'sriov_vf_pdevice_id' in output_values:
            self.system_host_port_object.set_sriov_vf_pdevice_id(output_values['sriov_vf_pdevice_id'])

        if 'driver' in output_values:
            self.system_host_port_object.set_driver(output_values['driver'])

        if 'pclass' in output_values:
            self.system_host_port_object.set_pclass(output_values['pclass'])

        if 'pvendor' in output_values:
            self.system_host_port_object.set_pvendor(output_values['pvendor'])

        if 'pdevice' in output_values:
            self.system_host_port_object.set_pdevice(output_values['pdevice'])

        if 'uuid' in output_values:
            self.system_host_port_object.set_uuid(output_values['uuid'])

        if 'host_uuid' in output_values:
            self.system_host_port_object.set_host_uuid(output_values['host_uuid'])

        if 'interface_uuid' in output_values:
            self.system_host_port_object.set_interface_uuid(output_values['interface_uuid'])

        if 'accelerated' in output_values:
            self.system_host_port_object.set_accelerated(bool(output_values['accelerated']))

        if 'created_at' in output_values:
            self.system_host_port_object.set_created_at(output_values['created_at'])

        if 'updated_at' in output_values:
            self.system_host_port_object.set_updated_at(output_values['updated_at'])

        if 'capabilities' in output_values:
            self.system_host_port_object.set_capabilities(output_values['capabilities'])

    def get_host_port_show(self):
        return self.system_host_port_object