from typing import Dict, List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import DcManagerTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_strategy_step_object import DcmanagerStrategyStepObject


class DcmanagerStrategyStepOutput:
    """
    Parses the output of the 'dcmanager strategy-step list' command into a list of DcmanagerStrategyStepObject instances.
    """

    def __init__(self, dcmanager_strategy: str) -> None:
        """
        Initializes DcmanagerStrategyStepOutput.

        Args:
            dcmanager_strategy (str): Output of the 'dcmanager strategy-step list' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        self.dcmanager_strategy_step: List[DcmanagerStrategyStepObject] = []
        dc_table_parser = DcManagerTableParser(dcmanager_strategy)
        output_values = dc_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                dcmanager_strategy_step = DcmanagerStrategyStepObject()
                dcmanager_strategy_step.set_cloud(value["cloud"])
                dcmanager_strategy_step.set_stage(value["stage"])
                dcmanager_strategy_step.set_state(value["state"])
                dcmanager_strategy_step.set_details(value["details"])
                dcmanager_strategy_step.set_started_at(value["started_at"])
                dcmanager_strategy_step.set_finished_at(value["finished_at"])
                self.dcmanager_strategy_step.append(dcmanager_strategy_step)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_dcmanager_strategy_step_list(self) -> List[DcmanagerStrategyStepObject]:
        """
        Retrieves the parsed dcmanager strategy-step list.

        Returns:
            List[DcmanagerStrategyStepObject]: A list of parsed DcmanagerStrategyStepObject instances.
        """
        return self.dcmanager_strategy_step

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output dictionary contains all required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.
        """
        required_fields = ["cloud", "stage", "state", "details", "started_at", "finished_at"]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
