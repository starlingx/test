from typing import Dict

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_kube_rootca_update_strategy_show_object import DcmanagerKubeRootcaUpdateStrategyShowObject


class DcmanagerKubeRootcaUpdateStrategyShowOutput:
    """
    Parses the output of the 'dcmanager kube-rootca-update-strategy' command into a DcmanagerKubeRootcaUpdateStrategyShowObject instance.
    """

    def __init__(self, kube_strategy: str) -> None:
        """
        Initializes DcmanagerKubeRootcaUpdateStrategyShowObject.

        Args:
            kube_strategy (str): Output of the 'kube-rootca-update-strategy' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        dc_vertical_table_parser = DcManagerVerticalTableParser(kube_strategy)
        output_values = dc_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.dcmanager_kube_rootca_update_strategy_step = DcmanagerKubeRootcaUpdateStrategyShowObject()
            self.dcmanager_kube_rootca_update_strategy_step.set_strategy_type(output_values["strategy type"])
            self.dcmanager_kube_rootca_update_strategy_step.set_subcloud_apply_type(output_values["subcloud apply type"])
            self.dcmanager_kube_rootca_update_strategy_step.set_max_parallel_subclouds(int(output_values["max parallel subclouds"]))
            self.dcmanager_kube_rootca_update_strategy_step.set_state(output_values["state"])
            self.dcmanager_kube_rootca_update_strategy_step.set_stop_on_failure(output_values["stop on failure"])
            self.dcmanager_kube_rootca_update_strategy_step.set_created_at(output_values["created_at"])
            self.dcmanager_kube_rootca_update_strategy_step.set_updated_at(output_values["updated_at"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_dcmanager_kube_rootca_update_strategy_step_show(self) -> DcmanagerKubeRootcaUpdateStrategyShowObject:
        """
        Retrieves the parsed dcmanager kube-rootca-update-strategy show object.

        Returns:
            DcmanagerKubeRootcaUpdateStrategyShowObject: The parsed dcmanager kube-rootca-update-strategy show object.
        """
        return self.dcmanager_kube_rootca_update_strategy_step

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
