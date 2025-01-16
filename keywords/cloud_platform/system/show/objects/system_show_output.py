from keywords.cloud_platform.system.show.objects.system_show_object import SystemShowObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemShowOutput:
    """
    This class parses the output of 'system show' command into an object of type SystemShowObject.
    """

    def __init__(self, system_show_output):
        """
        Constructor

        Args:
            system_show_output: output of 'system show' command as a list of strings.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_show_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        self.system_host_show_object = SystemShowObject()

        if 'contact' in output_values:
            self.system_host_show_object.set_contact(output_values['contact'])

        if 'created_at' in output_values:
            self.system_host_show_object.set_created_at(output_values['created_at'])

        if 'description' in output_values:
            self.system_host_show_object.set_description(output_values['description'])

        if 'distributed_cloud_role' in output_values:
            self.system_host_show_object.set_description(output_values['distributed_cloud_role'])

        if 'https_enabled' in output_values:
            self.system_host_show_object.set_https_enabled(output_values['https_enabled'])

        if 'latitude' in output_values:
            self.system_host_show_object.set_latitude(output_values['latitude'])

        if 'location' in output_values:
            self.system_host_show_object.set_location(output_values['location'])

        if 'longitude' in output_values:
            self.system_host_show_object.set_longitude(output_values['longitude'])

        if 'name' in output_values:
            self.system_host_show_object.set_name(output_values['name'])

        if 'region_name' in output_values:
            self.system_host_show_object.set_region_name(output_values['region_name'])

        if 'sdn_enabled' in output_values:
            self.system_host_show_object.set_sdn_enabled(output_values['sdn_enabled'])

        if 'security_feature' in output_values:
            self.system_host_show_object.set_security_feature(output_values['security_feature'])

        if 'service_project_name' in output_values:
            self.system_host_show_object.set_service_project_name(output_values['service_project_name'])

        if 'software_version' in output_values:
            self.system_host_show_object.set_software_version(output_values['software_version'])

        if 'system_mode' in output_values:
            self.system_host_show_object.set_system_mode(output_values['system_mode'])

        if 'system_type' in output_values:
            self.system_host_show_object.set_system_type(output_values['system_type'])

        if 'timezone' in output_values:
            self.system_host_show_object.set_timezone(output_values['timezone'])

        if 'updated_at' in output_values:
            self.system_host_show_object.set_updated_at(output_values['updated_at'])

        if 'uuid' in output_values:
            self.system_host_show_object.set_uuid(output_values['uuid'])

        if 'vswitch_type' in output_values:
            self.system_host_show_object.set_vswitch_type(output_values['vswitch_type'])

    def get_system_show_object(self) -> SystemShowObject:
        """
        Get system show object

        Returns: system show object

        """
        return self.system_host_show_object
