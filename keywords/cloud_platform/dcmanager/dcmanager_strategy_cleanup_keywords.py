from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc

STRATEGY_NOT_FOUND_PATTERN = "doesn't exist"


class DcmanagerStrategyCleanupKeywords(BaseKeyword):
    """Keywords for cleaning up dcmanager strategies in teardown.

    Provides idempotent strategy deletion that handles the case where
    no strategy exists without raising.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the system controller.
        """
        self.ssh_connection = ssh_connection

    def cleanup_strategy(self, strategy_type: str) -> None:
        """Delete a dcmanager strategy if it exists. No-op if no strategy is present.

        This is idempotent and safe to call in teardown regardless of whether
        a strategy was created during the test.

        Args:
            strategy_type (str): The strategy type to delete. Valid values:
                "sw-deploy", "kube-upgrade", "kube-rootca-update", "prestage".
        """
        get_logger().log_info(f"Attempting to delete {strategy_type}-strategy")
        cmd = source_openrc(f"dcmanager {strategy_type}-strategy delete")
        output = self.ssh_connection.send(cmd)
        output_str = "".join(output)

        if STRATEGY_NOT_FOUND_PATTERN in output_str:
            get_logger().log_info(f"No {strategy_type}-strategy exists, nothing to delete")
            return

        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"Deleted {strategy_type}-strategy successfully")
