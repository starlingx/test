from typing import Optional


class DcManagerSubcloudManageObject:
    """
    This class typically represents the output of the 'dcmanager subcloud <manage/unmanage> <subcloud name>' command as
    shown below.

        +-----------------------------+----------------------------+
        | Field                       | Value                      |
        +-----------------------------+----------------------------+
        | id                          | 2                          |
        | name                        | subcloud2                  |
        | description                 | None                       |
        | location                    | None                       |
        | software_version            | 24.09                      |
        | management                  | managed                    |
        | availability                | online                     |
        | deploy_status               | complete                   |
        | management_subnet           | ffff:11:88:222::/64        |
        | management_start_ip         | ffff:11:88:222::2          |
        | management_end_ip           | ffff:11:88:222::ffff       |
        | management_gateway_ip       | ffff:11:88:222::1          |
        | systemcontroller_gateway_ip | ffff:11:88:222::1          |
        | group_id                    | 1                          |
        | peer_group_id               | None                       |
        | created_at                  | 2024-11-05T16:22:52.246151 |
        | updated_at                  | 2024-11-13T15:22:28.907157 |
        | backup_status               | None                       |
        | backup_datetime             | None                       |
        | prestage_status             | None                       |
        | prestage_versions           | None                       |
        +-----------------------------+----------------------------+
    """

    def __init__(self):
        """
        Constructor.
        """
        self.id: Optional[str] = None
        self.name: Optional[str] = None
        self.description: Optional[str] = None
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
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None
        self.backup_status: Optional[str] = None
        self.backup_datetime: Optional[str] = None
        self.prestage_status: Optional[str] = None
        self.prestage_versions: Optional[str] = None

    def get_id(self) -> str:
        """
        Getter for this Subcloud Id
        """
        return self.id

    def set_id(self, id: str):
        """
        Setter for the Subcloud Id
        """
        self.id = id

    def get_name(self) -> str:
        """
        Getter for the Subcloud Name
        """
        return self.name

    def set_name(self, name: str):
        """
        Setter for the Subcloud Name
        """
        self.name = name

    def get_description(self) -> str:
        """
        Getter for the Description
        """
        return self.description

    def set_description(self, description: str):
        """
        Setter for the Description
        """
        self.description = description

    def get_location(self) -> str:
        """
        Getter for the Location
        """
        return self.location

    def set_location(self, location: str):
        """
        Setter for the Location
        """
        self.location = location

    def get_software_version(self) -> str:
        """
        Getter for the Software Version
        """
        return self.software_version

    def set_software_version(self, software_version: str):
        """
        Setter for the Software Version
        """
        self.software_version = software_version

    def get_management(self) -> str:
        """
        Getter for the Management
        """
        return self.management

    def set_management(self, management: str):
        """
        Setter for the Management
        """
        self.management = management

    def get_availability(self) -> str:
        """
        Getter for the Availability
        """
        return self.availability

    def set_availability(self, availability: str):
        """
        Setter for the Availability
        """
        self.availability = availability

    def get_deploy_status(self) -> str:
        """
        Getter for the Deploy Status
        """
        return self.deploy_status

    def set_deploy_status(self, deploy_status: str):
        """
        Setter for the Deploy Status
        """
        self.deploy_status = deploy_status

    def get_management_subnet(self) -> str:
        """
        Getter for the Management Subnet
        """
        return self.management_subnet

    def set_management_subnet(self, management_subnet: str):
        """
        Setter for the Management Subnet
        """
        self.management_subnet = management_subnet

    def get_management_start_ip(self) -> str:
        """
        Getter for the Management Start IP
        """
        return self.management_start_ip

    def set_management_start_ip(self, management_start_ip: str):
        """
        Setter for the Management Start IP
        """
        self.management_start_ip = management_start_ip

    def get_management_end_ip(self) -> str:
        """
        Getter for the Management End IP
        """
        return self.management_end_ip

    def set_management_end_ip(self, management_end_ip: str):
        """
        Setter for the Management End IP
        """
        self.management_end_ip = management_end_ip

    def get_management_gateway_ip(self) -> str:
        """
        Getter for the Management Gateway IP
        """
        return self.management_gateway_ip

    def set_management_gateway_ip(self, management_gateway_ip: str):
        """
        Setter for the Management Gateway IP
        """
        self.management_gateway_ip = management_gateway_ip

    def get_systemcontroller_gateway_ip(self) -> str:
        """
        Getter for the System Controller Gateway IP
        """
        return self.systemcontroller_gateway_ip

    def set_systemcontroller_gateway_ip(self, systemcontroller_gateway_ip: str):
        """
        Setter for the System Controller Gateway IP
        """
        self.systemcontroller_gateway_ip = systemcontroller_gateway_ip

    def get_group_id(self) -> int:
        """
        Getter for the Group ID
        """
        return self.group_id

    def set_group_id(self, group_id: int):
        """
        Setter for the Group ID
        """
        self.group_id = group_id

    def get_peer_group_id(self) -> str:
        """
        Getter for the Peer Group ID
        """
        return self.peer_group_id

    def set_peer_group_id(self, peer_group_id: str):
        """
        Setter for the Peer Group ID
        """
        self.peer_group_id = peer_group_id

    def get_created_at(self) -> str:
        """
        Getter for the Created At Timestamp
        """
        return self.created_at

    def set_created_at(self, created_at: str):
        """
        Setter for the Created At Timestamp
        """
        self.created_at = created_at

    def get_updated_at(self) -> str:
        """
        Getter for the Updated At Timestamp
        """
        return self.updated_at

    def set_updated_at(self, updated_at: str):
        """
        Setter for the Updated At Timestamp
        """
        self.updated_at = updated_at

    def get_backup_status(self) -> str:
        """
        Getter for the Backup Status
        """
        return self.backup_status

    def set_backup_status(self, backup_status: str):
        """
        Setter for the Backup Status
        """
        self.backup_status = backup_status

    def get_backup_datetime(self) -> str:
        """
        Getter for the Backup Datetime
        """
        return self.backup_datetime

    def set_backup_datetime(self, backup_datetime: str):
        """
        Setter for the Backup Datetime
        """
        self.backup_datetime = backup_datetime

    def get_prestage_status(self) -> str:
        """
        Getter for the Prestage Status
        """
        return self.prestage_status

    def set_prestage_status(self, prestage_status: str):
        """
        Setter for the Prestage Status
        """
        self.prestage_status = prestage_status

    def get_prestage_versions(self) -> str:
        """
        Getter for the Prestage Versions
        """
        return self.prestage_versions

    def set_prestage_versions(self, prestage_versions: str):
        """
        Setter for the Prestage Versions
        """
        self.prestage_versions = prestage_versions
