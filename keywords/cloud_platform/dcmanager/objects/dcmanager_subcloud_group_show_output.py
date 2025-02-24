from typing import Dict

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import (
    DcManagerVerticalTableParser,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_group_object import (
    DcmanagerSubcloudGroupObject,
)


class DcmanagerSubcloudGroupShowOutput:
    """
    Parses the output of the 'dcmanager subcloud-group show' command into a DcmanagerSubcloudGroupObject instance.
    """

    def __init__(self, dcmanager_output: str) -> None:
        """
        Initializes DcmanagerSubcloudGroupShowOutput.

        Args:
            dcmanager_output (str): Output of the 'dcmanager subcloud-group show' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        dc_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_output)
        output_values = dc_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.dcmanager_subcloud_group = DcmanagerSubcloudGroupObject()
            self.dcmanager_subcloud_group.set_id(output_values["id"])
            self.dcmanager_subcloud_group.set_name(output_values["name"])
            self.dcmanager_subcloud_group.set_description(output_values["description"])
            self.dcmanager_subcloud_group.set_update_apply_type(
                output_values["update apply type"]
            )
            self.dcmanager_subcloud_group.set_max_parallel_subclouds(
                output_values["max parallel subclouds"]
            )
            self.dcmanager_subcloud_group.set_created_at(output_values["created_at"])
            self.dcmanager_subcloud_group.set_updated_at(output_values["updated_at"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_dcmanager_subcloud_group_show(self) -> DcmanagerSubcloudGroupObject:
        """
        Retrieves the parsed dcmanager subcloud-group show object.

        Returns:
            DcmanagerSubcloudGroupObject: The parsed subcloud-group show object.
        """
        return self.dcmanager_subcloud_group

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = [
            "id",
            "name",
            "description",
            "update apply type",
            "max parallel subclouds",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
