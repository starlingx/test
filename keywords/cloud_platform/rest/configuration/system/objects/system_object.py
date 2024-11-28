import json5
from keywords.cloud_platform.rest.configuration.system.objects.system_capabilities_object import SystemCapabilitiesObject
from keywords.cloud_platform.system.host.objects.host_capabilities_object import HostCapabilities


class SystemObject:
    """
    Class for System Object
    """

    def __init__(self, uuid: str):
        self.uuid = uuid

        self.name: str = None
        self.system_type: str = None
        self.system_mode: str = None
        self.description: str = None
        self.contact: str = None
        self.location: str = None
        self.latitude: str = None
        self.longitude: str = None
        self.software_version: str = None
        self.timezone: str = None
        self.links = None
        self.capabilities: HostCapabilities = None
        self.region_name: str = None
        self.distributed_cloud_role: str = None
        self.service_project_name: str = None
        self.security_feature: str = None
        self.created_at: str = None
        self.updated_at: str = None

    def set_name(self, name: str):
        """
        Setter for name
        Args
            name () - the name 
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for name
        Args
            
        """
        return self.name
    
    def set_system_type(self, system_type: str):
        """
        Setter for system_type
        Args
            system_type () - the system_type 
        """
        self.system_type = system_type

    def get_system_type(self) -> str:
        """
        Getter for system_type
        Args
            
        """
        return self.system_type
    
    def set_system_mode(self, system_mode: str):
        """
        Setter for system_mode
        Args
            system_mode () - the system_mode 
        """
        self.system_mode = system_mode

    def get_system_mode(self) -> str:
        """
        Getter for system_mode
        Args
            
        """
        return self.system_mode
    
    def set_description(self, description: str):
        """
        Setter for description
        Args
            description () - the description 
        """
        self.description = description

    def get_description(self) -> str:
        """
        Getter for description
        Args
            
        """
        return self.description
    
    def set_contact(self, contact: str):
        """
        Setter for contact
        Args
            contact () - the contact 
        """
        self.contact = contact

    def get_contact(self) -> str:
        """
        Getter for contact
        Args
            
        """
        return self.contact
    
    def set_location(self, location: str):
        """
        Setter for location
        Args
            location () - the location 
        """
        self.location = location

    def get_location(self) -> str:
        """
        Getter for location
        Args
            
        """
        return self.location
    
    def set_latitude(self, latitude: str):
        """
        Setter for latitude
        Args
            latitude () - the latitude 
        """
        self.latitude = latitude

    def get_latitude(self) -> str:
        """
        Getter for latitude
        Args
            
        """
        return self.latitude
    
    def set_longitude(self, longitude: str):
        """
        Setter for longitude
        Args
            longitude () - the longitude 
        """
        self.longitude = longitude

    def get_longitude(self) -> str:
        """
        Getter for longitude
        Args
            
        """
        return self.longitude
    
    def set_software_version(self, software_version: str):
        """
        Setter for software_version
        Args
            software_version () - the software_version 
        """
        self.software_version = software_version

    def get_software_version(self) -> str:
        """
        Getter for software_version
        Args
            
        """
        return self.software_version
    
    def set_timezone(self, timezone: str):
        """
        Setter for timezone
        Args
            name () - the timezone 
        """
        self.timezone = timezone

    def get_timezone(self) -> str:
        """
        Getter for timezone
        Args
            
        """
        return self.timezone
    
    def set_links(self, links: str):
        """
        Setter for links
        Args
            links () - the links 
        """
        self.links = links

    def get_links(self) -> str:
        """
        Getter for links
        Args
            
        """
        return self.links
    
    def set_capabilities(self, capabilities):
        """
        Setter for host capabilities
        Args:
            capabilities (): the string of capabilities from the system host-list command (json format)

        Returns:

        """
        
        system_capability = SystemCapabilitiesObject()
        if 'region_config' in capabilities:
            system_capability.set_region_config(capabilities['region_config'])
        if 'vswitch_type' in capabilities:
            system_capability.set_vswitch_type(capabilities['vswitch_type'])
        if 'shared_services' in capabilities:
            system_capability.set_shared_services(capabilities['shared_services'])
        if 'sdn_enabled' in capabilities:
            system_capability.set_sdn_enabled(capabilities['sdn_enabled'])
        if 'https_enabled' in capabilities:
            system_capability.set_https_enabled(capabilities['https_enabled'])
        if 'bm_region' in capabilities:
            system_capability.set_bm_region(capabilities['bm_region'])

        self.capabilities = capabilities

    def get_capabilities(self) -> SystemCapabilitiesObject:
        """
        Getter for capabilities
        Returns:

        """
        return self.capabilities
    
    def set_region_name(self, region_name: str):
        """
        Setter for region_name
        Args
            region_name () - the region_name 
        """
        self.region_name = region_name

    def get_region_name(self) -> str:
        """
        Getter for region_name
        Args
            
        """
        return self.region_name
    
    def set_distributed_cloud_role(self, distributed_cloud_role: str):
        """
        Setter for distributed_cloud_role
        Args
            distributed_cloud_role () - the distributed_cloud_role 
        """
        self.distributed_cloud_role = distributed_cloud_role

    def get_distributed_cloud_role(self) -> str:
        """
        Getter for distributed_cloud_role
        Args
            
        """
        return self.distributed_cloud_role
    
    def set_service_project_name(self, service_project_name: str):
        """
        Setter for service_project_name
        Args
            service_project_name () - the service_project_name 
        """
        self.service_project_name = service_project_name

    def get_service_project_name(self) -> str:
        """
        Getter for service_project_name
        Args
            
        """
        return self.service_project_name
    
    def set_security_feature(self, security_feature: str):
        """
        Setter for security_feature
        Args
            security_feature () - the security_feature 
        """
        self.security_feature = security_feature

    def get_security_feature(self) -> str:
        """
        Getter for security_feature
        Args
            
        """
        return self.security_feature
    
    def set_created_at(self, created_at: str):
        """
        Setter for created_at
        Args
            created_at () - the created_at 
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for created_at
        Args
            
        """
        return self.created_at
    
    def set_updated_at(self, updated_at: str):
        """
        Setter for updated_at
        Args
            updated_at () - the updated_at 
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for updated_at
        Args
            
        """
        return self.updated_at