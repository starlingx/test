from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import DcManagerTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_peer_group_list_subclouds_object import DcManagerSubcloudPeerGroupListSubcloudsObject


class DcManagerSubcloudPeerGroupListSubcloudsOutput:
    """Output parser for 'dcmanager subcloud-peer-group list-subclouds' command."""

    def __init__(self, dcmanager_output: str):
        """Initialize output parser.

        Args:
            dcmanager_output (str): Raw command output to parse.
        """
        self.dcmanager_output = dcmanager_output
        self.subclouds: list[DcManagerSubcloudPeerGroupListSubcloudsObject] = []
        self._parse_output()

    def _parse_output(self):
        """Parse dcmanager output and populate subcloud objects."""
        parser = DcManagerTableParser(self.dcmanager_output)
        output_values_list = parser.get_output_values_list()

        for output_values in output_values_list:

            if not self.is_valid_output(output_values):
                raise KeywordException(f"The output line {output_values} was not valid")

            subcloud = DcManagerSubcloudPeerGroupListSubcloudsObject(output_values.get("id", ""))
            subcloud.set_name(output_values.get("name", ""))
            subcloud.set_description(output_values.get("description", ""))
            subcloud.set_location(output_values.get("location", ""))
            subcloud.set_software_version(output_values.get("software_version", ""))
            subcloud.set_management(output_values.get("management", ""))
            subcloud.set_availability(output_values.get("availability", ""))
            subcloud.set_deploy_status(output_values.get("deploy_status", ""))
            subcloud.set_management_subnet(output_values.get("management_subnet", ""))
            subcloud.set_management_start_ip(output_values.get("management_start_ip", ""))
            subcloud.set_management_end_ip(output_values.get("management_end_ip", ""))
            subcloud.set_management_gateway_ip(output_values.get("management_gateway_ip", ""))
            subcloud.set_systemcontroller_gateway_ip(output_values.get("systemcontroller_gateway_ip", ""))
            subcloud.set_group_id(output_values.get("group_id", ""))
            subcloud.set_peer_group_id(output_values.get("peer_group_id", ""))
            subcloud.set_created_at(output_values.get("created_at", ""))
            subcloud.set_updated_at(output_values.get("updated_at", ""))
            subcloud.set_backup_status(output_values.get("backup_status", ""))
            subcloud.set_backup_datetime(output_values.get("backup_datetime", ""))
            subcloud.set_prestage_status(output_values.get("prestage_status", ""))
            subcloud.set_prestage_versions(output_values.get("prestage_versions", ""))
            self.subclouds.append(subcloud)

    def get_subclouds(self) -> list[DcManagerSubcloudPeerGroupListSubcloudsObject]:
        """Get list of subcloud objects.

        Returns:
            list[DcManagerSubcloudPeerGroupListSubcloudsObject]: List of subcloud objects.
        """
        return self.subclouds

    def get_subcloud_by_name(self, name: str) -> DcManagerSubcloudPeerGroupListSubcloudsObject:
        """Get subcloud by name.

        Args:
            name (str): Subcloud name to search for.

        Returns:
            DcManagerSubcloudPeerGroupListSubcloudsObject: Subcloud object or None if not found.
        """
        for subcloud in self.subclouds:
            if subcloud.get_name() == name:
                return subcloud
        return None

    def get_subcloud_by_id(self, id: str) -> DcManagerSubcloudPeerGroupListSubcloudsObject:
        """Get subcloud by ID.

        Args:
            id (str): Subcloud ID to search for.

        Returns:
            DcManagerSubcloudPeerGroupListSubcloudsObject: Subcloud object or None if not found.
        """
        for subcloud in self.subclouds:
            if subcloud.get_id() == id:
                return subcloud
        return None

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """Check if output contains all required fields.

        Args:
            value (dict): Dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["id", "name", "description", "location", "software_version", "management", "availability", "deploy_status", "management_subnet", "management_start_ip", "management_end_ip", "management_gateway_ip", "systemcontroller_gateway_ip", "group_id", "peer_group_id", "created_at", "updated_at", "backup_status", "backup_datetime", "prestage_status", "prestage_versions"]
        return all(field in value for field in required_fields)

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            str: String representation of the object.
        """
        return f"{self.__class__.__name__}(SubcloudCount={len(self.subclouds)})"
