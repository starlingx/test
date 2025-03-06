from typing import Dict, List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import (
    DcManagerTableParser,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_patch_strategy_config_object import (
    DcmanagerPatchStrategyConfigObject,
)


class DcmanagerPatchStrategyConfigOutput:
    """
    Parses the output of the 'dcmanager patch-strategy-config list' command into a list of DcmanagerPatchStrategyConfigObject instances.
    """

    def __init__(self, dcmanager_patch: str) -> None:
        """
        Initializes DcmanagerPatchStrategyConfigOutput.

        Args:
            dcmanager_patch (str): Output of the 'dcmanager patch-strategy-config list' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        self.dcmanager_patch_strategy_config: List[DcmanagerPatchStrategyConfigObject] = []
        dc_table_parser = DcManagerTableParser(dcmanager_patch)
        output_values = dc_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                dcmanager_patch_strategy_config = DcmanagerPatchStrategyConfigObject()
                dcmanager_patch_strategy_config.set_cloud(value["cloud"])
                dcmanager_patch_strategy_config.set_storage_apply_type(value["storage apply type"])
                dcmanager_patch_strategy_config.set_worker_apply_type(value["worker apply type"])
                dcmanager_patch_strategy_config.set_max_parallel_workers(value["max parallel workers"])
                dcmanager_patch_strategy_config.set_alarm_restriction_type(value["alarm restriction type"])
                dcmanager_patch_strategy_config.set_default_instance_action(value["default instance action"])
                self.dcmanager_patch_strategy_config.append(dcmanager_patch_strategy_config)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_dcmanager_patch_strategy_config_list(self) -> List[DcmanagerPatchStrategyConfigObject]:
        """
        Retrieves the parsed dcmanager patch-strategy-config list.

        Returns:
            List[DcmanagerPatchStrategyConfigObject]: A list of parsed DcmanagerPatchStrategyConfigObject instances.
        """
        return self.dcmanager_patch_strategy_config

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output dictionary contains all required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.
        """
        required_fields = ["cloud", "storage apply type", "worker apply type", "max parallel workers", "alarm restriction type", "default instance action"]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
