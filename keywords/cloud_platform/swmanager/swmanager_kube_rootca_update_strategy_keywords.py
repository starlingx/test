import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.swmanager.objects.swmanager_kube_rootca_update_strategy_object import SwManagerKubeRootcaUpdateStrategyObject
from keywords.cloud_platform.swmanager.objects.swmanager_kube_rootca_update_strategy_show_output import SwManagerKubeRootcaUpdateStrategyShowOutput


class SwManagerKubeRootcaUpdateStrategyKeywords(BaseKeyword):
    """Keywords for sw-manager kube-rootca-update-strategy commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize kube-rootca-update-strategy keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection

    def create_kube_rootca_update_strategy(self, expiry_date: str, subject: str) -> SwManagerKubeRootcaUpdateStrategyObject:
        """Create kube-rootca-update strategy.

        Args:
            expiry_date (str): Certificate expiry date (YYYY-MM-DD).
            subject (str): Certificate subject string.

        Returns:
            SwManagerKubeRootcaUpdateStrategyObject: Created strategy object.
        """
        get_logger().log_info(f"Creating kube-rootca-update strategy with expiry {expiry_date}")
        cmd = f'sw-manager kube-rootca-update-strategy create --expiry-date "{expiry_date}" --subject "{subject}"'
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return self.wait_for_ready_to_apply(180)

    def apply_kube_rootca_update_strategy(self, timeout: int = 7200) -> SwManagerKubeRootcaUpdateStrategyObject:
        """Apply kube-rootca-update strategy.

        Args:
            timeout (int): Maximum time to wait for completion in seconds.

        Returns:
            SwManagerKubeRootcaUpdateStrategyObject: Strategy object after apply.
        """
        get_logger().log_info("Applying kube-rootca-update strategy")
        self.ssh_connection.send(source_openrc("sw-manager kube-rootca-update-strategy apply"))
        self.validate_success_return_code(self.ssh_connection)
        return self.wait_for_applied(timeout)

    def show_kube_rootca_update_strategy(self) -> SwManagerKubeRootcaUpdateStrategyShowOutput:
        """Show kube-rootca-update strategy details.

        Returns:
            SwManagerKubeRootcaUpdateStrategyShowOutput: Parsed strategy show output.

        Raises:
            ConnectionRefusedError: If sw-manager service is temporarily unavailable.
        """
        output = self.ssh_connection.send(source_openrc("sw-manager kube-rootca-update-strategy show"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            error_output = "\n".join(output)
            if "Connection refused" in error_output or "500 Server Error" in error_output:
                raise ConnectionRefusedError("sw-manager service temporarily unavailable")
        return SwManagerKubeRootcaUpdateStrategyShowOutput(output)

    def delete_kube_rootca_update_strategy(self) -> None:
        """Delete kube-rootca-update strategy if it exists."""
        get_logger().log_info("Deleting kube-rootca-update strategy")
        if not self.strategy_exists():
            get_logger().log_info("No kube-rootca-update strategy to delete")
            return
        self.ssh_connection.send(source_openrc("sw-manager kube-rootca-update-strategy delete"))
        self.validate_success_return_code(self.ssh_connection)
        self.verify_no_strategy_available()

    def strategy_exists(self) -> bool:
        """Check if kube-rootca-update strategy exists.

        Returns:
            bool: True if strategy exists, False otherwise.
        """
        output = self.ssh_connection.send(source_openrc("sw-manager kube-rootca-update-strategy show"))
        self.validate_success_return_code(self.ssh_connection)
        return "No strategy available" not in "\n".join(output)

    def verify_no_strategy_available(self) -> bool:
        """Verify no kube-rootca-update strategy is available.

        Returns:
            bool: True if no strategy is available, False otherwise.
        """

        def check_no_strategy() -> bool:
            output = self.ssh_connection.send(source_openrc("sw-manager kube-rootca-update-strategy show"))
            self.validate_success_return_code(self.ssh_connection)
            return "No strategy available" in "\n".join(output)

        validate_equals_with_retry(check_no_strategy, True, "Waiting for no kube-rootca-update strategy", 300, 10)
        return True

    def wait_for_ready_to_apply(self, timeout: int = 180) -> SwManagerKubeRootcaUpdateStrategyObject:
        """Wait for strategy to reach ready-to-apply state.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            SwManagerKubeRootcaUpdateStrategyObject: Strategy object when ready to apply.
        """

        def check_ready() -> bool:
            strategy_output = self.show_kube_rootca_update_strategy()
            strategy_obj = strategy_output.get_strategy()
            if strategy_obj.is_building():
                get_logger().log_info("Strategy is building")
            elif strategy_obj.is_build_failed():
                raise Exception("Strategy build failed")
            return strategy_obj.is_ready_to_apply()

        validate_equals_with_retry(check_ready, True, "Waiting for strategy ready to apply", timeout, 10)
        return self.show_kube_rootca_update_strategy().get_strategy()

    def wait_for_applied(self, timeout: int = 7200) -> SwManagerKubeRootcaUpdateStrategyObject:
        """Wait for strategy to reach applied state.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            SwManagerKubeRootcaUpdateStrategyObject: Strategy object when successfully applied.
        """
        unavailable_start = None

        def check_applied() -> bool:
            nonlocal unavailable_start
            try:
                strategy_output = self.show_kube_rootca_update_strategy()
                strategy_obj = strategy_output.get_strategy()
                unavailable_start = None

                if strategy_obj.is_applying():
                    phase = strategy_obj.get_current_phase()
                    stage = strategy_obj.get_current_stage()
                    completion = strategy_obj.get_current_phase_completion()
                    get_logger().log_info(f"Strategy applying: {phase}/{stage} ({completion} complete)")
                elif strategy_obj.is_apply_failed():
                    raise Exception("Strategy apply failed")
                return strategy_obj.is_applied()
            except ConnectionRefusedError:
                if unavailable_start is None:
                    unavailable_start = time.time()
                    get_logger().log_debug("sw-manager service temporarily unavailable")
                elif time.time() - unavailable_start > 180:
                    raise Exception("sw-manager service unavailable for more than 3 minutes")
                return False

        validate_equals_with_retry(check_applied, True, "Waiting for strategy applied", timeout, 30)
        return self.show_kube_rootca_update_strategy().get_strategy()
