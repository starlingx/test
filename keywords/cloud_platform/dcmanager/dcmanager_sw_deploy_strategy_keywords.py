from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from config.configuration_manager import ConfigurationManager
import time


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
        self.usm_config = ConfigurationManager.get_usm_config()

    def dcmanager_sw_deploy_strategy_create(self, subcloud_name: str = None, release: str = None, subcloud_group: str = None, with_delete: bool = False, delete_only: bool = False, rollback: bool = False, snapshot: bool = False):
        """
        Runs dcmanager sw-deploy-strategy create command.

        Args:
            subcloud_name (str): The subcloud name.
            release (str): The software version to be deployed.
            with_delete (bool): If true, adds parameter --with-delete
            delete_only (bool): If true, adds paramater --delete-only
            subcloud_group (str): The subcloud group name.
            rollback (bool): If true, adds parameter --rollback
            snapshot (bool): If true, adds parameter --snapshot
        """
        release_id = f"--release-id {release}" if release else ""
        delete = "--with-delete" if with_delete else ""
        clean_up_delete = "--delete-only" if delete_only else ""
        rollback = "--rollback" if rollback else ""
        snapshot = "--snapshot" if snapshot else ""
        
        if subcloud_group:
            command = source_openrc(f"dcmanager sw-deploy-strategy create --group {subcloud_group} {rollback} {snapshot} {release_id} {delete} {clean_up_delete}")
            target = subcloud_group
            is_group = True
        else:
            command = source_openrc(f"dcmanager sw-deploy-strategy create {subcloud_name} {rollback} {snapshot} {release_id} {delete} {clean_up_delete}")
            target = subcloud_name
            is_group = False

        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        self.wait_sw_deployment(subcloud=target, expected_status="initial", is_group=is_group)

    def dcmanager_sw_deploy_strategy_apply(self, target: str, is_group: bool = False):
        """
        Runs dcmanager sw-deploy-strategy apply command.

        Args:
            target (str): The subcloud name or group name.
            is_group (bool): Whether the target is a group or individual subcloud.
        """
        command = source_openrc("dcmanager sw-deploy-strategy apply")

        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        deployment_timeout = self.usm_config.get_deployment_timeout_sec()
        poll_interval = self.usm_config.get_upload_poll_interval_sec()
        self.wait_sw_deployment(
            subcloud=target,
            expected_status="complete",
            timeout=deployment_timeout,
            check_interval=poll_interval,
            is_group=is_group,
        )

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
        is_group: bool = False,
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
            if is_group:
                # For subcloud groups, use dcmanager strategy-step list
                strategy_steps = DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_list()
                steps = strategy_steps.get_dcmanager_strategy_step_list()
                if not steps:
                    return "unknown"
                # Check if all subclouds have the expected state
                for step in steps:
                    if step.get_state() != expected_status:
                        return step.get_state()  # Return the first non-matching state
                return expected_status  # All subclouds have expected state
            else:
                # For individual subclouds, use dcmanager strategy-step show <subcloud_name>
                sw_deployment_status = DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_show(subcloud).get_dcmanager_strategy_step_show().get_state()
                return sw_deployment_status

        validate_equals_with_retry(
            function_to_execute=check_sw_deployment,
            expected_value=expected_status,
            validation_description=f"Waiting for sw_deployment_status {expected_status}.",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )

    def dc_manager_sw_deploy_strategy_create_apply_delete(self, subcloud_name: str = None, release: str = None, subcloud_group: str = None, with_delete: bool = False, delete_only: bool = False, rollback: bool = False, snapshot: bool = False):
        """
        Runs dcmanager sw-deploy-strategy create / apply / delete commands.

        Args:
            subcloud_name (str): The subcloud name.
            release (str): The software version to be deployed.
            subcloud_group (str): The subcloud group name.
            with_delete (bool): If true, adds parameter --with-delete
            delete_only (bool): If true, adds paramater --delete-only
            rollback (bool): If true, adds parameter --rollback
            snapshot (bool): If true, adds parameter --snapshot
        """
        target = subcloud_group if subcloud_group else subcloud_name
        is_group = bool(subcloud_group)
        get_logger().log_test_case_step(f"Create the sw-deploy strategy for {target} with {release}")
        self.dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, release=release, subcloud_group=subcloud_group, with_delete=with_delete, delete_only=delete_only, rollback=rollback, snapshot=snapshot)
        get_logger().log_test_case_step("Apply the sw-deploy strategy")
        self.dcmanager_sw_deploy_strategy_apply(target, is_group=is_group)
        time.sleep(120)
        get_logger().log_test_case_step("Delete the sw-deploy strategy")
        self.dcmanager_sw_deploy_strategy_delete()
