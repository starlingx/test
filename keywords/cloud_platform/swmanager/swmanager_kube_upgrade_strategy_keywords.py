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
        controller_apply_type: str = None,
        storage_apply_type: str = None,
        worker_apply_type: str = None,
        instance_action: str = None,
        alarm_restrictions: str = None,
        max_parallel_worker_hosts: str = None,
    ) -> SwManagerKubeUpgradeStrategyObject:
        """Create a Kubernetes upgrade strategy using sw-manager.

        Args:
            target_kube_version (str): Target Kubernetes version for upgrade.
            controller_apply_type (str): Controller apply type (serial or ignore).
            storage_apply_type (str): Storage apply type (serial or ignore).
            worker_apply_type (str): Worker apply type (serial, parallel, or ignore).
            instance_action (str): Instance action (stop-start or migrate).
            alarm_restrictions (str): Alarm restrictions (strict or relaxed).
            max_parallel_worker_hosts (str): Maximum worker hosts to update in parallel (2-10, or "None" if not set).

        Returns:
            SwManagerKubeUpgradeStrategyObject: The created strategy object.
        """
        get_logger().log_info(f"Creating Kubernetes upgrade strategy - target_kube_version: {target_kube_version}, controller_apply_type: {controller_apply_type}, storage_apply_type: {storage_apply_type}, worker_apply_type: {worker_apply_type}, instance_action: {instance_action}, alarm_restrictions: {alarm_restrictions}, max_parallel_worker_hosts: {max_parallel_worker_hosts}")

        cmd = f"sw-manager kube-upgrade-strategy create --to-version {target_kube_version}"
        if controller_apply_type and controller_apply_type != "None":
            cmd += f" --controller-apply-type {controller_apply_type}"
        if storage_apply_type and storage_apply_type != "None":
            cmd += f" --storage-apply-type {storage_apply_type}"
        if worker_apply_type and worker_apply_type != "None":
            cmd += f" --worker-apply-type {worker_apply_type}"
        if instance_action and instance_action != "None":
            cmd += f" --instance-action {instance_action}"
        if alarm_restrictions and alarm_restrictions != "None":
            cmd += f" --alarm-restrictions {alarm_restrictions}"
        if max_parallel_worker_hosts and str(max_parallel_worker_hosts) != "None":
            cmd += f" --max-parallel-worker-hosts {max_parallel_worker_hosts}"

        command = source_openrc(cmd)
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        # Wait for strategy to be built
        return self.wait_for_ready_to_apply(180)

    def apply_kube_upgrade_strategy(self, timeout: int = 7200) -> SwManagerKubeUpgradeStrategyObject:
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

    def apply_kube_upgrade_strategy_without_waiting(self) -> None:
        """Apply the Kubernetes upgrade strategy without waiting for completion."""
        get_logger().log_info("Applying Kubernetes upgrade strategy (non-blocking)")
        command = source_openrc("sw-manager kube-upgrade-strategy apply")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

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

    def abort_kube_upgrade_strategy_without_waiting(self) -> None:
        """Abort the Kubernetes upgrade strategy without waiting for completion."""
        get_logger().log_info("Aborting Kubernetes upgrade strategy")
        command = source_openrc("sw-manager kube-upgrade-strategy abort")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

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

        # During host lock/unlock/reboot/swact (e.g. the kubelet stage) the SSH
        # session to the active controller can drop and reconnect. In that window
        # send() may return None or non-list output. Treat that as a transient
        # unavailability and signal the caller to retry, rather than letting the
        # parser crash with "can only join an iterable".
        if not isinstance(output, list):
            raise ConnectionRefusedError("sw-manager show returned no usable output (host lock/unlock/swact in progress)")

        # Allow connection refused, internal server errors, and empty responses during
        # upgrade (sw-manager service temporarily unavailable while hosts cycle).
        if rc != 0:
            error_output = "\n".join(output)
            if "Connection refused" in error_output or "500 Server Error: Internal Server Error" in error_output or "Unable to establish connection" in error_output or error_output.strip() == "":
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
        It tolerates transient unavailability of the sw-manager API and of the SSH
        session to the active controller, which happens while hosts are
        locked/unlocked/rebooted/swacted during the strategy (notably the kubelet
        stage). Such transient errors are retried; the overall ``timeout`` bounds
        the total wait. Only real terminal failure states abort the wait.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            SwManagerKubeUpgradeStrategyObject: Strategy object when applied.

        Raises:
            Exception: If strategy enters Apply-failed, Aborted, or Abort-failed state,
                      or if the strategy does not reach 'applied' within ``timeout``.
        """

        def check_applied() -> bool:
            try:
                # Attempt to get current strategy status
                strategy_output = self.show_kube_upgrade_strategy()
                strategy_obj = strategy_output.get_swmanager_kube_upgrade_strategy_show()

                # Check strategy state and log progress or raise exceptions for failures
                self._check_strategy_state(strategy_obj)
                # Return True if strategy is applied, False otherwise to continue polling
                return strategy_obj.is_applied()
            except ConnectionRefusedError:
                # sw-manager API or the SSH session to the active controller is
                # temporarily unavailable while a host is locked/unlocked/rebooted/
                # swacted during the strategy. Keep polling; the outer 'timeout'
                # bounds the total wait so a lengthy reboot/swact no longer causes a
                # spurious failure.
                get_logger().log_info("sw-manager service/SSH temporarily unavailable during host lock/unlock/swact, retrying")
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

    def wait_for_current_phase_completion(self, timeout: int = 3600) -> SwManagerKubeUpgradeStrategyObject:
        """Wait for the current-phase-completion to reach 100%.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            SwManagerKubeUpgradeStrategyObject: Strategy object when phase completion is 100%.

        Raises:
            Exception: If strategy enters a failed state.
        """

        def check_completion() -> bool:
            try:
                strategy_output = self.show_kube_upgrade_strategy()
                strategy_obj = strategy_output.get_swmanager_kube_upgrade_strategy_show()
                completion = strategy_obj.get_current_phase_completion_percentage()
                get_logger().log_info(f"Current phase completion: {strategy_obj.get_current_phase_completion()}")
                return completion == 100
            except ConnectionRefusedError:
                get_logger().log_info("sw-manager service temporarily unavailable, retrying")
                return False

        validate_equals_with_retry(function_to_execute=check_completion, expected_value=True, validation_description="Waiting for current-phase-completion to reach 100%", timeout=timeout, polling_sleep_time=30)

        return self.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()

    def wait_for_kube_upgrade_step(self, target_state: str, timeout: int = 600) -> None:
        """Wait for the current step of the kube-upgrade-strategy to reach the target state.

        Args:
            target_state (str): The current-step value to wait for (e.g. 'kube-host-upgrade-control-plane').
            timeout (int): Maximum wait time in seconds.
        """

        def check_step() -> bool:
            try:
                strategy_output = self.show_kube_upgrade_strategy()
                strategy_obj = strategy_output.get_swmanager_kube_upgrade_strategy_show()
                current_step = strategy_obj.get_current_step()
                get_logger().log_info(f"Current step: {current_step}, waiting for: {target_state}")
                return current_step is not None and target_state in current_step
            except ConnectionRefusedError:
                get_logger().log_info("sw-manager service temporarily unavailable, retrying")
                return False

        validate_equals_with_retry(function_to_execute=check_step, expected_value=True, validation_description=f"Waiting for kube-upgrade-strategy step to reach {target_state}", timeout=timeout, polling_sleep_time=5)
