from typing import List, Optional, Tuple

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import oidc_auth_wrap, source_openrc

STRATEGY_NOT_FOUND_PATTERN = "doesn't exist"
# A strategy that is actively applying cannot be deleted. Deletion is only valid
# once the strategy is in a settled/terminal state (initial/complete/failed/
# aborted). We must not force-delete a running strategy in teardown.
STRATEGY_RUNNING_PATTERN = "cannot be deleted"

# Every dcmanager strategy command prefix, i.e. "dcmanager <prefix>-strategy".
# dcmanager allows only ONE strategy to exist at a time regardless of type, so a
# leftover strategy of any type blocks creating a new one with:
#   Bad strategy request: Strategy of type: '<type>' already exists
ALL_STRATEGY_TYPES = [
    "sw-deploy",
    "kube-upgrade",
    "kube-rootca-update",
    "prestage",
    "fw-update",
]


class DcmanagerStrategyCleanupKeywords(BaseKeyword):
    """Keywords for cleaning up dcmanager strategies in teardown.

    Provides idempotent strategy deletion that handles the case where
    no strategy exists without raising.
    """

    def __init__(self, ssh_connection: SSHConnection, use_oidc: bool = False):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the system controller.
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

    def cleanup_strategy(self, strategy_type: str) -> None:
        """Delete a dcmanager strategy if it exists. No-op if no strategy is present.

        This is idempotent and safe to call in teardown regardless of whether
        a strategy was created during the test.

        Args:
            strategy_type (str): The strategy type to delete. Valid values:
                "sw-deploy", "kube-upgrade", "kube-rootca-update", "prestage".
        """
        get_logger().log_info(f"Attempting to delete {strategy_type}-strategy")
        cmd = self._wrap_command(f"dcmanager {strategy_type}-strategy delete")
        output = self.ssh_connection.send(cmd)
        output_str = "".join(output)

        if STRATEGY_NOT_FOUND_PATTERN in output_str:
            get_logger().log_info(f"No {strategy_type}-strategy exists, nothing to delete")
            return

        if STRATEGY_RUNNING_PATTERN in output_str:
            # The strategy is still applying. We deliberately do NOT abort or
            # force-delete a running strategy; it is left to settle on its own.
            get_logger().log_warning(f"{strategy_type}-strategy is still running and cannot be deleted; leaving it in place")
            return

        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"Deleted {strategy_type}-strategy successfully")

    @staticmethod
    def _parse_strategy_state(show_output: str) -> Optional[str]:
        """Extract the 'state' value from a dcmanager strategy show table.

        Args:
            show_output (str): Raw output of 'dcmanager <type>-strategy show'.

        Returns:
            Optional[str]: The strategy state, or None if the output holds no
                state row (which means no strategy of that type exists).
        """
        for line in show_output.splitlines():
            # Table rows are rendered as: | state | failed |
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) >= 3 and cells[1] == "state":
                return cells[2]
        return None

    def get_existing_strategies(self, strategy_types: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        """Find which dcmanager strategies currently exist.

        Args:
            strategy_types (Optional[List[str]]): Strategy command prefixes to
                check. Defaults to ALL_STRATEGY_TYPES.

        Returns:
            List[Tuple[str, str]]: (strategy_type, state) for each strategy that
                exists. Empty when the system controller has no strategy.
        """
        if strategy_types is None:
            strategy_types = ALL_STRATEGY_TYPES

        existing = []
        for strategy_type in strategy_types:
            cmd = self._wrap_command(f"dcmanager {strategy_type}-strategy show")
            output = "".join(self.ssh_connection.send(cmd))
            state = self._parse_strategy_state(output)
            if state is not None:
                existing.append((strategy_type, state))
        return existing

    def assert_no_strategy_exists(self, strategy_types: Optional[List[str]] = None) -> None:
        """Fail fast when a dcmanager strategy already exists on the system controller.

        Only one strategy may exist at a time, of any type, so a leftover
        strategy silently blocks every strategy-based test with an opaque
        "Return code was 1". Calling this first turns that into a single
        actionable error naming the offending strategy and how to clear it.

        Leftovers commonly survive a snapshot revert, since the strategy lives in
        the dcmanager database and is restored along with everything else.

        Args:
            strategy_types (Optional[List[str]]): Strategy command prefixes to
                check. Defaults to ALL_STRATEGY_TYPES.

        Raises:
            KeywordException: If any strategy exists.
        """
        existing = self.get_existing_strategies(strategy_types)

        if not existing:
            get_logger().log_info("Pre-flight: no pre-existing dcmanager strategy found")
            return

        found = "; ".join(f"'{strategy_type}' in state '{state}'" for strategy_type, state in existing)
        remediation = " && ".join(f"dcmanager {strategy_type}-strategy delete" for strategy_type, _ in existing)
        raise KeywordException("DcmanagerStrategyCleanupKeywords: a dcmanager strategy already exists, which blocks " f"creating a new one (only one strategy may exist at a time, of any type): {found}. " f"Clear it before running strategy tests: {remediation}")
