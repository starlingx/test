from typing import Optional


class DcmanagerSubcloudGroupObject:
    """
    This class represents a dcmanager subcloud-group as an object.
    """

    def __init__(self) -> None:
        """Initializes a DcmanagerSubcloudGroupObject with default values."""
        self.id: int = -1
        self.name: Optional[str] = None
        self.description: Optional[str] = None
        self.update_apply_type: Optional[str] = None
        self.max_parallel_subclouds: int = -1
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None
        self.location: Optional[str] = None
        self.software_version: Optional[str] = None
        self.management: Optional[str] = None
        self.availability: Optional[str] = None
        self.deploy_status: Optional[str] = None
        self.management_subnet: Optional[str] = None
        self.management_start_ip: Optional[str] = None
        self.management_end_ip: Optional[str] = None
        self.management_gateway_ip: Optional[str] = None
        self.systemcontroller_gateway_ip: Optional[str] = None
        self.group_id: int = -1
        self.peer_group_id: Optional[str] = None
        self.backup_status: Optional[str] = None
        self.backup_datetime: Optional[str] = None
        self.prestage_status: Optional[str] = None
        self.prestage_versions: Optional[str] = None

    def set_id(self, group_id: int) -> None:
        """Sets the ID of the subcloud group."""
        self.id = group_id

    def get_id(self) -> int:
        """Gets the ID of the subcloud group."""
        return self.id

    def set_name(self, name: str) -> None:
        """Sets the name of the subcloud group."""
        self.name = name

    def get_name(self) -> Optional[str]:
        """Gets the name of the subcloud group."""
        return self.name

    def set_description(self, description: str) -> None:
        """Sets the description of the subcloud group."""
        self.description = description

    def get_description(self) -> Optional[str]:
        """Gets the description of the subcloud group."""
        return self.description

    def set_update_apply_type(self, update_apply_type: str) -> None:
        """Sets the update apply type of the subcloud group."""
        self.update_apply_type = update_apply_type

    def get_update_apply_type(self) -> Optional[str]:
        """Gets the update apply type of the subcloud group."""
        return self.update_apply_type

    def set_max_parallel_subclouds(self, max_parallel_subclouds: int) -> None:
        """Sets the maximum number of parallel subclouds."""
        self.max_parallel_subclouds = max_parallel_subclouds

    def get_max_parallel_subclouds(self) -> int:
        """Gets the maximum number of parallel subclouds."""
        return self.max_parallel_subclouds

    def set_created_at(self, created_at: str) -> None:
        """Sets the creation timestamp of the subcloud group."""
        self.created_at = created_at

    def get_created_at(self) -> Optional[str]:
        """Gets the creation timestamp of the subcloud group."""
        return self.created_at

    def set_updated_at(self, updated_at: str) -> None:
        """Sets the last updated timestamp of the subcloud group."""
        self.updated_at = updated_at

    def get_updated_at(self) -> Optional[str]:
        """Gets the last updated timestamp of the subcloud group."""
        return self.updated_at

    def set_location(self, location: str) -> None:
        """Sets the location of the subcloud."""
        self.location = location

    def get_location(self) -> Optional[str]:
        """Gets the location of the subcloud."""
        return self.location

    def set_software_version(self, software_version: str) -> None:
        """Sets the software_version of the subcloud."""
        self.software_version = software_version

    def get_software_version(self) -> Optional[str]:
        """Gets the software_version of the subcloud."""
        return self.software_version

    def set_management(self, management: str) -> None:
        """Sets the management of the subcloud."""
        self.management = management

    def get_management(self) -> Optional[str]:
        """Gets the management of the subcloud."""
        return self.management

    def set_availability(self, availability: str) -> None:
        """Sets the availability of the subcloud."""
        self.availability = availability

    def get_availability(self) -> Optional[str]:
        """Gets the availability of the subcloud."""
        return self.availability

    def set_deploy_status(self, deploy_status: str) -> None:
        """Sets the deploy_status of the subcloud."""
        self.deploy_status = deploy_status

    def get_deploy_status(self) -> Optional[str]:
        """Gets the deploy_status of the subcloud."""
        return self.deploy_status

    def set_management_subnet(self, management_subnet: str) -> None:
        """Sets the management_subnet of the subcloud."""
        self.management_subnet = management_subnet

    def get_management_subnet(self) -> Optional[str]:
        """Gets the management_subnet of the subcloud."""
        return self.management_subnet

    def set_management_start_ip(self, management_start_ip: str) -> None:
        """Sets the management_start_ip of the subcloud."""
        self.management_start_ip = management_start_ip

    def get_management_start_ip(self) -> Optional[str]:
        """Gets the management_start_ip of the subcloud."""
        return self.management_start_ip

    def set_management_end_ip(self, management_end_ip: str) -> None:
        """Sets the management_end_ip of the subcloud."""
        self.management_end_ip = management_end_ip

    def get_management_end_ip(self) -> Optional[str]:
        """Gets the management_end_ip of the subcloud."""
        return self.management_end_ip

    def set_management_gateway_ip(self, management_gateway_ip: str) -> None:
        """Sets the management_gateway_ip of the subcloud."""
        self.management_gateway_ip = management_gateway_ip

    def get_management_gateway_ip(self) -> Optional[str]:
        """Gets the management_gateway_ip of the subcloud."""
        return self.management_gateway_ip

    def set_systemcontroller_gateway_ip(self, systemcontroller_gateway_ip: str) -> None:
        """Sets the systemcontroller_gateway_ip of the subcloud."""
        self.systemcontroller_gateway_ip = systemcontroller_gateway_ip

    def get_systemcontroller_gateway_ip(self) -> Optional[str]:
        """Gets the systemcontroller_gateway_ip of the subcloud."""
        return self.systemcontroller_gateway_ip

    def set_group_id(self, group_id: int) -> None:
        """Sets the group_id of the subcloud."""
        self.group_id = group_id

    def get_group_id(self) -> int:
        """Gets the group_id of the subcloud."""
        return self.group_id

    def set_peer_group_id(self, peer_group_id: str) -> None:
        """Sets the peer_group_id of the subcloud."""
        self.peer_group_id = peer_group_id

    def get_peer_group_id(self) -> Optional[str]:
        """Gets the peer_group_id of the subcloud."""
        return self.peer_group_id

    def set_backup_status(self, backup_status: str) -> None:
        """Sets the backup_status of the subcloud."""
        self.backup_status = backup_status

    def get_backup_status(self) -> Optional[str]:
        """Gets the backup_status of the subcloud."""
        return self.backup_status

    def set_backup_datetime(self, backup_datetime: str) -> None:
        """Sets the backup_datetime of the subcloud."""
        self.backup_datetime = backup_datetime

    def get_backup_datetime(self) -> Optional[str]:
        """Gets the backup_datetime of the subcloud."""
        return self.backup_datetime

    def set_prestage_status(self, prestage_status: str) -> None:
        """Sets the prestage_status of the subcloud."""
        self.prestage_status = prestage_status

    def get_prestage_status(self) -> Optional[str]:
        """Gets the prestage_status of the subcloud."""
        return self.prestage_status

    def set_prestage_versions(self, prestage_versions: str) -> None:
        """Sets the prestage_versions of the subcloud."""
        self.prestage_versions = prestage_versions

    def get_prestage_versions(self) -> Optional[str]:
        """Gets the prestage_versions of the subcloud."""
        return self.prestage_versions
