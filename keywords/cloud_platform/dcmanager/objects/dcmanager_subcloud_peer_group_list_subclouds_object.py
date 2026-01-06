class DcManagerSubcloudPeerGroupListSubcloudsObject:
    """Represents a subcloud from 'dcmanager subcloud-peer-group list-subclouds' command output."""

    def __init__(self, id: str):
        """Initialize subcloud object.

        Args:
            id (str): The subcloud ID.
        """
        self.id: str = id
        self.name: str
        self.description: str
        self.location: str
        self.software_version: str
        self.management: str
        self.availability: str
        self.deploy_status: str
        self.management_subnet: str
        self.management_start_ip: str
        self.management_end_ip: str
        self.management_gateway_ip: str
        self.systemcontroller_gateway_ip: str
        self.group_id: str
        self.peer_group_id: str
        self.created_at: str
        self.updated_at: str
        self.backup_status: str
        self.backup_datetime: str
        self.prestage_status: str
        self.prestage_versions: str

    def get_id(self) -> str:
        """Get subcloud ID.

        Returns:
            str: Subcloud ID.
        """
        return self.id

    def set_id(self, id: str):
        """Set subcloud ID.

        Args:
            id (str): Subcloud ID to set.
        """
        self.id = id

    def get_name(self) -> str:
        """Get subcloud name.

        Returns:
            str: Subcloud name.
        """
        return self.name

    def set_name(self, name: str):
        """Set subcloud name.

        Args:
            name (str): Subcloud name to set.
        """
        self.name = name

    def get_description(self) -> str:
        """Get subcloud description.

        Returns:
            str: Subcloud description.
        """
        return self.description

    def set_description(self, description: str):
        """Set subcloud description.

        Args:
            description (str): Subcloud description to set.
        """
        self.description = description

    def get_location(self) -> str:
        """Get subcloud location.

        Returns:
            str: Subcloud location.
        """
        return self.location

    def set_location(self, location: str):
        """Set subcloud location.

        Args:
            location (str): Subcloud location to set.
        """
        self.location = location

    def get_software_version(self) -> str:
        """Get software version.

        Returns:
            str: Software version.
        """
        return self.software_version

    def set_software_version(self, software_version: str):
        """Set software version.

        Args:
            software_version (str): Software version to set.
        """
        self.software_version = software_version

    def get_management(self) -> str:
        """Get management status.

        Returns:
            str: Management status.
        """
        return self.management

    def set_management(self, management: str):
        """Set management status.

        Args:
            management (str): Management status to set.
        """
        self.management = management

    def get_availability(self) -> str:
        """Get availability status.

        Returns:
            str: Availability status.
        """
        return self.availability

    def set_availability(self, availability: str):
        """Set availability status.

        Args:
            availability (str): Availability status to set.
        """
        self.availability = availability

    def get_deploy_status(self) -> str:
        """Get deploy status.

        Returns:
            str: Deploy status.
        """
        return self.deploy_status

    def set_deploy_status(self, deploy_status: str):
        """Set deploy status.

        Args:
            deploy_status (str): Deploy status to set.
        """
        self.deploy_status = deploy_status

    def get_management_subnet(self) -> str:
        """Get management subnet.

        Returns:
            str: Management subnet.
        """
        return self.management_subnet

    def set_management_subnet(self, management_subnet: str):
        """Set management subnet.

        Args:
            management_subnet (str): Management subnet to set.
        """
        self.management_subnet = management_subnet

    def get_management_start_ip(self) -> str:
        """Get management start IP.

        Returns:
            str: Management start IP.
        """
        return self.management_start_ip

    def set_management_start_ip(self, management_start_ip: str):
        """Set management start IP.

        Args:
            management_start_ip (str): Management start IP to set.
        """
        self.management_start_ip = management_start_ip

    def get_management_end_ip(self) -> str:
        """Get management end IP.

        Returns:
            str: Management end IP.
        """
        return self.management_end_ip

    def set_management_end_ip(self, management_end_ip: str):
        """Set management end IP.

        Args:
            management_end_ip (str): Management end IP to set.
        """
        self.management_end_ip = management_end_ip

    def get_management_gateway_ip(self) -> str:
        """Get management gateway IP.

        Returns:
            str: Management gateway IP.
        """
        return self.management_gateway_ip

    def set_management_gateway_ip(self, management_gateway_ip: str):
        """Set management gateway IP.

        Args:
            management_gateway_ip (str): Management gateway IP to set.
        """
        self.management_gateway_ip = management_gateway_ip

    def get_systemcontroller_gateway_ip(self) -> str:
        """Get system controller gateway IP.

        Returns:
            str: System controller gateway IP.
        """
        return self.systemcontroller_gateway_ip

    def set_systemcontroller_gateway_ip(self, systemcontroller_gateway_ip: str):
        """Set system controller gateway IP.

        Args:
            systemcontroller_gateway_ip (str): System controller gateway IP to set.
        """
        self.systemcontroller_gateway_ip = systemcontroller_gateway_ip

    def get_group_id(self) -> str:
        """Get group ID.

        Returns:
            str: Group ID.
        """
        return self.group_id

    def set_group_id(self, group_id: str):
        """Set group ID.

        Args:
            group_id (str): Group ID to set.
        """
        self.group_id = group_id

    def get_peer_group_id(self) -> str:
        """Get peer group ID.

        Returns:
            str: Peer group ID.
        """
        return self.peer_group_id

    def set_peer_group_id(self, peer_group_id: str):
        """Set peer group ID.

        Args:
            peer_group_id (str): Peer group ID to set.
        """
        self.peer_group_id = peer_group_id

    def get_created_at(self) -> str:
        """Get creation timestamp.

        Returns:
            str: Creation timestamp.
        """
        return self.created_at

    def set_created_at(self, created_at: str):
        """Set creation timestamp.

        Args:
            created_at (str): Creation timestamp to set.
        """
        self.created_at = created_at

    def get_updated_at(self) -> str:
        """Get update timestamp.

        Returns:
            str: Update timestamp.
        """
        return self.updated_at

    def set_updated_at(self, updated_at: str):
        """Set update timestamp.

        Args:
            updated_at (str): Update timestamp to set.
        """
        self.updated_at = updated_at

    def get_backup_status(self) -> str:
        """Get backup status.

        Returns:
            str: Backup status.
        """
        return self.backup_status

    def set_backup_status(self, backup_status: str):
        """Set backup status.

        Args:
            backup_status (str): Backup status to set.
        """
        self.backup_status = backup_status

    def get_backup_datetime(self) -> str:
        """Get backup datetime.

        Returns:
            str: Backup datetime.
        """
        return self.backup_datetime

    def set_backup_datetime(self, backup_datetime: str):
        """Set backup datetime.

        Args:
            backup_datetime (str): Backup datetime to set.
        """
        self.backup_datetime = backup_datetime

    def get_prestage_status(self) -> str:
        """Get prestage status.

        Returns:
            str: Prestage status.
        """
        return self.prestage_status

    def set_prestage_status(self, prestage_status: str):
        """Set prestage status.

        Args:
            prestage_status (str): Prestage status to set.
        """
        self.prestage_status = prestage_status

    def get_prestage_versions(self) -> str:
        """Get prestage versions.

        Returns:
            str: Prestage versions.
        """
        return self.prestage_versions

    def set_prestage_versions(self, prestage_versions: str):
        """Set prestage versions.

        Args:
            prestage_versions (str): Prestage versions to set.
        """
        self.prestage_versions = prestage_versions

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            str: String representation of the object.
        """
        return f"{self.__class__.__name__}(Name={self.name})"
