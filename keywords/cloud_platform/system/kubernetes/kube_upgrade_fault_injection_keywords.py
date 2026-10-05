import time
from typing import Callable, Sequence

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_str_contains_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.pkill.pkill_keywords import PkillKeywords


class KubeUpgradeFaultInjectionKeywords(BaseKeyword):
    """Fault-injection keywords for Kubernetes/combined upgrade scenarios.

    Provides reusable "repeatedly disrupt a process while polling for a
    failure/abort condition" loops that are shared across manual, orchestrated
    kube-upgrade, and combined (sw-deploy) upgrade fault-injection tests. The
    loops tolerate transient failures from both the disruption command (the
    target process may not exist between respawns) and the status query (the
    system may be temporarily unresponsive during the disruption).

    These keywords follow the success-or-exception contract: the polling
    '*_until_*' methods return None when the expected condition is reached and
    raise TimeoutError otherwise. The single-shot 'kill_process' helper applies
    one disruption and does not poll.
    """

    # Remote path where the background pkill loop records its PID for cleanup.
    BACKGROUND_PKILL_PID_FILE = "/tmp/kube_fault_injection_pkill.pid"

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize KubeUpgradeFaultInjectionKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.pkill_keywords = PkillKeywords(ssh_connection)

    def kill_process(self, process_pattern: str) -> None:
        """Kill processes matching a pattern once (SIGTERM via pkill pattern match) as sudo.

        A single-shot disruption helper for priming a fault before a step begins.

        Args:
            process_pattern (str): Process pattern to kill (e.g. '[k]ubeadm', 'sysinv-agent').
        """
        get_logger().log_info(f"Killing process matching '{process_pattern}'")
        self.pkill_keywords.pkill_by_pattern(process_pattern, send_as_sudo=True)

    def kill_process_until_state(self, process_pattern: str, state_getter: Callable[[], str], target_states: Sequence[str], timeout: int = 600, polling_interval: int = 1, signal: str = None) -> None:
        """Kill a process each poll until a strategy/upgrade state matches a target.

        Continuously kills the process matching process_pattern (via pkill) and
        polls state_getter until its returned value is one of target_states.
        Works with any strategy whose state can be read through a zero-argument
        getter (e.g. sw-deploy-strategy 'state' or kube-upgrade-strategy
        'apply-result').

        Args:
            process_pattern (str): Process pattern to kill (e.g. '[k]ubeadm', '/bin/etcd', 'sysinv-agent').
            state_getter (Callable[[], str]): Zero-argument callable returning the current state to evaluate.
            target_states (Sequence[str]): States that indicate the desired failure/abort condition was reached.
            timeout (int): Maximum wait time in seconds.
            polling_interval (int): Seconds between kill/poll iterations.
            signal (str): Optional signal to send to pkill (e.g. '9' for SIGKILL). Defaults to SIGTERM when None; use '9' for processes that ignore SIGTERM during shutdown (e.g. etcd).

        Raises:
            TimeoutError: If no target state is reached within the timeout.
        """
        self._disrupt_until_state(lambda: self.pkill_keywords.pkill_by_pattern(process_pattern, send_as_sudo=True, signal=signal), f"Killing process matching '{process_pattern}'", state_getter, target_states, timeout, polling_interval)

    def stop_process_until_state(self, process_name: str, state_getter: Callable[[], str], target_states: Sequence[str], timeout: int = 600, polling_interval: int = 1) -> None:
        """Send SIGSTOP to a process each poll until a strategy/upgrade state matches a target.

        Args:
            process_name (str): Exact process name to send the STOP signal to (e.g. 'kubeadm').
            state_getter (Callable[[], str]): Zero-argument callable returning the current state to evaluate.
            target_states (Sequence[str]): States that indicate the desired failure/abort condition was reached.
            timeout (int): Maximum wait time in seconds.
            polling_interval (int): Seconds between stop/poll iterations.

        Raises:
            TimeoutError: If no target state is reached within the timeout.
        """
        self._disrupt_until_state(lambda: self.pkill_keywords.pkill_signal("STOP", process_name), f"Sending STOP signal to '{process_name}'", state_getter, target_states, timeout, polling_interval)

    def kill_process_until_host_upgrade_status(self, process_pattern: str, hostname: str, expected_status: str, timeout: int = 600, polling_interval: int = 1, signal: str = None) -> None:
        """Kill a process each poll until a host's kube upgrade status matches.

        Continuously kills the process matching process_pattern and polls
        'system kube-host-upgrade-list' until the target host's status equals
        expected_status. Suitable for per-host fault injection during the
        control-plane or kubelet upgrade phases.

        Args:
            process_pattern (str): Process pattern to kill (e.g. '/bin/etcd', 'sysinv-agent').
            hostname (str): Target hostname whose upgrade status is monitored.
            expected_status (str): Status value indicating the desired failure (e.g. 'upgrading-control-plane-failed').
            timeout (int): Maximum wait time in seconds.
            polling_interval (int): Seconds between kill/poll iterations.
            signal (str): Optional signal to send to pkill (e.g. '9' for SIGKILL). Defaults to SIGTERM when None; use '9' for processes that ignore SIGTERM during shutdown (e.g. etcd).

        Raises:
            TimeoutError: If the expected status is not reached within the timeout.
        """
        kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(self.ssh_connection)

        def get_host_status() -> str:
            return kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(hostname).get_status()

        self.kill_process_until_state(process_pattern, get_host_status, [expected_status], timeout=timeout, polling_interval=polling_interval, signal=signal)

    def kill_process_until_log_marker(self, process_pattern: str, log_path: str, log_marker: str, timeout: int = 600, polling_interval: int = 5, signal: str = None) -> None:
        """Continuously kill a process until a marker line appears in a log file.

        Starts a detached background loop that kills the matching process every
        second without pausing, then reads log_path for log_marker until it is
        found. The log's line count is captured up front and only lines appended
        after that point are searched, so a failure line from an earlier run
        cannot cause a false match. The background killer is always stopped
        afterwards.

        Use this instead of the API/CLI-status variants when the killed process
        is required to serve that status (e.g. killing etcd makes
        'sw-manager sw-deploy-strategy show' and 'system kube-host-upgrade-list'
        unable to return meaningful state, because they depend on the Kubernetes
        API which depends on etcd). Reading a local log file does not depend on
        the killed process, so the failure can be detected reliably; the caller
        should confirm the failed state via a normal status query only after this
        method returns and the process has recovered.

        Args:
            process_pattern (str): Process pattern to kill (e.g. '/usr/bin/[e]tcd').
            log_path (str): Absolute path to the log file to read (e.g. '/var/log/sysinv.log').
            log_marker (str): Substring that indicates the desired failure occurred.
            timeout (int): Maximum wait time in seconds.
            polling_interval (int): Seconds between log reads.
            signal (str): Optional signal to send to pkill (e.g. '9' for SIGKILL). Defaults to SIGTERM when None; use '9' for processes that ignore SIGTERM during shutdown (e.g. etcd).

        Raises:
            Exception: If the marker does not appear within the timeout.
        """
        file_keywords = FileKeywords(self.ssh_connection)
        pid_file = self.BACKGROUND_PKILL_PID_FILE
        # Bookmark the current end of the log so only lines appended after this
        # method starts are searched. A line offset (rather than a timestamp range)
        # is used because it does not depend on the log's timestamp format, and it
        # prevents a marker written by an earlier run from causing a false match.
        start_line = file_keywords.get_file_line_count(log_path)
        get_logger().log_info(f"Searching {log_path} for '{log_marker}' after line {start_line}")
        get_logger().log_info(f"Starting continuous background kill of '{process_pattern}' (signal={signal or 'TERM'})")
        self.pkill_keywords.start_background_pkill_loop(process_pattern, pid_file=pid_file, interval=1, signal=signal)

        def get_marker_lines() -> str:
            """Return log lines appended after the bookmark that contain the marker.

            Returns:
                str: The matching log lines joined by newlines, or an empty string when none match yet.
            """
            lines = file_keywords.read_file_from_line(log_path, start_line, log_marker)
            return "\n".join(lines)

        try:
            validate_str_contains_with_retry(
                get_marker_lines,
                log_marker,
                f"'{log_marker}' appears in {log_path} after line {start_line}",
                timeout=timeout,
                polling_sleep_time=polling_interval,
            )
        finally:
            get_logger().log_info(f"Stopping continuous background kill of '{process_pattern}'")
            self.pkill_keywords.stop_background_pkill_loop(pid_file)

    def _disrupt_until_state(self, disrupt_action: Callable[[], None], disrupt_log_message: str, state_getter: Callable[[], str], target_states: Sequence[str], timeout: int, polling_interval: int) -> None:
        """Run a disruption action each poll until state_getter returns a target state.

        Args:
            disrupt_action (Callable[[], None]): The disruption to apply each iteration (kill or stop a process).
            disrupt_log_message (str): Message logged before each disruption attempt.
            state_getter (Callable[[], str]): Zero-argument callable returning the current state to evaluate.
            target_states (Sequence[str]): States that indicate the desired condition was reached.
            timeout (int): Maximum wait time in seconds.
            polling_interval (int): Seconds between iterations.

        Raises:
            TimeoutError: If no target state is reached within the timeout.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                get_logger().log_info(disrupt_log_message)
                disrupt_action()
            # Disruption is best-effort: the target process may not exist between
            # respawns, so a pkill/ssh failure here is expected and retried next iteration.
            except (KeywordException, ConnectionRefusedError) as e:
                get_logger().log_info(f"Disruption action failed: {e}, retrying")
            try:
                state = state_getter()
                get_logger().log_info(f"Current state: {state}")
                if state in target_states:
                    return
            except (KeywordException, ConnectionRefusedError):
                # Status query can fail transiently while the system cycles hosts
                # (lock/unlock/swact); retry rather than aborting the loop.
                get_logger().log_info("Status query failed during polling, retrying")
            if time.time() + polling_interval < end_time:
                time.sleep(polling_interval)

        get_logger().log_error(f"Timed out after {timeout}s waiting for state in {list(target_states)}")
        raise TimeoutError(f"Timed out after {timeout}s waiting for one of {list(target_states)}")
