from keywords.cloud_platform.system.host.objects.system_host_interface_object import SystemHostInterfaceObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostIfShowOutput:
    """
    Class for System Host If SHOW Output
    """

    def __init__(self, system_host_if_show_output):
        system_table_parser = SystemTableParser(system_host_if_show_output)
        self.output_values = system_table_parser.get_output_values_list()
        self.system_host_interface_object = SystemHostInterfaceObject()

        ifname = self.get_property_value('ifname')
        if ifname:
            self.system_host_interface_object.set_ifname(ifname)

        iftype = self.get_property_value('iftype')
        if iftype:
            self.system_host_interface_object.set_iftype(iftype)

        ports = self.get_property_value('ports')
        if ports:
            self.system_host_interface_object.set_ports(ports)

        imac = self.get_property_value('imac')
        if imac:
            self.system_host_interface_object.set_imac(imac)

        imtu = self.get_property_value('imtu')
        if imtu:
            self.system_host_interface_object.set_imtu(imtu)

        ifclass = self.get_property_value('ifclass')
        if ifclass:
            self.system_host_interface_object.set_ifclass(ifclass)

        ptp_role = self.get_property_value('ptp_role')
        if ptp_role:
            self.system_host_interface_object.set_ptp_role(ptp_role)

        aemode = self.get_property_value('aemode')
        if aemode:
            self.system_host_interface_object.set_aemode(aemode)

        schedpolicy = self.get_property_value('schedpolicy')
        if schedpolicy:
            self.system_host_interface_object.set_schedpolicy(schedpolicy)

        txhashpolicy = self.get_property_value('txhashpolicy')
        if txhashpolicy:
            self.system_host_interface_object.set_txhashpolicy(txhashpolicy)

        primary_reselect = self.get_property_value('primary_reselect')
        if primary_reselect:
            self.system_host_interface_object.set_primary_reselect(primary_reselect)

        uuid = self.get_property_value('uuid')
        if uuid:
            self.system_host_interface_object.set_uuid(uuid)

        ihost_uuid = self.get_property_value('ihost_uuid')
        if ihost_uuid:
            self.system_host_interface_object.set_ihost_uuid(ihost_uuid)

        vlan_id = self.get_property_value('vlan_id')
        if vlan_id:
            self.system_host_interface_object.set_vlan_id(vlan_id)

        uses = self.get_property_value('uses')
        if uses:
            self.system_host_interface_object.set_uses(uses)

        used_by = self.get_property_value('used_by')
        if used_by:
            self.system_host_interface_object.set_used_by(used_by)

        created_at = self.get_property_value('created_at')
        if created_at:
            self.system_host_interface_object.set_created_at(created_at)

        updated_at = self.get_property_value('updated_at')
        if updated_at:
            self.system_host_interface_object.set_updated_at(updated_at)

        sriov_numvfs = self.get_property_value('sriov_numvfs')
        if sriov_numvfs:
            self.system_host_interface_object.set_sriov_numvfs(sriov_numvfs)

        sriov_vf_driver = self.get_property_value('sriov_vf_driver')
        if sriov_vf_driver:
            self.system_host_interface_object.set_sriov_vf_driver(sriov_vf_driver)

        max_tx_rate = self.get_property_value('max_tx_rate')
        if schedpolicy:
            self.system_host_interface_object.set_max_tx_rate(max_tx_rate)

        accelerated = self.get_property_value('accelerated')
        if accelerated:
            self.system_host_interface_object.set_accelerated(accelerated)

    def get_property_value(self, property: str):
        """
        Returns the value of the property
        Args:
            property (): the property name to get the value for

        Returns:

        """
        values = list(filter(lambda property_dict: property_dict['Property'] == property, self.output_values))
        if len(values) == 0:
            return None  # no key was found

        return values[0]['Value']

    def get_system_host_interface_object(self) -> SystemHostInterfaceObject:
        """
        Returns the system host interface object
        Returns:

        """
        return self.system_host_interface_object
