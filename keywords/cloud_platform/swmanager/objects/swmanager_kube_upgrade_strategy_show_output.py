from typing import Dict

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.swmanager.objects.swmanager_kube_upgrade_strategy_object import SwManagerKubeUpgradeStrategyObject
from keywords.cloud_platform.swmanager.swmanager_vertical_table_parser import SwManagerVerticalTableParser


class SwManagerKubeUpgradeStrategyShowOutput:
    """
    Parses the output of the 'sw-manager kube-upgrade-strategy show' command into a SwManagerKubeUpgradeStrategyObject instance.
    """

    def __init__(self, swmanager_kube_upgrade: list) -> None:
        """
        Initializes class SwManagerKubeUpgradeStrategyObject.

        Args:
            swmanager_kube_upgrade (list): Output of the 'sw-manager kube-upgrade-strategy show' command.

        Raises:
            ValidationException: If the output format is invalid.
        """
        swmanager_vertical_table_parser = SwManagerVerticalTableParser(swmanager_kube_upgrade)
        output_values = swmanager_vertical_table_parser.get_output_values_dict()

        validate_equals(self.is_valid_output(output_values), True, f"The output line {output_values} was not valid")

        self.swmanager_kube_upgrade_strategy = SwManagerKubeUpgradeStrategyObject()
        kube_upgrade_strat = output_values["Strategy Kubernetes Upgrade Strategy"]
        self.swmanager_kube_upgrade_strategy.set_strategy_uuid(kube_upgrade_strat.get("strategy-uuid"))
        self.swmanager_kube_upgrade_strategy.set_controller_apply_type(kube_upgrade_strat.get("controller-apply-type"))
        self.swmanager_kube_upgrade_strategy.set_storage_apply_type(kube_upgrade_strat.get("storage-apply-type"))
        self.swmanager_kube_upgrade_strategy.set_worker_apply_type(kube_upgrade_strat.get("worker-apply-type"))
        self.swmanager_kube_upgrade_strategy.set_default_instance_action(kube_upgrade_strat.get("default-instance-action"))
        self.swmanager_kube_upgrade_strategy.set_alarm_restrictions(kube_upgrade_strat.get("alarm-restrictions"))
        self.swmanager_kube_upgrade_strategy.set_current_phase(kube_upgrade_strat.get("current-phase"))
        self.swmanager_kube_upgrade_strategy.set_current_stage(kube_upgrade_strat.get("current-stage"))
        self.swmanager_kube_upgrade_strategy.set_current_step(kube_upgrade_strat.get("current-step"))
        self.swmanager_kube_upgrade_strategy.set_current_phase_completion(kube_upgrade_strat.get("current-phase-completion"))
        self.swmanager_kube_upgrade_strategy.set_state(kube_upgrade_strat.get("state"))
        self.swmanager_kube_upgrade_strategy.set_inprogress(kube_upgrade_strat.get("inprogress"))

    def get_swmanager_kube_upgrade_strategy_show(self) -> SwManagerKubeUpgradeStrategyObject:
        """
        Retrieves the parsed sw-manager kube-upgrade-strategy show object.

        Returns:
            SwManagerKubeUpgradeStrategyObject: The parsed sw-manager kube-upgrade-strategy show object.
        """
        return self.swmanager_kube_upgrade_strategy

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["strategy-uuid", "controller-apply-type", "storage-apply-type", "worker-apply-type", "default-instance-action", "alarm-restrictions", "current-phase", "current-phase-completion", "state"]
        if "Strategy Kubernetes Upgrade Strategy" not in value:
            get_logger().log_error("Strategy Kubernetes Upgrade Strategy is not in the output value")
            return False
        for field in required_fields:
            if field not in value["Strategy Kubernetes Upgrade Strategy"]:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
