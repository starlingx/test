import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_prestage_strategy_object import DcmanagerPrestageStrategyObject
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_object import SwManagerSwDeployStrategyObject
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_show_output import SwManagerSwDeployStrategyShowOutput


class SwManagerSwDeployStrategyKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'sw-manager sw-deploy-strategy' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initializes SwManagerSwDeployStrategyKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_sw_deploy_strategy_abort(self):
        """Gets the sw-deploy-strategy abort."""
        command = source_openrc("sw-manager sw-deploy-strategy abort")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def get_sw_deploy_strategy_apply(self) -> DcmanagerPrestageStrategyObject:
        """Gets the sw-deploy-strategy apply.

        Returns:
            DcmanagerPrestageStrategyObject: An object containing details of the sw-deploy strategy.
        """
        command = source_openrc("sw-manager sw-deploy-strategy apply")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        # wait for apply to complete
        return self.wait_for_state(["applied", "apply-failed"])

    def get_sw_deploy_strategy_create(self, release: str, delete: bool) -> DcmanagerPrestageStrategyObject:
        """Gets the sw-deploy-strategy create.

        Args:
            release (str): The release to be deployed.
            delete (bool): If True, include the --delete argument in the command.

        Returns:
            DcmanagerPrestageStrategyObject: The output of the sw-deploy strategy.
        """
        delete_arg = "--delete" if delete else ""

        command = source_openrc(f"sw-manager sw-deploy-strategy create {delete_arg} {release}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        # wait for build to complete
        return self.wait_for_state(["ready-to-apply", "build-failed"])

    def get_sw_deploy_strategy_show(self) -> SwManagerSwDeployStrategyShowOutput:
        """Gets the sw-deploy-strategy show.

        Returns:
            SwManagerSwDeployStrategyShowOutput: An object containing details of the prestage strategy .
        """
        command = source_openrc("sw-manager sw-deploy-strategy show")
        output = self.ssh_connection.send(command)
        return SwManagerSwDeployStrategyShowOutput(output)

    def check_sw_deploy_strategy_delete(self) -> bool:
        """Checks the output of the sw-deploy-strategy delete command.

        Returns:
            bool: True if no strategy exists to be deleted, False if a strategy is in the process of being deleted.
        """
        command = source_openrc("sw-manager sw-deploy-strategy delete")
        output = self.ssh_connection.send(command)
        if "Nothing to delete" in "".join(output):
            get_logger().log_info("No sw-deploy-strategy to be deleted, moving on...")
            return True
        return False

    def get_sw_deploy_strategy_delete(self) -> None:
        """Starts sw-deploy-strategy deletion process if there is a strategy in progress and waits for its deletion."""
        validate_equals_with_retry(function_to_execute=self.check_sw_deploy_strategy_delete, expected_value=True, validation_description="Waits for strategy deletion", timeout=600, polling_sleep_time=10)

    def wait_for_state(self, state: list, timeout: int = 1800) -> SwManagerSwDeployStrategyObject:
        """Waits for the sw-deploy-strategy to reach a specific state.

        Args:
            state (list): The desired state to wait for.
            timeout (int): The maximum time to wait in seconds.

        Returns:
            SwManagerSwDeployStrategyObject: The output of the sw-deploy-strategy show command when the desired state is reached.
        """
        interval = 10
        start_time = time.time()
        while time.time() - start_time < timeout:
            output = self.get_sw_deploy_strategy_show().get_swmanager_sw_deploy_strategy_show()
            if output.get_state() in state:
                return output
            time.sleep(interval)
        raise TimeoutError(f"Timed out waiting for sw-deploy-strategy to reach state '{state}' after {timeout} seconds.")
