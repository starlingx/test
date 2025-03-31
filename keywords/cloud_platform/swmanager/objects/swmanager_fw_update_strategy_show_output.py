from typing import Dict

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.swmanager.objects.swmanager_fw_update_strategy_object import SwmanagerFwUpdateStrategyObject
from keywords.cloud_platform.swmanager.swmanager_vertical_table_parser import SwManagerVerticalTableParser


class SwmanagerFwUpdateStrategyShowOutput:
    """
    Parses the output of the 'sw-manager fw-update-strategy show' command into a SwmanagerFwUpdateStrategyObject instance.
    """

    def __init__(self, swmanager_fw_update: str) -> None:
        """
        Initializes SwmanagerFwUpdateStrategyObject.

        Args:
            swmanager_fw_update (str): Output of the 'sw-manager fw-update-strategy show' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        swmanager_vertical_table_parser = SwManagerVerticalTableParser(swmanager_fw_update)
        output_values = swmanager_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.swmanager_fw_update_strategy = SwmanagerFwUpdateStrategyObject()
            strat_fw_update = output_values["Strategy Firmware Update Strategy"]
            self.swmanager_fw_update_strategy.set_strategy_uuid(strat_fw_update["strategy-uuid"])
            self.swmanager_fw_update_strategy.set_controller_apply_type(strat_fw_update["controller-apply-type"])
            self.swmanager_fw_update_strategy.set_storage_apply_type(strat_fw_update["storage-apply-type"])
            self.swmanager_fw_update_strategy.set_worker_apply_type(strat_fw_update["worker-apply-type"])
            self.swmanager_fw_update_strategy.set_default_instance_action(strat_fw_update["default-instance-action"])
            self.swmanager_fw_update_strategy.set_alarm_restrictions(strat_fw_update["alarm-restrictions"])
            self.swmanager_fw_update_strategy.set_current_phase(strat_fw_update["current-phase"])
            self.swmanager_fw_update_strategy.set_current_stage(strat_fw_update["current-stage"])
            self.swmanager_fw_update_strategy.set_current_step(strat_fw_update["current-step"])
            self.swmanager_fw_update_strategy.set_current_phase_completion(strat_fw_update["current-phase-completion"])
            self.swmanager_fw_update_strategy.set_state(strat_fw_update["state"])
            self.swmanager_fw_update_strategy.set_build_result(strat_fw_update["build-result"])
            self.swmanager_fw_update_strategy.set_build_reason(strat_fw_update["build-reason"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_swmanager_fw_update_strategy_show(self) -> SwmanagerFwUpdateStrategyObject:
        """
        Retrieves the parsed sw-manager fw-update-strategy show object.

        Returns:
            SwmanagerFwUpdateStrategyObject: The parsed sw-manager fw-update-strategy show object.
        """
        return self.swmanager_fw_update_strategy

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["strategy-uuid", "controller-apply-type", "storage-apply-type", "worker-apply-type", "default-instance-action", "alarm-restrictions", "current-phase", "current-stage", "current-step", "current-phase-completion", "state", "build-result", "build-reason"]
        if "Strategy Firmware Update Strategy" not in value:
            get_logger().log_error("Strategy Firmware Update Strategy is not in the output value")
            return False
        for field in required_fields:
            if field not in value["Strategy Firmware Update Strategy"]:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
