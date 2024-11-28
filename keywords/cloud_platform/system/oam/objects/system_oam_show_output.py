from keywords.cloud_platform.system.host.objects.system_host_label_object import SystemHostLabelObject
from keywords.cloud_platform.system.oam.objects.system_oam_show_object import SystemOamShowObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemOamShowOutput:
    """
    Class for System OAM SHOW Output
    """

    def __init__(self, system_oam_output):
        system_table_parser = SystemTableParser(system_oam_output)
        self.output_values = system_table_parser.get_output_values_list()
        self.system_oam_show_object = SystemOamShowObject()

        created_at = self.get_property_value('created_at')
        if created_at:
            self.system_oam_show_object.set_created_at(created_at)

        isystem_uuid = self.get_property_value('isystem_uuid')
        if isystem_uuid:
            self.system_oam_show_object.set_isystem_uuid(isystem_uuid)

        oam_c0_ip = self.get_property_value('oam_c0_ip')
        if oam_c0_ip:
            self.system_oam_show_object.set_oam_c0_ip(oam_c0_ip)

        oam_c1_ip = self.get_property_value('oam_c1_ip')
        if oam_c1_ip:
            self.system_oam_show_object.set_oam_c1_ip(oam_c1_ip)

        oam_floating_ip = self.get_property_value('oam_floating_ip')
        if oam_floating_ip:
            self.system_oam_show_object.set_oam_floating_ip(oam_floating_ip)

        oam_gateway_ip = self.get_property_value('oam_gateway_ip')
        if oam_gateway_ip:
            self.system_oam_show_object.set_oam_gateway_ip(oam_gateway_ip)

        oam_subnet = self.get_property_value('oam_subnet')
        if oam_subnet:
            self.system_oam_show_object.set_oam_subnet(oam_subnet)

        updated_at = self.get_property_value('updated_at')
        if updated_at:
            self.system_oam_show_object.set_updated_at(updated_at)

        uuid = self.get_property_value('uuid')
        if uuid:
            self.system_oam_show_object.set_uuid(uuid)

        oam_ip = self.get_property_value('oam_ip')
        if oam_ip:
            self.system_oam_show_object.set_oam_ip(oam_ip)

    def get_property_value(self, property: str) -> SystemHostLabelObject:
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
