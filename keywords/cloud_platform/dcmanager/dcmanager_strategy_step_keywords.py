import time

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_strategy_step_object import DcmanagerStrategyStepObject
from keywords.cloud_platform.dcmanager.objects.dcmanager_strategy_step_output import DcmanagerStrategyStepOutput
from keywords.cloud_platform.dcmanager.objects.dcmanager_strategy_step_show_output import DcmanagerStrategyStepShowOutput


class DcmanagerStrategyStepKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager strategy-step' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initializes DcmanagerStrategyStepKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_strategy_step_list(self) -> DcmanagerStrategyStepOutput:
        """
        Gets the dcmanager strategy-step list.

        Returns:
            DcmanagerStrategyStepOutput: An object containing the list of strategy steps.
        """
        command = source_openrc("dcmanager strategy-step list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerStrategyStepOutput(output)

    def get_dcmanager_strategy_step_show(self, subcloud_name: str) -> DcmanagerStrategyStepShowOutput:
        """
        Gets the dcmanager strategy-step show.

        Args:
            subcloud_name (str): The subcloud name.

        Returns:
            DcmanagerStrategyStepShowOutput: An object containing details of the strategy step.
        """
        command = source_openrc(f"dcmanager strategy-step show {subcloud_name}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerStrategyStepShowOutput(output)

    def wait_for_strategy_step_state(self, subcloud_name: str, states: list, timeout: int = 240, polling_sleep_time: int = 10) -> DcmanagerStrategyStepObject:
        """
        Waits for the dcmanager strategy-step of a subcloud to reach one of the given states.

        Unlike waiting for a single expected state, this accepts a list of acceptable
        end states (e.g. ["complete", "failed"]) so callers can wait for either a
        successful or a failed outcome without triggering a fail-fast exception.

        Args:
            subcloud_name (str): The subcloud name.
            states (list): Acceptable end states to wait for (e.g. ["complete", "failed"]).
            timeout (int): The maximum time (in seconds) to wait for one of the states.
            polling_sleep_time (int): The interval of time (in seconds) between polls.

        Returns:
            DcmanagerStrategyStepObject: The strategy step object once it reaches one of the given states.

        Raises:
            TimeoutError: If none of the given states is reached within the timeout.
        """
        end_time = time.time() + timeout
        while True:
            strategy_step = self.get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show()
            if strategy_step.get_state() in states:
                return strategy_step
            if time.time() >= end_time:
                raise TimeoutError(f"Timed out waiting for strategy-step of {subcloud_name} to reach one of {states}. Last state: {strategy_step.get_state()}")
            time.sleep(polling_sleep_time)
