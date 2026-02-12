from typing import Union

from keywords.cloud_platform.swmanager.objects.swmanager_kube_rootca_update_strategy_object import SwManagerKubeRootcaUpdateStrategyObject
from keywords.cloud_platform.swmanager.swmanager_vertical_table_parser import SwManagerVerticalTableParser


class SwManagerKubeRootcaUpdateStrategyShowOutput:
    """Parser for sw-manager kube-rootca-update-strategy show output."""

    def __init__(self, command_output: Union[str, list[str]]):
        """Initialize parser with command output.

        Args:
            command_output (Union[str, list[str]]): Raw command output.
        """
        self.raw_output = command_output
        self.strategy = self._parse_output(command_output)

    def _parse_output(self, output: Union[str, list[str]]) -> SwManagerKubeRootcaUpdateStrategyObject:
        """Parse command output into strategy object.

        Args:
            output (Union[str, list[str]]): Command output to parse.

        Returns:
            SwManagerKubeRootcaUpdateStrategyObject: Parsed strategy object.
        """
        parser = SwManagerVerticalTableParser(output)
        parsed_dict = parser.get_output_values_dict()

        # Extract nested dictionary under strategy name key
        output_dict = parsed_dict.get("Strategy Kubernetes RootCA Update Strategy", {})

        strategy = SwManagerKubeRootcaUpdateStrategyObject()
        strategy.set_state(output_dict.get("state", ""))
        strategy.set_current_phase(output_dict.get("current-phase", ""))
        strategy.set_current_phase_completion_percentage(output_dict.get("current-phase-completion-percentage", ""))
        return strategy

    def get_strategy(self) -> SwManagerKubeRootcaUpdateStrategyObject:
        """Get parsed strategy object.

        Returns:
            SwManagerKubeRootcaUpdateStrategyObject: Parsed strategy object.
        """
        return self.strategy
