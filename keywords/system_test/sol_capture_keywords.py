import os
import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection

# Settle time after launching 'sol activate' before verifying the session attached.
SOL_SETTLE_SECONDS = 5

# iDRAC-reset tuning. start() resets every BMC up front (mc reset cold) so all SOL
# sessions begin from a guaranteed-clean state, then:
#  - waits a minimum settle before probing (the BMC is unreachable while it reboots),
#  - polls a real ipmitool command ('chassis power status') until it succeeds, because
#    the BMC IP can respond before ipmitool commands work again.
IDRAC_RESET_MIN_WAIT_SECONDS = 360   # minimum 6 min before probing BMCs after reset
IDRAC_RESET_POLL_INTERVAL_SECONDS = 20
IDRAC_RESET_POLL_TIMEOUT_SECONDS = 300  # additional time to poll for BMC to become functional


class SolCaptureKeywords:
    """Capture BMC Serial-Over-LAN (SOL) console output for a set of nodes.

    Used by the power system tests (dead office recovery, controllers power
    cycle) to record the full firmware -> bootloader -> kernel boot on every
    node under test. This is the only way to see an early-boot stall, because a
    node that hangs before the kernel starts writes nothing to its own
    /var/log.

    All ipmitool commands run on the jump server (which has BMC reachability).
    Only one SOL session is allowed per BMC, and a stale/dead session blocks new
    ones, so start() resets every BMC up front (mc reset cold) to guarantee a clean
    SOL state before opening sessions. Capture is best-effort: a failure to
    start/stop SOL on one node is logged but never aborts the caller (the test
    result must not depend on the debug capture).
    """

    def __init__(self, jump_ssh: SSHConnection, nodes: list, bm_password: str, run_id: str) -> None:
        """Initialize the SOL capture helper.

        Args:
            jump_ssh (SSHConnection): SSH connection to the jump server.
            nodes (list): Lab node objects (each exposes get_name/get_bm_ip/get_bm_username).
            bm_password (str): BMC password shared by all nodes.
            run_id (str): Unique tag for this run, used in the remote log file names.
        """
        self.jump_ssh = jump_ssh
        self.nodes = nodes
        self.bm_password = bm_password
        self.run_id = run_id
        self.remote_dir = "/tmp"

    def get_remote_log_path(self, node_name: str) -> str:
        """Get the remote (jump server) SOL log path for a node.

        Args:
            node_name (str): Node name.

        Returns:
            str: Absolute path of the SOL log file on the jump server.
        """
        return f"{self.remote_dir}/sol_{node_name}_{self.run_id}.log"

    def _ipmitool_prefix(self, bm_ip: str, bm_username: str) -> str:
        """Build the common ipmitool command prefix for a BMC.

        Args:
            bm_ip (str): BMC IP address.
            bm_username (str): BMC username.

        Returns:
            str: The ipmitool command prefix up to (but excluding) the subcommand.
        """
        return f"ipmitool -I lanplus -H {bm_ip} -U {bm_username} -P {self.bm_password}"

    def _launch_sol(self, prefix: str, remote_log: str) -> None:
        """Launch a detached SOL 'sol activate' for one BMC.

        No force-clear is needed because reset_bmcs() already cleared any session.
        'sol activate' exits on stdin EOF, so feed it from 'tail -f /dev/null' (stdin
        never closes) and detach with setsid so it survives the SSH channel that
        launched it. CRITICAL: redirect the OUTER backgrounded command's
        stdin/stdout/stderr away from the SSH exec channel (</dev/null >/dev/null 2>&1)
        so the channel reaches EOF and the framework's send() returns immediately.

        Args:
            prefix (str): ipmitool command prefix for this BMC.
            remote_log (str): Remote SOL log path to write to.
        """
        self.jump_ssh.send(f"setsid bash -c 'tail -f /dev/null | {prefix} sol activate > {remote_log} 2>&1' </dev/null >/dev/null 2>&1 &")

    def _bmc_is_responsive(self, prefix: str) -> bool:
        """Return True if the BMC answers a real ipmitool command.

        Uses 'chassis power status' rather than ping: after an iDRAC reset the BMC
        IP may respond while ipmitool commands still fail, so a functional command
        is the reliable readiness check.

        Args:
            prefix (str): ipmitool command prefix for this BMC.

        Returns:
            bool: True if 'chassis power status' returns the expected output.
        """
        result = self.jump_ssh.send(f"{prefix} chassis power status 2>&1")
        if isinstance(result, list):
            result = "".join(result)
        return "Chassis Power is" in (result or "")

    def _sol_is_capturing(self, bm_ip: str, remote_log: str) -> bool:
        """Return True if the SOL session is actually attached and healthy.

        Healthy means: a live ipmitool 'sol activate' process exists for this BMC
        AND the log does not contain the BMC rejection strings ("already active" /
        "session closed by BMC"). This is checked right after launch so a failed
        attach is caught and retried BEFORE the power test proceeds (not discovered
        afterwards).

        Args:
            bm_ip (str): BMC IP address.
            remote_log (str): Remote SOL log path.

        Returns:
            bool: True if the session is attached and not rejected.
        """
        result = self.jump_ssh.send(
            f"if pgrep -f 'ipmitool.* -H {bm_ip} .*sol activate' >/dev/null 2>&1 "
            f"&& ! grep -qiE 'already active|session closed by BMC' {remote_log} 2>/dev/null; "
            f"then echo SOL_UP; else echo SOL_DOWN; fi"
        )
        if isinstance(result, list):
            result = "".join(result)
        return "SOL_UP" in (result or "")

    def reset_bmcs(self) -> None:
        """Reset all BMCs and wait until each is functional again.

        Call this BEFORE the power cycle (and before start()). 'mc reset cold'
        every BMC in parallel so they begin from a clean state (any stale SOL
        session is cleared), wait a minimum settle, then poll each BMC with a real
        command ('chassis power status') until it responds. Resetting a BMC does
        NOT power off its host. Best-effort: never aborts the caller.
        """
        targets = self._targets()
        if not targets:
            return

        get_logger().log_info(f"SOL capture: iDRAC-resetting all {len(targets)} BMC(s)")
        for node_name, bm_ip, prefix, _ in targets:
            try:
                self.jump_ssh.send(f"{prefix} mc reset cold 2>/dev/null")
                get_logger().log_info(f"SOL capture: issued 'mc reset cold' to {node_name} (BMC {bm_ip})")
            except Exception as e:
                get_logger().log_info(f"SOL capture: failed to reset BMC {bm_ip}: {e}")

        get_logger().log_info(f"SOL capture: waiting {IDRAC_RESET_MIN_WAIT_SECONDS}s minimum for BMCs to reboot...")
        time.sleep(IDRAC_RESET_MIN_WAIT_SECONDS)

        for node_name, bm_ip, prefix, _ in targets:
            waited = 0
            while waited < IDRAC_RESET_POLL_TIMEOUT_SECONDS:
                if self._bmc_is_responsive(prefix):
                    get_logger().log_info(f"SOL capture: BMC {bm_ip} ({node_name}) is responsive")
                    break
                time.sleep(IDRAC_RESET_POLL_INTERVAL_SECONDS)
                waited += IDRAC_RESET_POLL_INTERVAL_SECONDS
            else:
                get_logger().log_info(f"SOL capture: WARNING - BMC {bm_ip} ({node_name}) not responsive after reset")

    def _targets(self) -> list:
        """Build the list of (node_name, bm_ip, prefix, remote_log) for nodes with a BMC.

        Returns:
            list: One tuple per node that has a usable BMC IP.
        """
        targets = []
        for node in self.nodes:
            node_name = node.get_name()
            bm_ip = node.get_bm_ip()
            bm_username = node.get_bm_username()
            if not node_name or not bm_ip or bm_ip == "None":
                get_logger().log_info(f"SOL capture: skipping {node_name} (no BMC IP)")
                continue
            prefix = self._ipmitool_prefix(bm_ip, bm_username)
            targets.append((node_name, bm_ip, prefix, self.get_remote_log_path(node_name)))
        return targets

    def start(self) -> None:
        """Open a SOL session on every node and verify it attached.

        Call this AFTER the power cycle (with the hosts already powering on) so the
        BMC's own SOL session-close during the power transition has already happened
        and we attach to the fresh session in time to capture the boot. Assumes the
        BMCs were reset via reset_bmcs() first, so there is no stale session to
        fight. Best-effort per node; verifies attach once (no retry).
        """
        for node_name, bm_ip, prefix, remote_log in self._targets():
            try:
                self._launch_sol(prefix, remote_log)
                # Verify once (no retry) that the session attached, so a failure is visible
                # immediately rather than discovered as a tiny log after the whole test.
                time.sleep(SOL_SETTLE_SECONDS)
                if self._sol_is_capturing(bm_ip, remote_log):
                    get_logger().log_info(f"SOL capture started for {node_name} (BMC {bm_ip}) -> {remote_log}")
                else:
                    get_logger().log_info(f"SOL capture: WARNING - session did not attach for {node_name} (BMC {bm_ip}); capture may be unavailable (LC log is the fallback)")
            except Exception as e:
                get_logger().log_info(f"SOL capture: failed to start for {node_name}: {e}")

    def stop(self) -> None:
        """Stop SOL capture for every node by deactivating each SOL session.

        Best-effort per node; never raises.
        """
        for node in self.nodes:
            node_name = node.get_name()
            bm_ip = node.get_bm_ip()
            bm_username = node.get_bm_username()
            if not node_name or not bm_ip or bm_ip == "None":
                continue

            prefix = self._ipmitool_prefix(bm_ip, bm_username)
            try:
                # Kill the ipmitool SOL reader for this BMC first. Match on the BMC IP, which
                # is present in the ipmitool process command line (the log-path redirect is
                # NOT, since the shell consumes it). Killing ipmitool makes its 'tail -f'
                # stdin feeder exit on SIGPIPE. Then release the SOL session on the BMC.
                self.jump_ssh.send(f"pkill -f 'ipmitool.* -H {bm_ip} .*sol activate' 2>/dev/null")
                self.jump_ssh.send(f"{prefix} sol deactivate 2>/dev/null")
                get_logger().log_info(f"SOL capture stopped for {node_name} (BMC {bm_ip})")
            except Exception as e:
                get_logger().log_info(f"SOL capture: failed to stop for {node_name}: {e}")

    def collect(self, local_dir: str) -> list:
        """Copy each node's SOL log from the jump server into a local directory.

        Reads the remote log content over the existing jump SSH connection and
        writes it to '<local_dir>/sol_<node>_<run_id>.log'. Best-effort per node.

        Args:
            local_dir (str): Local directory to write the SOL logs into.

        Returns:
            list: Local paths of the SOL log files that were written.
        """
        os.makedirs(local_dir, exist_ok=True)
        written = []
        for node in self.nodes:
            node_name = node.get_name()
            bm_ip = node.get_bm_ip()
            if not node_name or not bm_ip or bm_ip == "None":
                continue

            remote_log = self.get_remote_log_path(node_name)
            local_log = os.path.join(local_dir, f"sol_{node_name}_{self.run_id}.log")
            try:
                content = self.jump_ssh.send(f"cat {remote_log} 2>/dev/null")
                if isinstance(content, list):
                    content = "".join(content)
                with open(local_log, "w") as f:
                    f.write(content if content else "")
                line_count = content.count("\n") if content else 0
                get_logger().log_info(f"SOL log collected for {node_name}: {local_log} ({line_count} lines)")
                written.append(local_log)
            except Exception as e:
                get_logger().log_info(f"SOL capture: failed to collect for {node_name}: {e}")
        return written
