"""Factory-restore auto-restore log verification keywords.

Verifies completion of the local-site GRUB "Local Factory Restore" flow by
reading the subcloud auto-restore and restore-ansible logs over the OAM SSH
connection, with no DC manager involvement.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.files.file_keywords import FileKeywords

from config.configuration_manager import ConfigurationManager


class FactoryRestoreLogKeywords(BaseKeyword):
    """Verifies factory-restore completion from the subcloud auto-restore log.

    This is the authoritative check for the local-site, GRUB "Local Factory
    Restore" flow (no DC manager involvement during the restore). It reads the
    auto-restore log on the restored subcloud and confirms the success markers
    the factory auto-restore script writes on completion. All checks are purely
    node-local over the OAM SSH connection supplied by the caller.

    The log path and the expected success markers are read from the
    backup_restore configuration so they can be adjusted without code changes.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keyword with an SSH connection to the restored subcloud.

        Args:
            ssh_connection (SSHConnection): SSH connection to the subcloud (its
                OAM IP), established by the caller through the ACE connection
                framework (LabConnectionKeywords).
        """
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)
        self.config = ConfigurationManager.get_backup_restore_config().get_factory_restore_grub_config()

    def wait_for_oam_reachable(self, oam_ip: str, timeout: int = 600, polling_sleep_time: int = 15) -> bool:
        """Wait until the subcloud OAM IP answers a ping before any SSH is attempted.

        Right after a factory install the node reaches a login prompt well before
        its OAM interface is up, so SSH attempted immediately times out. This pings
        the OAM IP from the active controller (the DC-reachable vantage point) and
        polls until it responds, gating the SSH login that follows. IPv6 OAM IPs
        use ``ping6`` automatically.

        Args:
            oam_ip (str): The subcloud OAM IP to ping.
            timeout (int): Maximum number of seconds to wait for a ping reply.
            polling_sleep_time (int): Seconds to sleep between ping attempts.

        Returns:
            bool: True once the OAM IP responds to ping.

        Raises:
            TimeoutError: If the OAM IP does not respond within the timeout.
        """
        ping_cmd = "ping6" if ":" in oam_ip else "ping"
        controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_info(f"Waiting for subcloud OAM {oam_ip} to respond to {ping_cmd} (timeout {timeout}s)")

        def is_oam_pingable() -> bool:
            controller_ssh.send(f"{ping_cmd} -c 3 -W 2 {oam_ip}")
            reachable = controller_ssh.get_return_code() == 0
            get_logger().log_info(f"{ping_cmd} {oam_ip} reachable={reachable}")
            return reachable

        validate_equals_with_retry(is_oam_pingable, True, f"subcloud OAM {oam_ip} responds to {ping_cmd}", timeout=timeout, polling_sleep_time=polling_sleep_time)
        return True

    def wait_for_ssh_reachable(self, timeout: int = 300, polling_sleep_time: int = 15) -> bool:
        """Wait until the subcloud OAM SSH accepts a connection.

        A successful ping does not guarantee sshd is accepting connections yet, so
        a login attempted on the first ping success can still be refused/time out.
        This polls the OAM SSH connection (established through the ACE connection
        framework with the factory credentials) until it connects, so a transient
        refusal right after the node comes up does not fail the step.

        Args:
            timeout (int): Maximum number of seconds to wait for SSH to connect.
            polling_sleep_time (int): Seconds to sleep between connect attempts.

        Returns:
            bool: True once the SSH connection is established.

        Raises:
            TimeoutError: If SSH does not connect within the timeout.
        """
        get_logger().log_info(f"Waiting for subcloud OAM SSH to accept connections (timeout {timeout}s)")

        def is_ssh_up() -> bool:
            reachable = self.ssh_connection.is_reachable()
            get_logger().log_info(f"subcloud OAM SSH reachable={reachable}")
            return reachable

        validate_equals_with_retry(is_ssh_up, True, "subcloud OAM SSH accepts connections", timeout=timeout, polling_sleep_time=polling_sleep_time)
        return True

    def wait_for_restore_ansible_complete(self, timeout: int = 3600, polling_sleep_time: int = 30) -> bool:
        """Wait for the restore/bootstrap ansible to finish before verifying the log.

        The node reaches a login prompt while the optimized-restore ansible is
        still running (e.g. 'TASK [optimized-restore/restore-configuration : Read
        current IP addresses]'), so the auto-restore success marker is not written
        yet. This polls the restore ansible log for its ``PLAY RECAP`` localhost
        line and treats the restore as complete only when that line reports
        ``unreachable=0`` and ``failed=0``. A recap with a non-zero ``failed`` or
        ``unreachable`` count fails the step immediately (fail fast) with the recap
        line, rather than waiting out the full timeout.

        Args:
            timeout (int): Maximum number of seconds to wait for the restore to
                finish (a full restore is long; default 1 hour).
            polling_sleep_time (int): Seconds to sleep between log polls.

        Returns:
            bool: True once a PLAY RECAP with unreachable=0 and failed=0 appears.

        Raises:
            TimeoutError: If no completed recap appears within the timeout.
            ValidationFailureError: If the recap reports a non-zero failed or
                unreachable count.
        """
        log_path = self.config.get_restore_ansible_log_path()
        get_logger().log_info(f"Waiting for restore ansible to complete, polling PLAY RECAP in {log_path} (timeout {timeout}s)")

        def get_recap_state() -> str:
            recap_line = self._get_last_play_recap_line(log_path)
            if not recap_line:
                get_logger().log_info("Restore ansible PLAY RECAP not present yet; restore still running")
                return "pending"
            get_logger().log_info(f"Restore ansible PLAY RECAP: {recap_line}")
            unreachable = self._parse_recap_counter(recap_line, "unreachable")
            failed = self._parse_recap_counter(recap_line, "failed")
            if unreachable == 0 and failed == 0:
                return "complete"
            get_logger().log_error(f"Restore ansible reported failures (unreachable={unreachable}, failed={failed}): {recap_line}")
            return "failed"

        validate_equals_with_retry(get_recap_state, "complete", "restore ansible PLAY RECAP shows unreachable=0 and failed=0", timeout=timeout, polling_sleep_time=polling_sleep_time, failure_values=["failed"])
        get_logger().log_info("Restore ansible completed successfully (unreachable=0, failed=0).")
        return True

    def _get_last_play_recap_line(self, log_path: str) -> str:
        """Return the most recent ansible PLAY RECAP localhost summary line.

        Greps the restore ansible log for the per-host recap line (the one that
        carries the ok=/changed=/unreachable=/failed= counters) and returns the
        last occurrence, so a restore that logged earlier recaps is read at its
        final state.

        Args:
            log_path (str): Path to the restore ansible log on the subcloud.

        Returns:
            str: The last matching recap line, or an empty string if none is
            present yet.
        """
        output = self.ssh_connection.send(f"grep -E 'unreachable=[0-9]+ +failed=[0-9]+' {log_path} 2>/dev/null | tail -n 1 || true")
        lines = [line.strip() for line in output if line.strip()] if isinstance(output, list) else []
        return lines[-1] if lines else ""

    def _parse_recap_counter(self, recap_line: str, counter: str) -> int:
        """Parse a single ``name=value`` counter out of an ansible recap line.

        Args:
            recap_line (str): A PLAY RECAP localhost line, e.g.
                'localhost : ok=274 changed=143 unreachable=0 failed=0 ...'.
            counter (str): The counter name to extract (e.g. "failed").

        Returns:
            int: The counter value, or -1 if the counter is not present (treated
            as not-yet-complete rather than success).
        """
        for token in recap_line.split():
            if token.startswith(f"{counter}="):
                value = token.split("=", 1)[1]
                return int(value) if value.isdigit() else -1
        return -1

    def wait_for_controller_available(self, host_name: str = "controller-0", timeout: int = 2800) -> bool:
        """Wait for a controller to be administrative=unlocked, operational=enabled, availability=available.

        Reuses the established host-state wait (SystemHostLockKeywords), which
        polls 'system host-list' until the host reports unlocked/enabled/available
        (and clears config-out-of-date alarms). For this simplex subcloud the
        caller passes controller-0.

        Args:
            host_name (str): The controller to wait on. Defaults to "controller-0".
            timeout (int): Maximum number of seconds to wait.

        Returns:
            bool: True once the controller reaches unlocked/enabled/available.

        Raises:
            AssertionError: If the controller does not reach the expected state
                within the timeout.
        """
        get_logger().log_info(f"Waiting for {host_name} to be unlocked/enabled/available (timeout {timeout}s)")
        is_unlocked = SystemHostLockKeywords(self.ssh_connection).wait_for_host_unlocked(host_name, unlock_wait_timeout=timeout)
        validate_equals(is_unlocked, True, f"{host_name} reached unlocked/enabled/available")
        return True

    def source_platform_openrc(self) -> bool:
        """Source /etc/platform/openrc on the restored subcloud.

        Confirms the restored node has a usable platform environment before the
        log is inspected. This is purely node-local over the OAM SSH and does not
        touch the DC manager.

        Returns:
            bool: True if the platform openrc sourced successfully.

        Raises:
            AssertionError: If sourcing the platform openrc fails.
        """
        get_logger().log_info("Sourcing /etc/platform/openrc on the restored subcloud")
        self.ssh_connection.send(source_openrc("true"))
        self.validate_success_return_code(self.ssh_connection)
        return True

    def verify_factory_restore_complete(self, timeout: int = 600, polling_sleep_time: int = 15) -> bool:
        """Verify the auto-restore log shows a successful factory restore.

        Polls the configured auto-restore log on the subcloud until every
        configured success marker is present, or the timeout elapses. This is
        the sole authoritative pass criterion for the local-site GRUB
        factory-restore flow.

        Polling (rather than a single read) is required because the subcloud
        runs ``system restore-complete`` in its own retry loop (up to ~15
        attempts) AFTER the controller first reports
        unlocked/enabled/available: the controller can still be
        ``available/degraded`` when this step begins, so the
        "restore-complete completed successfully" marker is written only once
        that loop converges. A one-shot read here failed intermittently even
        though the restore succeeded moments later.

        Args:
            timeout (int): Maximum number of seconds to wait for all success
                markers to appear (covers the subcloud's restore-complete retry
                loop). Defaults to 600 (10 minutes).
            polling_sleep_time (int): Seconds to sleep between log reads.

        Returns:
            bool: True once all success markers are present in the log.

        Raises:
            TimeoutError: If the success markers do not all appear within the
                timeout.
        """
        log_path = self.config.get_auto_restore_log_path()
        success_markers = self.config.get_success_markers()
        get_logger().log_info(f"Verifying factory restore completion from {log_path} (polling up to {timeout}s)")

        def all_markers_present() -> bool:
            log_lines = self.file_keywords.read_file_with_sudo(log_path)
            log_text = "\n".join(log_lines)
            missing = [marker for marker in success_markers if marker not in log_text]
            if missing:
                get_logger().log_info(f"auto-restore log missing success marker(s) {missing}; restore-complete not finished yet")
                return False
            return True

        validate_equals_with_retry(all_markers_present, True, "auto-restore log contains all success markers", timeout=timeout, polling_sleep_time=polling_sleep_time)
        get_logger().log_info("auto-restore log confirms factory restore completed successfully.")
        return True
