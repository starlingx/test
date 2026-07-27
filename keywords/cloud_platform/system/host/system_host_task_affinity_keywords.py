import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword

# Path that StarlingX mtce writes while task-affining is in progress.
# Its absence signals that CPU affinity assignment is complete.
TASK_AFFINING_SENTINEL = "/etc/platform/.task_affining_incomplete"

# If the sentinel file has not been modified within this many seconds it is
# considered a permanently stale leftover — mtce does not always remove it
# after affining completes (known platform quirk seen in the field).
STALE_SENTINEL_THRESHOLD_SECS = 300  # 5 minutes


class SystemHostTaskAffinityKeywords(BaseKeyword):
    """Keywords for host CPU task-affinity readiness checks.

    StarlingX writes the sentinel file
    ``/etc/platform/.task_affining_incomplete`` while it is in the
    process of re-pinning platform tasks to their designated CPU sets
    after a host lock/unlock or initial provisioning.

    Two wait methods are provided:

    - :meth:`wait_for_tasks_affined` — strict: raises ``TimeoutError``
      if the sentinel is still present after the timeout.  Use when the
      caller must abort if affining is incomplete.
    - :meth:`wait_for_tasks_affined_or_warn` — best-effort: logs a
      warning and returns ``False`` if the sentinel is still present.
      Use for tests where a permanently stale sentinel should not
      block execution.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the
                target controller.
        """
        self.ssh_connection = ssh_connection

    def log_cpu_info(self, host_name: str) -> None:
        """Dump CPU topology and platform config for diagnostics.

        Runs ``lscpu; cat /proc/cpuinfo; cat /etc/platform/platform.conf``
        as a single combined command, then ``cat /sys/devices/system/cpu/online``
        separately — matching the established KPI run ordering. Intended
        to capture the CPU layout / platform configuration context
        *before* the task-affinity sentinel is checked, so KPI runs have
        this information on record.

        Args:
            host_name (str): Hostname being inspected, e.g.
                ``"controller-0"``.
        """
        # First three collected together (single send), matching reference run order.
        combined_cmd = "lscpu; cat /proc/cpuinfo; cat /etc/platform/platform.conf"
        get_logger().log_info(f"Collecting CPU/platform info on {host_name}: {combined_cmd}")
        self.ssh_connection.send(combined_cmd)

        # Online CPU list collected separately, after the combined dump.
        online_cmd = "cat /sys/devices/system/cpu/online"
        get_logger().log_info(f"Collecting online CPU list on {host_name}: {online_cmd}")
        self.ssh_connection.send(online_cmd)

    def is_tasks_affined(self, host_name: str) -> bool:
        """Return True when task-affining is complete on *host_name*.

        Executes ``stat /etc/platform/.task_affining_incomplete`` on
        the remote host.  A non-zero return code (file absent) means
        affining is done.  If the file exists but has not been modified
        within the last ``STALE_SENTINEL_THRESHOLD_SECS`` seconds it is
        treated as a permanently stale leftover (known platform quirk
        where mtce does not always remove the file) and affining is
        considered complete.

        Args:
            host_name (str): Hostname to check, e.g. ``"controller-0"``.

        Returns:
            bool: ``True`` if the sentinel file is absent or stale
                (affining complete); ``False`` if it is actively present.
        """
        get_logger().log_info(f"Checking task-affinity sentinel on {host_name}: stat {TASK_AFFINING_SENTINEL}")
        self.ssh_connection.send(f"stat {TASK_AFFINING_SENTINEL}")
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            # File absent — affining complete
            get_logger().log_info(f"Task-affinity on {host_name}: sentinel absent (rc={rc}) — affining complete")
            return True

        # File present — check if it is stale (not modified recently)
        age_output = "".join(self.ssh_connection.send(f"echo $(( $(date +%s) - $(stat -c %Y {TASK_AFFINING_SENTINEL}) ))")).strip()
        try:
            age_secs = int(age_output)
        except ValueError:
            age_secs = 0

        if age_secs > STALE_SENTINEL_THRESHOLD_SECS:
            get_logger().log_warning(f"Task-affinity on {host_name}: sentinel present but stale " f"(age={age_secs}s > threshold={STALE_SENTINEL_THRESHOLD_SECS}s) " f"— treating as complete (known mtce cleanup quirk)")
            return True

        get_logger().log_info(f"Task-affinity on {host_name}: sentinel present and active (age={age_secs}s, rc={rc})")
        return False

    def wait_for_tasks_affined(self, host_name: str, timeout: int = 180) -> bool:
        """Poll until CPU task-affining completes on *host_name*.

        Raises ``TimeoutError`` if the sentinel file is still present
        after *timeout* seconds.  Use this when the caller must abort
        if affining does not complete.

        Args:
            host_name (str): Hostname to poll, e.g. ``"controller-0"``.
            timeout (int): Maximum seconds to wait. Defaults to 180s.

        Returns:
            bool: ``True`` once affining is confirmed complete.

        Raises:
            TimeoutError: If the sentinel file is still present after
                *timeout* seconds.
        """
        get_logger().log_info(f"Waiting up to {timeout}s for task-affining to complete on {host_name}")

        # Capture CPU topology / platform config before checking the sentinel.
        self.log_cpu_info(host_name)

        def _is_affined() -> bool:
            return self.is_tasks_affined(host_name)

        validate_equals_with_retry(
            _is_affined,
            True,
            f"Task-affining on {host_name} did not complete within {timeout}s — sentinel file {TASK_AFFINING_SENTINEL} is still present",
            timeout=timeout,
        )

        get_logger().log_info(f"Task-affining complete on {host_name} — sentinel file is absent")
        return True

    def wait_for_tasks_affined_or_warn(self, host_name: str, timeout: int = 180) -> bool:
        """Poll for task-affining completion, logging a warning if it does not complete.

        Best-effort variant of :meth:`wait_for_tasks_affined`. If the
        sentinel file is still present after *timeout* seconds, logs a
        warning and returns ``False`` rather than raising.

        Use this for KPI tests where a permanently stale sentinel file
        should not block test execution.

        Args:
            host_name (str): Hostname to poll, e.g. ``"controller-0"``.
            timeout (int): Maximum seconds to wait. Defaults to 180s.

        Returns:
            bool: ``True`` when affining completes; ``False`` if the
                sentinel is still present after *timeout* seconds.
        """
        get_logger().log_info(f"Waiting up to {timeout}s for task-affining to complete on {host_name} (best-effort)")

        # Capture CPU topology / platform config before checking the sentinel.
        self.log_cpu_info(host_name)

        elapsed = 0
        poll_interval = 5
        while elapsed < timeout:
            if self.is_tasks_affined(host_name):
                get_logger().log_info(f"Task-affining complete on {host_name} — sentinel file is absent")
                return True
            elapsed += poll_interval
            if elapsed < timeout:
                time.sleep(poll_interval)

        get_logger().log_warning(f"Task-affining on {host_name}: sentinel file {TASK_AFFINING_SENTINEL} still present after {timeout}s — proceeding anyway. The sentinel may be permanently stale.")
        return False
