from typing import Dict

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_object import SwManagerSwDeployStrategyObject
from keywords.cloud_platform.swmanager.swmanager_vertical_table_parser import SwManagerVerticalTableParser


class SwManagerSwDeployStrategyShowOutput:
    """
    Parses the output of the 'sw-manager sw-deploy-strategy show' command into a SwManagerSwDeployStrategyObject instance.
    """

    def __init__(self, swmanager_sw_deploy: str) -> None:
        """
        Initializes SwManagerSwDeployStrategyObject.

        Args:
            swmanager_sw_deploy (str): Output of the 'sw-manager sw-deploy-strategy show' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        swmanager_vertical_table_parser = SwManagerVerticalTableParser(swmanager_sw_deploy)
        output_values = swmanager_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.swmanager_sw_deploy_strategy = SwManagerSwDeployStrategyObject()
            sw_deploy_strat = output_values["Strategy Software Deploy Strategy"]
            self.swmanager_sw_deploy_strategy.set_strategy_uuid(sw_deploy_strat["strategy-uuid"])
            self.swmanager_sw_deploy_strategy.set_release_id(sw_deploy_strat["release-id"])
            self.swmanager_sw_deploy_strategy.set_controller_apply_type(sw_deploy_strat["controller-apply-type"])
            self.swmanager_sw_deploy_strategy.set_storage_apply_type(sw_deploy_strat["storage-apply-type"])
            self.swmanager_sw_deploy_strategy.set_worker_apply_type(sw_deploy_strat["worker-apply-type"])
            self.swmanager_sw_deploy_strategy.set_default_instance_action(sw_deploy_strat["default-instance-action"])
            self.swmanager_sw_deploy_strategy.set_alarm_restrictions(sw_deploy_strat["alarm-restrictions"])
            self.swmanager_sw_deploy_strategy.set_current_phase(sw_deploy_strat["current-phase"])
            self.swmanager_sw_deploy_strategy.set_current_stage(sw_deploy_strat["current-stage"])
            self.swmanager_sw_deploy_strategy.set_current_step(sw_deploy_strat["current-step"])
            self.swmanager_sw_deploy_strategy.set_current_phase_completion(sw_deploy_strat["current-phase-completion"])
            self.swmanager_sw_deploy_strategy.set_state(sw_deploy_strat["state"])
            self.swmanager_sw_deploy_strategy.set_inprogress(sw_deploy_strat["inprogress"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_swmanager_sw_deploy_strategy_show(self) -> SwManagerSwDeployStrategyObject:
        """
        Retrieves the parsed sw-manager  sw-deploy-strategy show object.

        Returns:
            SwManagerSwDeployStrategyObject: The parsed sw-manager  sw-deploy-strategy show object.
        """
        return self.swmanager_sw_deploy_strategy

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["strategy-uuid", "release-id", "controller-apply-type", "storage-apply-type", "worker-apply-type", "default-instance-action", "alarm-restrictions", "current-phase", "current-stage", "current-step", "current-phase-completion", "state", "inprogress"]
        if "Strategy Software Deploy Strategy" not in value:
            get_logger().log_error("Strategy Software Deploy Strategy is not in the output value")
            return False
        for field in required_fields:
            if field not in value["Strategy Software Deploy Strategy"]:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
