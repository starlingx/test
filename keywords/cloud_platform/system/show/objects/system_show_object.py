class SystemShowObject:
    """
    This class represents a System Show as an object.
    This is typically a line in the system show output vertical table.
    """

    def __init__(self):
        self.contact = None
        self.created_at = None
        self.description = None
        self.distributed_cloud_role = None
        self.https_enabled: bool = True
        self.latitude = None
        self.location = None
        self.longitude = None
        self.name = None
        self.region_name = None
        self.sdn_enabled: bool = False
        self.security_feature = None
        self.service_project_name = None
        self.software_version = None
        self.system_mode = None
        self.system_type = None
        self.timezone = None
        self.updated_at = None
        self.uuid = None
        self.vswitch_type = None

    def set_contact(self, contact: str):
        """
        Setter for the contact
        """
        self.contact = contact

    def get_contact(self) -> str:
        """
        Getter for this contact
        """
        return self.contact

    def set_created_at(self, created_at: str):
        """
        Setter for the created_at
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for the created_at
        """
        return self.created_at

    def set_description(self, description: str):
        """
        Setter for the description
        """
        self.description = description

    def get_description(self) -> str:
        """
        Getter for the description.
        """
        return self.description

    def set_distributed_cloud_role(self, distributed_cloud_role: str):
        """
        Setter for the distributed_cloud_role
        """
        self.distributed_cloud_role = distributed_cloud_role

    def get_distributed_cloud_role(self) -> str:
        """
        Getter for the distributed_cloud_role
        """
        return self.distributed_cloud_role

    def set_https_enabled(self, https_enabled: bool):
        """
        Setter for the https_enabled
        """
        self.https_enabled = https_enabled

    def get_https_enabled(self) -> bool:
        """
        Getter for the https_enabled
        """
        return self.https_enabled

    def set_latitude(self, latitude: str):
        """
        Setter for the latitude
        """
        self.latitude = latitude

    def get_latitude(self) -> str:
        """
        Getter for the latitude
        """
        return self.latitude

    def set_location(self, location: str):
        """
        Setter for the location.
        """
        self.location = location

    def get_location(self) -> str:
        """
        Getter for the location.
        """
        return self.location

    def set_longitude(self, longitude: str):
        """
        Setter for the longitude.
        """
        self.longitude = longitude

    def get_longitude(self) -> str:
        """
        Getter for the longitude.
        """
        return self.longitude

    def set_name(self, name: str):
        """
        Setter for the name.
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for the name.
        """
        return self.name

    def set_region_name(self, region_name: str):
        """
        Setter for the region_name.
        """
        self.region_name = region_name

    def get_region_name(self) -> str:
        """
        Getter for the region_name.
        """
        return self.region_name

    def set_sdn_enabled(self, sdn_enabled: bool):
        """
        Setter for the sdn_enabled.
        """
        self.sdn_enabled = sdn_enabled

    def get_sdn_enabled(self) -> bool:
        """
        Getter for the sdn_enabled.
        """
        return self.sdn_enabled

    def set_security_feature(self, security_feature: str):
        """
        Setter for the security_feature.
        """
        self.security_feature = security_feature

    def get_security_feature(self) -> str:
        """
        Getter for the security_feature.
        """
        return self.security_feature

    def set_service_project_name(self, service_project_name: str):
        """
        Setter for the service_project_name.
        """
        self.service_project_name = service_project_name

    def get_service_project_name(self) -> str:
        """
        Getter for the service_project_name.
        """
        return self.service_project_name

    def set_software_version(self, software_version: str):
        """
        Setter for the software_version.
        """
        self.software_version = software_version

    def get_software_version(self) -> str:
        """
        Getter for the software_version.
        """
        return self.software_version

    def set_system_mode(self, system_mode: str):
        """
        Setter for the system_mode.
        """
        self.system_mode = system_mode

    def get_system_mode(self) -> str:
        """
        Getter for the system_mode.
        """
        return self.system_mode

    def set_system_type(self, system_type: str):
        """
        Setter for the system_type.
        """
        self.system_type = system_type

    def get_system_type(self) -> str:
        """
        Getter for the system_type.
        """
        return self.system_type

    def set_timezone(self, timezone: str):
        """
        Setter for the timezone.
        """
        self.timezone = timezone

    def get_timezone(self) -> str:
        """
        Getter for the timezone.
        """
        return self.timezone

    def set_updated_at(self, updated_at: str):
        """
        Setter for the updated_at.
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for the updated_at.
        """
        return self.updated_at

    def set_uuid(self, uuid: str):
        """
        Setter for the uuid.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for the uuid.
        """
        return self.uuid

    def set_vswitch_type(self, vswitch_type: str):
        """
        Setter for the vswitch_type.
        """
        self.vswitch_type = vswitch_type

    def get_vswitch_type(self) -> str:
        """
        Getter for the vswitch_type.
        """
        return self.vswitch_type

