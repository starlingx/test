from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords


class DcmanagerSwDeployStrategy(BaseKeyword):
    """
    This class executes sw-deploy-strategy commands
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_sw_deploy_strategy_create(self, subcloud_name: str, sw_version: str):
        """
        Runs dcmanager sw-deploy-strategy create command.

        Args:
            subcloud_name (str): The subcloud name.
            sw_version (str): The software version to be deployed.
        """
        command = source_openrc(f"dcmanager sw-deploy-strategy create {subcloud_name} {sw_version}")

        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        self.wait_sw_deployment(subcloud=subcloud_name, expected_status="initial")

    def dcmanager_sw_deploy_strategy_apply(self, subcloud_name: str):
        """
        Runs dcmanager sw-deploy-strategy apply command.

        Args:
            subcloud_name (str): The subcloud name.
        """
        command = source_openrc("dcmanager sw-deploy-strategy apply")

        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        self.wait_sw_deployment(subcloud=subcloud_name, expected_status="complete", timeout=600, check_interval=30)

    def check_sw_deploy_strategy_delete_output(self):
        """
        Verifies dcmanager sw-deploy-strategy delete output.
        """
        command = source_openrc("dcmanager sw-deploy-strategy delete")

        output = self.ssh_connection.send(command)
        if "Strategy with type sw-deploy doesn't exist." in "".join(output):
            get_logger().log_info("No strategy to be deleted, moving on...")
            return True
        elif "Strategy in state deleting cannot be deleted" in "".join(output):
            return False

    def dcmanager_sw_deploy_strategy_delete(self):
        """
        Starts sw-deploy-strategy deletion process if there is a strategy in progress and waits for its deletion.
        """
        validate_equals_with_retry(function_to_execute=self.check_sw_deploy_strategy_delete_output, expected_value=True, validation_description="Waits for strategy deletion", timeout=240, polling_sleep_time=10)

    def wait_sw_deployment(
        self,
        subcloud: str,
        expected_status: str,
        check_interval: int = 30,
        timeout: int = 240,
    ) -> None:
        """
        Waits for check_sw_deployment method to return True.
        """

        def check_sw_deployment() -> str:
            """
            Checks if the sw deployment operation has been completed, either 'create' or 'apply'.

            Returns:
                str: Expected status for sw deployment.
            """
            sw_deployment_status = DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_show(subcloud).get_dcmanager_strategy_step_show().get_state()
            return sw_deployment_status

        validate_equals_with_retry(
            function_to_execute=check_sw_deployment,
            expected_value=expected_status,
            validation_description=f"Waiting for sw_deployment_status {expected_status}.",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )
