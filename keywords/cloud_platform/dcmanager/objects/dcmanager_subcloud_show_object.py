class DcManagerSubcloudShowObject:
    """This class represents a detailed subcloud as object.

    This is typically the output of the 'dcmanager subcloud show <subcloud name>' command output table as shown below.

    +-----------------------------+----------------------------------+
    | Field                       | Value                            |
    +-----------------------------+----------------------------------+
    | id                          | 4                                |
    | name                        | subcloud1                        |
    | description                 | None                             |
    | location                    | None                             |
    | software_version            | 24.09                            |
    | management                  | managed                          |
    | availability                | offline                          |
    | deploy_status               | complete                         |
    | management_subnet           | fdff:10:80:221::/64              |
    | management_start_ip         | fdff:10:80:221::2                |
    | management_end_ip           | fdff:10:80:221::ffff             |

    some more configuration properties ...

    | region_name                 | 11a60317384d4eef89c629449d4c2de2 |
    +-----------------------------+----------------------------------+

    """

    def __init__(self, id: str):
        """Constructor for the DcManagerSubcloudShowObject class.

        Args:
            id (str): The unique identifier for the subcloud.
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
        self.group_id: int = -1
        self.peer_group_id: str
        self.created_at: str
        self.updated_at: str
        self.backup_status: str
        self.backup_datetime: str
        self.prestage_status: str
        self.prestage_versions: str
        self.dc_cert_sync_status: str
        self.firmware_sync_status: str
        self.identity_sync_status: str
        self.kubernetes_sync_status: str
        self.kube_rootca_sync_status: str
        self.load_sync_status: str
        self.patching_sync_status: str
        self.platform_sync_status: str
        self.usm_sync_status: str
        self.region_name: str

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

    def get_dc_cert_sync_status(self) -> str:
        """
        Getter for the DC Cert Sync Status
        """
        return self.dc_cert_sync_status

    def set_dc_cert_sync_status(self, dc_cert_sync_status: str):
        """
        Setter for the DC Cert Sync Status
        """
        self.dc_cert_sync_status = dc_cert_sync_status

    def get_firmware_sync_status(self) -> str:
        """
        Getter for the Firmware Sync Status
        """
        return self.firmware_sync_status

    def set_firmware_sync_status(self, firmware_sync_status: str):
        """
        Setter for the Firmware Sync Status
        """
        self.firmware_sync_status = firmware_sync_status

    def get_identity_sync_status(self) -> str:
        """
        Getter for the Identity Sync Status
        """
        return self.identity_sync_status

    def set_identity_sync_status(self, identity_sync_status: str):
        """
        Setter for the Identity Sync Status
        """
        self.identity_sync_status = identity_sync_status

    def get_kubernetes_sync_status(self) -> str:
        """
        Getter for the Kubernetes Sync Status
        """
        return self.kubernetes_sync_status

    def set_kubernetes_sync_status(self, kubernetes_sync_status: str):
        """
        Setter for the Kubernetes Sync Status
        """
        self.kubernetes_sync_status = kubernetes_sync_status

    def get_kube_rootca_sync_status(self) -> str:
        """
        Getter for the Kube Root CA Sync Status
        """
        return self.kube_rootca_sync_status

    def set_kube_rootca_sync_status(self, kube_rootca_sync_status: str):
        """
        Setter for the Kube Root CA Sync Status
        """
        self.kube_rootca_sync_status = kube_rootca_sync_status

    def get_load_sync_status(self) -> str:
        """
        Getter for the Load Sync Status
        """
        return self.load_sync_status

    def set_load_sync_status(self, load_sync_status: str):
        """
        Setter for the Load Sync Status
        """
        self.load_sync_status = load_sync_status

    def get_patching_sync_status(self) -> str:
        """
        Getter for the Patching Sync Status
        """
        return self.patching_sync_status

    def set_patching_sync_status(self, patching_sync_status: str):
        """
        Setter for the Patching Sync Status
        """
        self.patching_sync_status = patching_sync_status

    def get_platform_sync_status(self) -> str:
        """
        Getter for the Platform Sync Status
        """
        return self.platform_sync_status

    def set_platform_sync_status(self, platform_sync_status: str):
        """
        Setter for the Platform Sync Status
        """
        self.platform_sync_status = platform_sync_status

    def get_usm_sync_status(self) -> str:
        """
        Getter for the USM Sync Status
        """
        return self.usm_sync_status

    def set_usm_sync_status(self, usm_sync_status: str):
        """
        Setter for the USM Sync Status
        """
        self.usm_sync_status = usm_sync_status

    def get_software_sync_status(self) -> str:
        """
        Getter for the software Sync Status
        """
        return self.software_sync_status

    def set_software_sync_status(self, software_sync_status: str):
        """
        Setter for the software Sync Status
        """
        self.software_sync_status = software_sync_status

    def get_region_name(self) -> str:
        """
        Getter for the Region Name
        """
        return self.region_name

    def set_region_name(self, region_name: str):
        """
        Setter for the Region Name
        """
        self.region_name = region_name
