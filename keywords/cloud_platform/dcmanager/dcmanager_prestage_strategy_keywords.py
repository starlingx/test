import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import oidc_auth_wrap, source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_prestage_strategy_object import DcmanagerPrestageStrategyObject
from keywords.cloud_platform.dcmanager.objects.dcmanager_prestage_strategy_show_output import DcmanagerPrestageStrategyShowOutput


class DcmanagerPrestageStrategyKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager prestage-strategy' commands.
    """

    def __init__(self, ssh_connection: SSHConnection, use_oidc: bool = False) -> str:
        """
        Initializes DcmanagerPrestageStrategyKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
            use_oidc (bool): If True, use OIDC authentication instead of source_openrc.
        """
        self.ssh_connection = ssh_connection
        self.use_oidc = use_oidc

    def _wrap_command(self, cmd: str) -> str:
        """Wrap a dcmanager command with the appropriate auth method.

        Args:
            cmd (str): Raw dcmanager command.

        Returns:
            str: Command wrapped with either source_openrc or OIDC auth.
        """
        if self.use_oidc:
            return oidc_auth_wrap(cmd)
        return source_openrc(cmd)

    def get_dcmanager_prestage_strategy_abort(self) -> str:
        """Gets the prestage-strategy abort."""
        command = self._wrap_command("dcmanager prestage-strategy abort")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return output

    def get_dcmanager_prestage_strategy_apply(self) -> DcmanagerPrestageStrategyObject:
        """Gets the prestage-strategy apply.

        Returns:
            DcmanagerPrestageStrategyObject: An object containing details of the prestage strategy.
        """
        command = self._wrap_command("dcmanager prestage-strategy apply")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        # wait for apply to complete
        return self.wait_for_state(["complete", "failed"])

    def get_dcmanager_prestage_strategy_create(self, release: str = None, sw_deploy: bool = True, subcloud_name: str = None, subcloud_group: str = None) -> DcmanagerPrestageStrategyShowOutput:
        """Gets the prestage-strategy create.

        Args:
            release (str): The software release to be used for the strategy.
            sw_deploy (bool): If True, include the --for-sw-deploy argument in the command,
             if False include --for-install argument.
            subcloud_name (str): The subcloud name.
            subcloud_group (str): The subcloud group name.

        Returns:
            DcmanagerPrestageStrategyShowOutput: The output of the prestage strategy.
        """
        sysadmin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        sw_deploy_arg = "--for-sw-deploy" if sw_deploy else "--for-install"
        release_id = f"--release {release}" if release else ""
        
        if subcloud_group:
            command = self._wrap_command(f"dcmanager prestage-strategy create {release_id} {sw_deploy_arg} --sysadmin-password {sysadmin_password} --group {subcloud_group}")
        else:
            subcloud_name_arg = subcloud_name if subcloud_name else ""
            command = self._wrap_command(f"dcmanager prestage-strategy create {release_id} {sw_deploy_arg} --sysadmin-password {sysadmin_password} {subcloud_name_arg}")
        
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPrestageStrategyShowOutput(output)

    def get_dcmanager_prestage_strategy_show(self) -> DcmanagerPrestageStrategyShowOutput:
        """
        Gets the prestage-strategy show.

        Returns:
            DcmanagerPrestageStrategyShowOutput: An object containing details of the prestage strategy .
        """
        command = self._wrap_command("dcmanager prestage-strategy show")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPrestageStrategyShowOutput(output)

    def check_dcmanager_prestage_strategy_delete(self):
        """Gets the prestage-strategy delete."""
        command = self._wrap_command("dcmanager prestage-strategy delete")
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

    def dc_manager_prestage_strategy_create_apply_delete(self, release: str = None, sw_deploy: bool = True, subcloud_name: str = None, subcloud_group: str = None):
        """Creates, applies, and deletes a prestage strategy.

        Args:
            release (str): The software release to be used for the strategy.
            sw_deploy (bool): If True, the strategy will be created with the --for-sw-deploy argument.
            subcloud_name (str): The subcloud name.
            subcloud_group (str): The subcloud group name.
        """
        get_logger().log_info("Starting the prestage strategy creation, application, and deletion process.")
        get_logger().log_test_case_step("Create the prestage strategy")
        prestage_strategy_out = self.get_dcmanager_prestage_strategy_create(release=release, sw_deploy=sw_deploy, subcloud_name=subcloud_name, subcloud_group=subcloud_group)
        get_logger().log_info(f"Created prestage strategy state: {prestage_strategy_out.get_dcmanager_prestage_strategy().get_state()}")
        get_logger().log_test_case_step("Apply the strategy")
        dcman_obj = self.get_dcmanager_prestage_strategy_apply()
        validate_equals(dcman_obj.get_state(), "complete", "prestage strategy applied successfully.")
        get_logger().log_test_case_step("Delete the strategy")
        self.get_dcmanager_prestage_strategy_delete()
