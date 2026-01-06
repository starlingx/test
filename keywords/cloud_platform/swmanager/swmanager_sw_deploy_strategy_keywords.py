import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_show_output import (
    SwManagerSwDeployStrategyShowOutput
)
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_create_config import (
    SwManagerSwDeployStrategyCreateConfig
)


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

    def get_sw_deploy_strategy_abort(self) -> bool:
        """Aborts the sw-deploy-strategy.
        
        Returns:
            bool: True if abort was successful, False otherwise.
        """
        command = source_openrc("sw-manager sw-deploy-strategy abort")
        self.ssh_connection.send(command)
        try:
            self.validate_success_return_code(self.ssh_connection)
            return True
        except AssertionError:
            return False

    def get_sw_deploy_strategy_apply(self) -> bool:
        """Applies the sw-deploy-strategy.
        
        Returns:
            bool: True if apply command was successful, False otherwise.
        """
        command = source_openrc("sw-manager sw-deploy-strategy apply")
        self.ssh_connection.send(command)
        try:
            self.validate_success_return_code(self.ssh_connection)
            return True
        except AssertionError:
            return False

    def get_sw_deploy_strategy_create(self, config: SwManagerSwDeployStrategyCreateConfig) -> bool:
        """Creates the sw-deploy-strategy.
        
        Args:
            config (SwManagerSwDeployStrategyCreateConfig): Configuration object containing all create parameters.
        
        Returns:
            bool: True if create command was successful, False otherwise.
        """
        args_str = config.build_command_args()
        command = source_openrc(f"sw-manager sw-deploy-strategy create {args_str} {config.release}")
        self.ssh_connection.send(command)
        try:
            self.validate_success_return_code(self.ssh_connection)
            return True
        except AssertionError:
            return False

    def get_sw_deploy_strategy_show(self, timeout: int = 60) -> SwManagerSwDeployStrategyShowOutput:
        """Gets the sw-deploy-strategy show.
        
        Args:
            timeout (int): Timeout in seconds (default: 60).
        
        Returns:
            SwManagerSwDeployStrategyShowOutput: An object containing details of the prestage strategy.
        """
        command = source_openrc("sw-manager sw-deploy-strategy show")
        timeout_time = time.time() + timeout
        retry_interval = 10
        connection_retry_count = 0
        max_connection_retries = 3
        
        while time.time() < timeout_time:
            try:
                output = self.ssh_connection.send(command)
                return SwManagerSwDeployStrategyShowOutput(output)
            except Exception as e:
                error_msg = str(e).lower()
                if "connection" in error_msg or "timeout" in error_msg or "nonetype" in error_msg:
                    connection_retry_count += 1
                    if connection_retry_count <= max_connection_retries:
                        get_logger().log_info(f"Connection issue during system operation (attempt {connection_retry_count}/{max_connection_retries}), retrying in {retry_interval} seconds...")
                        time.sleep(retry_interval)
                        continue
                    else:
                        get_logger().log_warning(f"Max connection retries reached, continuing with longer interval...")
                        connection_retry_count = 0
                        time.sleep(30)
                else:
                    get_logger().log_debug(f"Non-connection error: {e}, retrying in {retry_interval} seconds...")
                    time.sleep(retry_interval)
        
        # Final attempt after timeout
        try:
            output = self.ssh_connection.send(command)
            return SwManagerSwDeployStrategyShowOutput(output)
        except Exception as e:
            get_logger().log_error(f"Final attempt failed: {e}")
            raise

    def get_sw_deploy_strategy_show_details(self) -> list:
        """Gets the sw-deploy-strategy show --details.
        
        Returns:
            list: Raw output of the sw-deploy-strategy show --details command.
        """
        command = source_openrc("sw-manager sw-deploy-strategy show --details")
        output = self.ssh_connection.send(command)
        return output

    def check_sw_deploy_strategy_exists(self) -> bool:
        """Checks if a sw-deploy-strategy exists without deleting it.
        
        Returns:
            bool: True if a strategy exists, False if no strategy exists.
        """
        try:
            output = self.get_sw_deploy_strategy_show()
            return True
        except Exception:
            return False

    def get_sw_deploy_strategy_delete(self) -> bool:
        """Starts sw-deploy-strategy deletion.
        
        Returns:
            bool: True if delete command was successful, False otherwise.
        """
        command = source_openrc("sw-manager sw-deploy-strategy delete")
        output = self.ssh_connection.send(command)
        try:
            self.validate_success_return_code(self.ssh_connection)
            self.log_delete_result(output)
            return True
        except AssertionError:
            return False

    def wait_for_state(self, state: list, timeout: int = 1800) -> bool:
        """Waits for the sw-deploy-strategy to reach a specific state.
        
        Args:
            state (list): The desired state to wait for.
            timeout (int): The maximum time to wait in seconds.
        
        Returns:
            bool: True if desired state is reached, False if timeout.
        """
        end_time = time.time() + timeout
        retry_interval = 15
        connection_issues = 0
        
        while time.time() < end_time:
            try:
                output = self.get_sw_deploy_strategy_show(timeout=120).get_swmanager_sw_deploy_strategy_show()
                if output.get_state() in state:
                    return True
                connection_issues = 0  # Reset counter on successful connection
            except Exception as e:
                connection_issues += 1
                error_msg = str(e).lower()
                if "connection" in error_msg or "timeout" in error_msg:
                    if connection_issues <= 5:
                        get_logger().log_info(f"Connection issue during state monitoring (#{connection_issues}), system may be rebooting. Retrying...")
                    else:
                        get_logger().log_warning(f"Extended connection issues detected, continuing to monitor...")
                else:
                    get_logger().log_debug(f"Error getting strategy status: {e}. Retrying...")
            
            # Only sleep if we haven't reached timeout
            if time.time() + retry_interval < end_time:
                time.sleep(retry_interval)
        
        return False

    def is_delete_completed(self, output: list) -> bool:
        """Checks if delete operation is completed based on output.
        
        Args:
            output (list): Command output to check.
            
        Returns:
            bool: True if deletion is completed or nothing to delete.
        """
        output_str = "".join(output)
        if "Nothing to delete" in output_str or "Strategy deleted" in output_str:
            get_logger().log_info("Strategy deletion completed or no strategy to delete")
            return True
        return False

    def log_delete_result(self, output: list) -> None:
        """Logs the result of delete operation.
        
        Args:
            output (list): Command output to analyze.
        """
        output_str = "".join(output)
        if "Nothing to delete" in output_str:
            get_logger().log_info("No strategy to delete")
        elif "Strategy deleted" in output_str:
            get_logger().log_info("Strategy deleted successfully")
        else:
            get_logger().log_warning(f"Unexpected deletion output: {output_str}")
