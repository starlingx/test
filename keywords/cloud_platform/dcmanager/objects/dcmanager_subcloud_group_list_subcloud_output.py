from typing import Dict, List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import (
    DcManagerTableParser,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_group_object import (
    DcmanagerSubcloudGroupObject,
)


class DcmanagerSubcloudGroupListSubcloudOutput:
    """
    Parses the output of the 'dcmanager subcloud-group list-subclouds' command into a list of DcmanagerSubcloudGroupObject instances.
    """

    def __init__(self, dcmanager_output: str) -> None:
        """
        Initializes DcmanagerSubcloudGroupOutput.

        Args:
            dcmanager_output (str): Output of the 'dcmanager subcloud-group list-subclouds' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        self.dcmanager_subcloud_group: List[DcmanagerSubcloudGroupObject] = []
        dc_table_parser = DcManagerTableParser(dcmanager_output)
        output_values = dc_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                dcmanager_subcloud_group = DcmanagerSubcloudGroupObject()
                dcmanager_subcloud_group.set_id(value["id"])
                dcmanager_subcloud_group.set_name(value["name"])
                dcmanager_subcloud_group.set_description(value["description"])
                dcmanager_subcloud_group.set_location(value["location"])
                dcmanager_subcloud_group.set_software_version(value["software_version"])
                dcmanager_subcloud_group.set_management(value["management"])
                dcmanager_subcloud_group.set_availability(value["availability"])
                dcmanager_subcloud_group.set_deploy_status(value["deploy_status"])
                dcmanager_subcloud_group.set_management_subnet(value["management_subnet"])
                dcmanager_subcloud_group.set_management_start_ip(value["management_start_ip"])
                dcmanager_subcloud_group.set_management_end_ip(value["management_end_ip"])
                dcmanager_subcloud_group.set_management_gateway_ip(value["management_gateway_ip"])
                dcmanager_subcloud_group.set_systemcontroller_gateway_ip(value["systemcontroller_gateway_ip"])
                dcmanager_subcloud_group.set_group_id(value["group_id"])
                dcmanager_subcloud_group.set_peer_group_id(value["peer_group_id"])
                dcmanager_subcloud_group.set_created_at(value["created_at"])
                dcmanager_subcloud_group.set_updated_at(value["updated_at"])
                dcmanager_subcloud_group.set_backup_status(value["backup_status"])
                dcmanager_subcloud_group.set_backup_datetime(value["backup_datetime"])
                dcmanager_subcloud_group.set_prestage_status(value["prestage_status"])
                dcmanager_subcloud_group.set_prestage_versions(value["prestage_versions"])
                self.dcmanager_subcloud_group.append(dcmanager_subcloud_group)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_dcmanager_subcloud_group_list_subclouds(self) -> List[DcmanagerSubcloudGroupObject]:
        """
        Retrieves the parsed dcmanager subcloud-group list-subclouds.

        Returns:
            List[DcmanagerSubcloudGroupObject]: A list of parsed DcmanagerSubcloudGroupObject instances.
        """
        return self.dcmanager_subcloud_group

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output dictionary contains all required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.
        """
        required_fields = ["id", "name", "description", "location", "software_version", "management", "availability", "deploy_status", "management_subnet", "management_start_ip", "management_end_ip", "management_gateway_ip", "systemcontroller_gateway_ip", "group_id", "peer_group_id", "created_at", "updated_at", "backup_status", "backup_datetime", "prestage_status", "prestage_versions"]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
