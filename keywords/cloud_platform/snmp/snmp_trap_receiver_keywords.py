"""Keywords for a local SNMP trap receiver on the test runner.

Runs ``snmptrapd`` directly on the test runner (via subprocess, like the
existing SNMP get/walk helpers) to capture traps emitted by the platform's
SNMP trap-subagent in response to a fault-management alarm.

The receiver is per-session and collision-safe for concurrent runs on the
same runner:

    * a free high UDP port is chosen by the OS (bind to port 0);
    * the systemd transient unit, capture file and config file names are
      made unique with the process id and a random token;
    * the receiver address the controller should target is derived at
      runtime from ``ip route get <controller_oam_ip>`` (the ``src`` field),
      so no static IP is reserved.
"""

import os
import secrets
import socket
import subprocess
import time

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword


class SnmpTrapReceiverKeywords(BaseKeyword):
    """Start, poll and stop a local snmptrapd trap receiver on the runner."""

    def __init__(self):
        """Constructor.

        Allocates per-session unique names and a free UDP port so multiple
        receivers can run on the same runner without colliding.
        """
        session_token = f"{os.getpid()}-{secrets.token_hex(3)}"
        self.unit_name = f"snmp-trap-receiver-{session_token}"
        self.capture_file = f"/tmp/snmp-trap-{session_token}.log"
        self.conf_file = f"/tmp/snmp-trap-{session_token}.conf"
        self.port = self._pick_free_udp_port()

    def _pick_free_udp_port(self) -> int:
        """Pick a free high UDP port assigned by the OS.

        Returns:
            int: A free UDP port number.
        """
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        try:
            sock.bind(("", 0))
            return sock.getsockname()[1]
        finally:
            sock.close()

    def _run_local(self, command: str) -> str:
        """Run a shell command locally on the test runner.

        Args:
            command (str): The command to execute.

        Returns:
            str: The combined stdout of the command.
        """
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return result.stdout.strip()

    def get_port(self) -> int:
        """Return the UDP port the receiver listens on.

        Returns:
            int: The receiver port.
        """
        return self.port

    def get_receiver_ip(self, controller_oam_ip: str) -> str:
        """Derive the runner IP that routes to the controller.

        Runs ``ip route get <controller_oam_ip>`` locally and returns the
        ``src`` address, which is the source IP the controller will see and
        the address its trap2sink should target.

        Args:
            controller_oam_ip (str): The controller OAM IP to route toward.

        Returns:
            str: The runner's routable source IP, or None if it could not be
            derived.
        """
        output = self._run_local(f"ip route get {controller_oam_ip}")
        tokens = output.split()
        receiver_ip = None
        if "src" in tokens:
            receiver_ip = tokens[tokens.index("src") + 1]
        get_logger().log_info(f"Receiver IP toward {controller_oam_ip}: {receiver_ip}")
        return receiver_ip

    def start_receiver(self) -> None:
        """Start the snmptrapd receiver as a transient systemd user unit.

        Stops any prior unit of the same name first, writes a minimal
        ``disableAuthorization yes`` config, and launches snmptrapd listening
        on both IPv4 and IPv6 on the chosen port, logging received traps to
        the capture file. Returns once the unit reports active (bounded wait)
        rather than after a fixed sleep.
        """
        self.stop_receiver()
        self._run_local(f"echo 'disableAuthorization yes' > {self.conf_file}")
        self._run_local(f": > {self.capture_file}")
        start_cmd = f"systemd-run --user --unit={self.unit_name} /usr/sbin/snmptrapd -f -Ln -Lf {self.capture_file} -On -c {self.conf_file} udp:{self.port} udp6:[::]:{self.port}"
        self._run_local(start_cmd)
        self._wait_until_running()
        get_logger().log_info(f"Started snmptrapd receiver '{self.unit_name}' on port {self.port}")

    def _wait_until_running(self, timeout: int = 10, polling_sleep_time: int = 1) -> bool:
        """Wait for the receiver unit to become active.

        Args:
            timeout (int): Maximum number of seconds to wait.
            polling_sleep_time (int): Seconds to sleep between polls.

        Returns:
            bool: True if the unit became active within the timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_receiver_running():
                return True
            time.sleep(polling_sleep_time)
        return False

    def is_receiver_running(self) -> bool:
        """Return whether the snmptrapd receiver unit is active.

        Returns:
            bool: True if the systemd user unit is active.
        """
        state = self._run_local(f"systemctl --user is-active {self.unit_name}")
        return state == "active"

    def clear_captured_traps(self) -> None:
        """Truncate the capture file so stale traps do not cause a false pass."""
        self._run_local(f": > {self.capture_file}")

    def _captured_trap_count(self) -> int:
        """Return the number of trap entries currently in the capture file.

        Returns:
            int: Count of ``TRAP`` markers written by snmptrapd.
        """
        count = self._run_local(f"grep -c 'TRAP' {self.capture_file} 2>/dev/null || echo 0")
        try:
            return int(count.strip())
        except ValueError:
            return 0

    def wait_for_trap(self, timeout: int = 120, polling_sleep_time: int = 5) -> bool:
        """Wait for at least one trap to be captured by the receiver.

        Args:
            timeout (int): Maximum number of seconds to wait.
            polling_sleep_time (int): Seconds to sleep between polls.

        Returns:
            bool: True if a trap was captured within the timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._captured_trap_count() > 0:
                get_logger().log_info("Trap captured by the receiver")
                return True
            time.sleep(polling_sleep_time)
        get_logger().log_info("No trap captured within the timeout")
        return False

    def get_captured_traps(self) -> str:
        """Return the full captured-trap text.

        Returns:
            str: Contents of the capture file.
        """
        return self._run_local(f"cat {self.capture_file} 2>/dev/null")

    def stop_receiver(self) -> None:
        """Stop the receiver unit and remove its temporary files.

        Safe to call even if the receiver was never started.
        """
        self._run_local(f"systemctl --user stop {self.unit_name} 2>/dev/null")
        self._run_local(f"systemctl --user reset-failed {self.unit_name} 2>/dev/null")
        self._run_local(f"rm -f {self.capture_file} {self.conf_file}")
        get_logger().log_info(f"Stopped snmptrapd receiver '{self.unit_name}'")
