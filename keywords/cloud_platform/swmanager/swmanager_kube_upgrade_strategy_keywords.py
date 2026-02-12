import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.swmanager.objects.swmanager_kube_upgrade_strategy_object import SwManagerKubeUpgradeStrategyObject
from keywords.cloud_platform.swmanager.objects.swmanager_kube_upgrade_strategy_show_output import SwManagerKubeUpgradeStrategyShowOutput


class SwManagerKubeUpgradeStrategyKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'sw-manager kube-upgrade-strategy' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize SwManagerKubeUpgradeStrategyKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def create_sw_manager_kube_upgrade_strategy(
        self,
        target_kube_version: str,
    ) -> SwManagerKubeUpgradeStrategyObject:
        """Create a Kubernetes upgrade strategy using sw-manager.

        Args:
            target_kube_version (str): Target Kubernetes version for upgrade.

        Returns:
            SwManagerKubeUpgradeStrategyObject: The created strategy object.
        """
        get_logger().log_info(f"Creating Kubernetes upgrade strategy for version {target_kube_version}")
        command = source_openrc(f"sw-manager kube-upgrade-strategy create --to-version {target_kube_version}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        # Wait for strategy to be built
        return self.wait_for_ready_to_apply(180)

    def apply_kube_upgrade_strategy(self, timeout: int = 3600) -> SwManagerKubeUpgradeStrategyObject:
        """Apply the Kubernetes upgrade strategy.

        Args:
            timeout (int): Maximum time to wait for strategy completion in seconds.

        Returns:
            SwManagerKubeUpgradeStrategyObject: The strategy object after apply.
        """
        get_logger().log_info("Applying Kubernetes upgrade strategy")

        command = source_openrc("sw-manager kube-upgrade-strategy apply")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        # Wait for strategy to complete
        return self.wait_for_applied(timeout=timeout)

    def abort_kube_upgrade_strategy(self) -> SwManagerKubeUpgradeStrategyObject:
        """Abort the Kubernetes upgrade strategy.

        Returns:
            SwManagerKubeUpgradeStrategyObject: The strategy object after apply.
        """
        get_logger().log_info("Aborting Kubernetes upgrade strategy")

        command = source_openrc("sw-manager kube-upgrade-strategy abort")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        # Wait for strategy to abort
        return self.wait_for_aborted()

    def show_kube_upgrade_strategy(self) -> SwManagerKubeUpgradeStrategyShowOutput:
        """Show the Kubernetes upgrade strategy details.

        Returns:
            SwManagerKubeUpgradeStrategyShowOutput: Strategy show output object.

        Raises:
            ConnectionRefusedError: If sw-manager service is temporarily unavailable.
        """
        command = source_openrc("sw-manager kube-upgrade-strategy show")
        output = self.ssh_connection.send(command)
        rc = self.ssh_connection.get_return_code()

        # Allow connection refused and internal server errors during upgrade (service temporarily unavailable)
        if rc != 0:
            error_output = "\n".join(output)
            if "Connection refused" in error_output or "500 Server Error: Internal Server Error" in error_output:
                raise ConnectionRefusedError("sw-manager service temporarily unavailable")

        return SwManagerKubeUpgradeStrategyShowOutput(output)

    def show_kube_upgrade_strategy_details(self) -> list[str]:
        """Show the Kubernetes upgrade strategy with detailed timing information.

        Returns:
            list[str]: Detailed strategy output lines.
        """
        command = source_openrc("sw-manager kube-upgrade-strategy show --details")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return output

    def verify_no_kube_upgrade_strategy_available(self) -> bool:
        """Verify that no Kubernetes upgrade strategy is available.

        Returns:
            bool: True if no strategy is available, False otherwise.
        """

        def check_no_strategy() -> bool:
            command = source_openrc("sw-manager kube-upgrade-strategy show")
            output = self.ssh_connection.send(command)
            self.validate_success_return_code(self.ssh_connection)
            return "No strategy available" in "\n".join(output)

        validate_equals_with_retry(function_to_execute=check_no_strategy, expected_value=True, validation_description="Waiting for no kube upgrade strategy to be available", timeout=300, polling_sleep_time=10)
        return True

    def kube_upgrade_strategy_exists(self) -> bool:
        """Check if a Kubernetes upgrade strategy exists.

        Returns:
            bool: True if strategy exists, False otherwise.
        """
        command = source_openrc("sw-manager kube-upgrade-strategy show")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return "No strategy available" not in "\n".join(output)

    def delete_kube_upgrade_strategy(self) -> None:
        """Delete the Kubernetes upgrade strategy if it exists."""
        get_logger().log_info("Deleting Kubernetes upgrade strategy")

        # Check if strategy exists first
        if not self.kube_upgrade_strategy_exists():
            get_logger().log_info("No kube upgrade strategy to delete")
            return

        # Strategy exists, proceed with deletion
        command = source_openrc("sw-manager kube-upgrade-strategy delete")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        self.verify_no_kube_upgrade_strategy_available()

    def wait_for_ready_to_apply(self, timeout: int = 180) -> SwManagerKubeUpgradeStrategyObject:
        """Wait for strategy to be ready to apply.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            SwManagerKubeUpgradeStrategyObject: Strategy object when ready to apply.
        """

        def check_ready() -> bool:
            strategy_output = self.show_kube_upgrade_strategy()
            strategy_obj = strategy_output.get_swmanager_kube_upgrade_strategy_show()
            if strategy_obj.is_building():
                get_logger().log_info("Kube-upgrade-strategy is currently in Building state")
            elif strategy_obj.is_build_failed():
                get_logger().log_info("Kube-upgrade-strategy is currently in Build-failed state")
                return False
            return strategy_obj.is_ready_to_apply()

        validate_equals_with_retry(function_to_execute=check_ready, expected_value=True, validation_description="Waiting for kube-upgrade-strategy to be ready to apply", timeout=timeout, polling_sleep_time=10)

        return self.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()

    def _check_strategy_state(self, strategy_obj: SwManagerKubeUpgradeStrategyObject) -> None:
        """Check and log strategy state, raise exception if in failed state.

        This method monitors the current state of the upgrade strategy and logs
        progress information. It raises exceptions for terminal failure states.

        Args:
            strategy_obj (SwManagerKubeUpgradeStrategyObject): Current strategy object.

        Raises:
            Exception: If strategy is in Apply-failed, Aborted, or Abort-failed state.
        """
        # Log progress for active states
        if strategy_obj.is_applying():
            phase = strategy_obj.get_current_phase()
            stage = strategy_obj.get_current_stage()
            completion = strategy_obj.get_current_phase_completion()
            get_logger().log_info(f"Kube-upgrade-strategy applying: {phase}/{stage} ({completion} complete)")
        elif strategy_obj.is_aborting():
            phase = strategy_obj.get_current_phase()
            stage = strategy_obj.get_current_stage()
            completion = strategy_obj.get_current_phase_completion()
            get_logger().log_info(f"Kube-upgrade-strategy aborting: {phase}/{stage} ({completion} complete)")
        # Raise exceptions for failure states
        elif strategy_obj.is_apply_failed():
            raise Exception("Kube-upgrade-strategy is in Apply-failed state")
        elif strategy_obj.is_aborted():
            raise Exception("Kube-upgrade-strategy is in Aborted state")
        elif strategy_obj.is_abort_failed():
            raise Exception("Kube-upgrade-strategy is in Abort-failed state")

    def wait_for_applied(self, timeout: int = 3600) -> SwManagerKubeUpgradeStrategyObject:
        """Wait for strategy to be applied.

        This method monitors the Kubernetes upgrade strategy until it completes.
        The method handles temporary service unavailability (up to 3 minutes) which
        can occur during certain upgrade operations like control plane upgrades.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            SwManagerKubeUpgradeStrategyObject: Strategy object when applied.

        Raises:
            Exception: If strategy enters Apply-failed or Aborted state, or if
                      sw-manager service is unavailable for more than 3 minutes.
        """
        unavailable_start = None

        def check_applied() -> bool:
            nonlocal unavailable_start

            try:
                # Attempt to get current strategy status
                strategy_output = self.show_kube_upgrade_strategy()
                strategy_obj = strategy_output.get_swmanager_kube_upgrade_strategy_show()

                # Service is available - reset unavailability timer if it was set
                unavailable_start = None

                # Check strategy state and log progress or raise exceptions for failures
                self._check_strategy_state(strategy_obj)
                # Return True if strategy is applied, False otherwise to continue polling
                return strategy_obj.is_applied()
            except ConnectionRefusedError:
                # Service temporarily unavailable - track elapsed time
                if unavailable_start is None:
                    # First time seeing unavailability - start timer
                    unavailable_start = time.time()
                    get_logger().log_debug("sw-manager service temporarily unavailable, will retry")
                elif time.time() - unavailable_start > 180:
                    # Fail if service has been unavailable for more than 3 minutes
                    raise Exception("sw-manager service unavailable for more than 3 minutes")
                else:
                    # Service still unavailable - log elapsed time
                    get_logger().log_debug(f"sw-manager service still unavailable ({int(time.time() - unavailable_start)}s elapsed, max 180s)")
                # Return False to retry after polling interval
                return False

        # Poll check_applied() every 30 seconds until it returns True or timeout
        validate_equals_with_retry(function_to_execute=check_applied, expected_value=True, validation_description="Waiting for kube-upgrade-strategy to be applied", timeout=timeout, polling_sleep_time=30)
        # Strategy applied successfully - return final strategy object
        return self.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()

    def wait_for_aborted(self, timeout: int = 600) -> SwManagerKubeUpgradeStrategyObject:
        """Wait for strategy to be aborted.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            SwManagerKubeUpgradeStrategyObject: Strategy object when aborted.
        """

        def check_aborted() -> bool:
            strategy_output = self.show_kube_upgrade_strategy()
            strategy_obj = strategy_output.get_swmanager_kube_upgrade_strategy_show()
            if strategy_obj.is_abort_failed():
                get_logger().log_info("Kube-upgrade-strategy is currently in Abort-failed state")
                return False
            return strategy_obj.is_aborted()

        validate_equals_with_retry(function_to_execute=check_aborted, expected_value=True, validation_description="Waiting for kube-upgrade-strategy to be aborted", timeout=timeout, polling_sleep_time=10)

        return self.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()
