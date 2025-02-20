from typing import Dict, List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import (
    DcManagerTableParser,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_group_object import (
    DcmanagerSubcloudGroupObject,
)


class DcmanagerSubcloudGroupOutput:
    """
    Parses the output of the 'dcmanager subcloud-group list' command into a list of DcmanagerSubcloudGroupObject instances.
    """

    def __init__(self, dcmanager_output: str) -> None:
        """
        Initializes DcmanagerSubcloudGroupOutput.

        Args:
            dcmanager_output (str): Output of the 'dcmanager subcloud-group list' command.

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
                self.dcmanager_subcloud_group.append(dcmanager_subcloud_group)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_dcmanager_subcloud_group_list(self) -> List[DcmanagerSubcloudGroupObject]:
        """
        Retrieves the parsed dcmanager subcloud-group list.

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
        required_fields = ["id", "name", "description"]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
