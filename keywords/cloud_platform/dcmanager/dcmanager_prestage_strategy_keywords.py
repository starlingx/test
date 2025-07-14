import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_prestage_strategy_object import DcmanagerPrestageStrategyObject
from keywords.cloud_platform.dcmanager.objects.dcmanager_prestage_strategy_show_output import DcmanagerPrestageStrategyShowOutput


class DcmanagerPrestageStrategyKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager prestage-strategy' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> str:
        """
        Initializes DcmanagerPrestageStrategyKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_prestage_strategy_abort(self) -> str:
        """Gets the prestage-strategy abort."""
        command = source_openrc("dcmanager prestage-strategy abort")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return output

    def get_dcmanager_prestage_strategy_apply(self) -> DcmanagerPrestageStrategyObject:
        """Gets the prestage-strategy apply.

        Returns:
            DcmanagerPrestageStrategyObject: An object containing details of the prestage strategy.
        """
        command = source_openrc("dcmanager prestage-strategy apply")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        # wait for apply to complete
        return self.wait_for_state(["complete", "failed"])

    def get_dcmanager_prestage_strategy_create(self, sysadmin_password: str, sw_deploy: bool = True, subcloud_name: str = None) -> DcmanagerPrestageStrategyShowOutput:
        """Gets the prestage-strategy create.

        Args:
            sysadmin_password (str): The password for the sysadmin user.
            sw_deploy (bool): If True, include the --for-sw-deploy argument in the command.
            subcloud_name (str): The subcloud name.

        Returns:
            DcmanagerPrestageStrategyShowOutput: The output of the prestage strategy.
        """
        sw_deploy_arg = "--for-sw-deploy" if sw_deploy else ""
        subcloud_name_arg = subcloud_name if subcloud_name else ""
        command = source_openrc(f"dcmanager prestage-strategy create {sw_deploy_arg} --sysadmin-password {sysadmin_password} {subcloud_name_arg}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPrestageStrategyShowOutput(output)

    def get_dcmanager_prestage_strategy_show(self) -> DcmanagerPrestageStrategyShowOutput:
        """
        Gets the prestage-strategy show.

        Returns:
            DcmanagerPrestageStrategyShowOutput: An object containing details of the prestage strategy .
        """
        command = source_openrc("dcmanager prestage-strategy show")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPrestageStrategyShowOutput(output)

    def check_dcmanager_prestage_strategy_delete(self):
        """Gets the prestage-strategy delete."""
        command = source_openrc("dcmanager prestage-strategy delete")
        output = self.ssh_connection.send(command)
        if "Unable to delete strategy of type" in "".join(output):
            get_logger().log_info("No strategy to be deleted, moving on...")
            return True
        return False

    def get_dcmanager_prestage_strategy_delete(self):
        """
        Starts sw-deploy-strategy deletion process if there is a strategy in progress and waits for its deletion.
        """
        validate_equals_with_retry(function_to_execute=self.check_dcmanager_prestage_strategy_delete, expected_value=True, validation_description="Waits for strategy deletion", timeout=600, polling_sleep_time=10)

    def wait_for_state(self, state: list, timeout: int = 1800) -> DcmanagerPrestageStrategyObject:
        """Waits for the prestage-strategy to reach a specific state.

        Args:
            state (list): The desired state to wait for.
            timeout (int): The maximum time to wait in seconds.

        Returns:
            DcmanagerPrestageStrategyObject: The output of the prestage-strategy show command when the desired state is reached.
        """
        # possibles states :  initial, deleting, deleting, complete, aborting, applying
        interval = 10
        start_time = time.time()
        while time.time() - start_time < timeout:
            output = self.get_dcmanager_prestage_strategy_show().get_dcmanager_prestage_strategy()
            if output.get_state() in state:
                return output
            else:
                # execute the dcmanager strategy-step list for monitoring
                DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_list()
            time.sleep(interval)
        raise TimeoutError(f"Timed out waiting for prestage-strategy to reach state '{state}' after {timeout} seconds.")

    def dc_manager_prestage_strategy_create_apply_delete(self, sw_deploy: bool = True, subcloud_name: str = None):
        """Creates, applies, and deletes a prestage strategy.

        Args:
            sw_deploy (bool): If True, the strategy will be created with the --for-sw-deploy argument.
            subcloud_name (str): The subcloud name.
        """
        get_logger().log_info("Starting the prestage strategy creation, application, and deletion process.")
        sysadmin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        get_logger().log_test_case_step("Create the prestage strategy")
        prestage_strategy_out = self.get_dcmanager_prestage_strategy_create(sysadmin_password=sysadmin_password, sw_deploy=sw_deploy, subcloud_name=subcloud_name)
        get_logger().log_info(f"Created prestage strategy state: {prestage_strategy_out.get_dcmanager_prestage_strategy().get_state()}")
        get_logger().log_test_case_step("Apply the strategy")
        dcman_obj = self.get_dcmanager_prestage_strategy_apply()
        validate_equals(dcman_obj.get_state(), "complete", "prestage strategy applied successfully.")
        get_logger().log_test_case_step("Delete the strategy")
        self.get_dcmanager_prestage_strategy_delete()
