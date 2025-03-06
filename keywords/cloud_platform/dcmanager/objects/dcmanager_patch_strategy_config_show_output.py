from typing import Dict

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import (
    DcManagerVerticalTableParser,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_patch_strategy_config_object import (
    DcmanagerPatchStrategyConfigObject,
)


class DcmanagerPatchStrategyConfigShowOutput:
    """
    Parses the output of the 'dcmanager patch-strategy-config show' command into a DcmanagerPatchStrategyConfigObject instance.
    """

    def __init__(self, dcmanager_patch: str) -> None:
        """
        Initializes DcmanagerPatchStrategyConfigObject.

        Args:
            dcmanager_patch (str): Output of the 'dcmanager patch-strategy-config show' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        dc_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_patch)
        output_values = dc_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.dcmanager_patch_strategy_config = DcmanagerPatchStrategyConfigObject()
            self.dcmanager_patch_strategy_config.set_cloud(output_values["cloud"])
            self.dcmanager_patch_strategy_config.set_storage_apply_type(output_values["storage apply type"])
            self.dcmanager_patch_strategy_config.set_worker_apply_type(output_values["worker apply type"])
            self.dcmanager_patch_strategy_config.set_max_parallel_workers(output_values["max parallel workers"])
            self.dcmanager_patch_strategy_config.set_alarm_restriction_type(output_values["alarm restriction type"])
            self.dcmanager_patch_strategy_config.set_default_instance_action(output_values["default instance action"])
            self.dcmanager_patch_strategy_config.set_created_at(output_values["created_at"])
            self.dcmanager_patch_strategy_config.set_updated_at(output_values["updated_at"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_dcmanager_patch_strategy_config_show(self) -> DcmanagerPatchStrategyConfigObject:
        """
        Retrieves the parsed dcmanager patch-strategy-config show object.

        Returns:
            DcmanagerPatchStrategyConfigObject: The parsed dcmanager patch-strategy-config show object.
        """
        return self.dcmanager_patch_strategy_config

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["cloud", "storage apply type", "worker apply type", "max parallel workers", "alarm restriction type", "default instance action", "created_at", "updated_at"]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
