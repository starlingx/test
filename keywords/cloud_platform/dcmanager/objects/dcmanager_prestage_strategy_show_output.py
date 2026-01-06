from typing import Dict

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_prestage_strategy_object import DcmanagerPrestageStrategyObject


class DcmanagerPrestageStrategyShowOutput:
    """DcmanagerPrestageStrategyShowOutput

    Parses the output of the 'dcmanager prestage-strategy create and
    show' command into a DcmanagerPrestageStrategyObject instance.
    """

    def __init__(self, dcmanager_prestage: str) -> None:
        """
        Initializes DcmanagerPrestageStrategyObject.

        Args:
            dcmanager_prestage (str): Output of the 'dcmanager prestage-strategy show' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        dc_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_prestage)
        output_values = dc_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.dcmanager_prestage_strategy = DcmanagerPrestageStrategyObject()
            self.dcmanager_prestage_strategy.set_strategy_type(output_values["strategy type"])
            self.dcmanager_prestage_strategy.set_subcloud_apply_type(output_values["subcloud apply type"])
            self.dcmanager_prestage_strategy.set_max_parallel_subclouds(output_values["max parallel subclouds"])
            self.dcmanager_prestage_strategy.set_stop_on_failure(output_values["stop on failure"])
            self.dcmanager_prestage_strategy.set_prestage_software_version(output_values["prestage software version"])
            self.dcmanager_prestage_strategy.set_state(output_values["state"])
            self.dcmanager_prestage_strategy.set_created_at(output_values["created_at"])
            self.dcmanager_prestage_strategy.set_updated_at(output_values["updated_at"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_dcmanager_prestage_strategy(self) -> DcmanagerPrestageStrategyObject:
        """
        Retrieves the parsed dcmanager prestage-strategy show object.

        Returns:
            DcmanagerPrestageStrategyObject: The parsed dcmanager prestage-strategy show object.
        """
        return self.dcmanager_prestage_strategy

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["strategy type", "subcloud apply type", "max parallel subclouds", "stop on failure", "prestage software version", "state", "created_at", "updated_at"]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
