from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.configuration.system.objects.system_object import SystemObject


class SystemOutput:
    """
    Class for System Output
    """
    def __init__(self, system_output: RestResponse):
        
        system = system_output.get_json_content()['isystems'][0]  # there will only be one system

        self.system_object = SystemObject(system['uuid']) 

        if system['name']:
            self.system_object.set_name(system['name'])
        if system['system_type']:
            self.system_object.set_system_type(system['system_type'])
        if system['system_mode']:
            self.system_object.set_system_mode(system['system_mode'])
        if system['description']:
            self.system_object.set_description(system['description'])
        if system['contact']:
            self.system_object.set_contact(system['contact'])
        if system['location']:
            self.system_object.set_location(system['location'])
        if system['latitude']:
            self.system_object.set_latitude(system['latitude'])
        if system['longitude']:
            self.system_object.set_longitude(system['longitude'])
        if system['software_version']:
            self.system_object.set_software_version(system['software_version'])
        if system['timezone']:
            self.system_object.set_timezone(system['timezone'])
        if system['links']:
            self.system_object.set_links(system['links'])
        if system['capabilities']:
            self.system_object.set_capabilities(system['capabilities'])
        if system['region_name']:
            self.system_object.set_region_name(system['region_name'])
        if system['distributed_cloud_role']:
            self.system_object.set_distributed_cloud_role(system['distributed_cloud_role'])
        if system['service_project_name']:
            self.system_object.set_service_project_name(system['service_project_name'])
        if system['security_feature']:
            self.system_object.set_security_feature(system['security_feature'])
        if system['created_at']:
            self.system_object.set_created_at(system['created_at'])
        if system['updated_at']:
            self.system_object.set_updated_at(system['updated_at'])

    def get_system_object(self) -> SystemObject:
        """
        Getter for system object

        Return: the system object
        """
        return self.system_object