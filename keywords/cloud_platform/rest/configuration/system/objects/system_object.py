from keywords.cloud_platform.rest.configuration.system.objects.system_capabilities_object import SystemCapabilitiesObject


class SystemObject:
    """Represents a StarlingX system with its configuration and metadata."""

    def __init__(self, uuid: str):
        """Initialize a SystemObject with the given UUID.

        Args:
            uuid (str): The unique identifier for the system.
        """
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
        self.capabilities: SystemCapabilitiesObject = None
        self.region_name: str = None
        self.distributed_cloud_role: str = None
        self.service_project_name: str = None
        self.security_feature: str = None
        self.created_at: str = None
        self.updated_at: str = None

    def set_name(self, name: str):
        """Set the system name.

        Args:
            name (str): The name of the system.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the system name.

        Returns:
            str: The name of the system.
        """
        return self.name

    def set_system_type(self, system_type: str):
        """Set the system type.

        Args:
            system_type (str): The type of the system.
        """
        self.system_type = system_type

    def get_system_type(self) -> str:
        """Get the system type.

        Returns:
            str: The type of the system.
        """
        return self.system_type

    def set_system_mode(self, system_mode: str):
        """Set the system mode.

        Args:
            system_mode (str): The mode of the system.
        """
        self.system_mode = system_mode

    def get_system_mode(self) -> str:
        """Get the system mode.

        Returns:
            str: The mode of the system.
        """
        return self.system_mode

    def set_description(self, description: str):
        """Set the system description.

        Args:
            description (str): The description of the system.
        """
        self.description = description

    def get_description(self) -> str:
        """Get the system description.

        Returns:
            str: The description of the system.
        """
        return self.description

    def set_contact(self, contact: str):
        """Set the system contact information.

        Args:
            contact (str): The contact information for the system.
        """
        self.contact = contact

    def get_contact(self) -> str:
        """Get the system contact information.

        Returns:
            str: The contact information for the system.
        """
        return self.contact

    def set_location(self, location: str):
        """Set the system location.

        Args:
            location (str): The location of the system.
        """
        self.location = location

    def get_location(self) -> str:
        """Get the system location.

        Returns:
            str: The location of the system.
        """
        return self.location

    def set_latitude(self, latitude: str):
        """Set the system latitude.

        Args:
            latitude (str): The latitude coordinate of the system.
        """
        self.latitude = latitude

    def get_latitude(self) -> str:
        """Get the system latitude.

        Returns:
            str: The latitude coordinate of the system.
        """
        return self.latitude

    def set_longitude(self, longitude: str):
        """Set the system longitude.

        Args:
            longitude (str): The longitude coordinate of the system.
        """
        self.longitude = longitude

    def get_longitude(self) -> str:
        """Get the system longitude.

        Returns:
            str: The longitude coordinate of the system.
        """
        return self.longitude

    def set_software_version(self, software_version: str):
        """Set the system software version.

        Args:
            software_version (str): The software version of the system.
        """
        self.software_version = software_version

    def get_software_version(self) -> str:
        """Get the system software version.

        Returns:
            str: The software version of the system.
        """
        return self.software_version

    def set_timezone(self, timezone: str):
        """Set the system timezone.

        Args:
            timezone (str): The timezone of the system.
        """
        self.timezone = timezone

    def get_timezone(self) -> str:
        """Get the system timezone.

        Returns:
            str: The timezone of the system.
        """
        return self.timezone

    def set_links(self, links: str):
        """Set the system links.

        Args:
            links (str): The links associated with the system.
        """
        self.links = links

    def get_links(self) -> str:
        """Get the system links.

        Returns:
            str: The links associated with the system.
        """
        return self.links

    def set_capabilities(self, capabilities: dict):
        """Set the system capabilities from a dictionary.

        Args:
            capabilities (dict): Dictionary containing system capabilities data.
        """
        system_capability = SystemCapabilitiesObject()
        if "region_config" in capabilities:
            system_capability.set_region_config(capabilities["region_config"])
        if "vswitch_type" in capabilities:
            system_capability.set_vswitch_type(capabilities["vswitch_type"])
        if "shared_services" in capabilities:
            system_capability.set_shared_services(capabilities["shared_services"])
        if "sdn_enabled" in capabilities:
            system_capability.set_sdn_enabled(capabilities["sdn_enabled"])
        if "https_enabled" in capabilities:
            system_capability.set_https_enabled(capabilities["https_enabled"])
        if "bm_region" in capabilities:
            system_capability.set_bm_region(capabilities["bm_region"])

        self.capabilities = system_capability

    def get_capabilities(self) -> SystemCapabilitiesObject:
        """Get the system capabilities object.

        Returns:
            SystemCapabilitiesObject: The system's capabilities object.
        """
        return self.capabilities

    def set_region_name(self, region_name: str):
        """Set the system region name.

        Args:
            region_name (str): The name of the region for this system.
        """
        self.region_name = region_name

    def get_region_name(self) -> str:
        """Get the system region name.

        Returns:
            str: The name of the region for this system.
        """
        return self.region_name

    def set_distributed_cloud_role(self, distributed_cloud_role: str):
        """Set the distributed cloud role.

        Args:
            distributed_cloud_role (str): The distributed cloud role of the system.
        """
        self.distributed_cloud_role = distributed_cloud_role

    def get_distributed_cloud_role(self) -> str:
        """Get the distributed cloud role.

        Returns:
            str: The distributed cloud role of the system.
        """
        return self.distributed_cloud_role

    def set_service_project_name(self, service_project_name: str):
        """Set the service project name.

        Args:
            service_project_name (str): The name of the service project.
        """
        self.service_project_name = service_project_name

    def get_service_project_name(self) -> str:
        """Get the service project name.

        Returns:
            str: The name of the service project.
        """
        return self.service_project_name

    def set_security_feature(self, security_feature: str):
        """Set the security feature.

        Args:
            security_feature (str): The security feature of the system.
        """
        self.security_feature = security_feature

    def get_security_feature(self) -> str:
        """Get the security feature.

        Returns:
            str: The security feature of the system.
        """
        return self.security_feature

    def set_created_at(self, created_at: str):
        """Set the creation timestamp.

        Args:
            created_at (str): The timestamp when the system was created.
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """Get the creation timestamp.

        Returns:
            str: The timestamp when the system was created.
        """
        return self.created_at

    def set_updated_at(self, updated_at: str):
        """Set the update timestamp.

        Args:
            updated_at (str): The timestamp when the system was last updated.
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """Get the update timestamp.

        Returns:
            str: The timestamp when the system was last updated.
        """
        return self.updated_at
