from typing import Dict

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_kube_strategy_step_show_object import DcmanagerKubeStrategyStepObject


class DcmanagerKubeStrategyStepShowOutput:
    """
    Parses the output of the 'dcmanager kube-strategy-step show' command into a DcmanagerKubeStrategyStepObject instance.
    """

    def __init__(self, kube_strategy: str) -> None:
        """
        Initializes DcmanagerKubeStrategyStepShowOutput.

        Args:
            kube_strategy (str): Output of the 'dcmanager strategy-step show' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        dc_vertical_table_parser = DcManagerVerticalTableParser(kube_strategy)
        output_values = dc_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.dcmanager_kube_strategy_step = DcmanagerKubeStrategyStepObject()
            self.dcmanager_kube_strategy_step.set_state(output_values["state"])

        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_dcmanager_kube_strategy_step_show(self) -> DcmanagerKubeStrategyStepObject:
        """
        Retrieves the parsed dcmanager strategy-step show object.

        Returns:
            DcmanagerKubeStrategyStepObject: The parsed dcmanager kube-strategy-step show object.
        """
        return self.dcmanager_kube_strategy_step

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["strategy type", "subcloud apply type", "max parallel subclouds", "stop on failure", "state", "created_at", "updated_at"]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
