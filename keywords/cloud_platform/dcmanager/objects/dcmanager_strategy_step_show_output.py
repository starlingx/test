from typing import Dict

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_strategy_step_object import DcmanagerStrategyStepObject


class DcmanagerStrategyStepShowOutput:
    """
    Parses the output of the 'dcmanager strategy-step show' command into a DcmanagerStrategyStepObject instance.
    """

    def __init__(self, dcmanager_strategy: str) -> None:
        """
        Initializes DcmanagerStrategyStepObject.

        Args:
            dcmanager_strategy (str): Output of the 'dcmanager strategy-step show' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        dc_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_strategy)
        output_values = dc_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.dcmanager_strategy_step = DcmanagerStrategyStepObject()
            self.dcmanager_strategy_step.set_cloud(output_values["cloud"])
            self.dcmanager_strategy_step.set_stage(output_values["stage"])
            self.dcmanager_strategy_step.set_state(output_values["state"])
            self.dcmanager_strategy_step.set_details(output_values["details"])
            self.dcmanager_strategy_step.set_started_at(output_values["started_at"])
            self.dcmanager_strategy_step.set_finished_at(output_values["finished_at"])
            self.dcmanager_strategy_step.set_created_at(output_values["created_at"])
            self.dcmanager_strategy_step.set_updated_at(output_values["updated_at"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_dcmanager_strategy_step_show(self) -> DcmanagerStrategyStepObject:
        """
        Retrieves the parsed dcmanager strategy-step show object.

        Returns:
            DcmanagerStrategyStepObject: The parsed dcmanager strategy-step show object.
        """
        return self.dcmanager_strategy_step

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["cloud", "stage", "state", "details", "started_at", "finished_at", "created_at", "updated_at"]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
