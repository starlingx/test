import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.bmc.ipmitool.chassis.bootdev.ipmitool_chassis_bootdev_keywords import IPMIToolChassisBootdevKeywords
from keywords.bmc.ipmitool.chassis.power.ipmitool_chassis_power_keywords import IPMIToolChassisPowerKeywords
from keywords.bmc.ipmitool.chassis.status.ipmitool_chassis_status_keywords import IPMIToolChassisStatusKeywords
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords

# Alarm IDs that block a successful power-on
BLOCKING_ALARM_IDS = ["200.004", "200.005", "750.006"]

# Minimum uptime (in seconds) required for mtcAgent before considering
# the host ready.  The mtcAgent has a 20-second inline delay before it
# starts adding hosts, so we wait at least 30 seconds to be safe.
MTC_AGENT_MIN_UPTIME_SECONDS = 30


class PowerKeywordsImplementation:
    """Default StarlingX implementation of the power keywords.

    This class holds the actual power-management logic that the public
    :class:`PowerKeywords` interface dispatches to. It is intentionally a
    plain class (not a ``BaseKeyword`` subclass) so that the keyword
    logging hook only fires once at the interface boundary rather than
    being wrapped a second time when the interface delegates here.

    Users can extend this class to override behavior
    on a per-method basis and register the subclass via
    :meth:`PowerKeywords.set_implementation_class`. Anything not
    overridden falls through to the StarlingX behavior implemented here.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection used to drive
                IPMI and ``system`` CLI commands on the target lab.
        """
        self.ssh_connection = ssh_connection
        self._last_power_on_failure_reason = "Unknown"

    def power_on(self, host_name: str) -> bool:
        """Power on the given host and wait for it to be in a good state.

        Args:
            host_name (str): The name of the host.

        Returns:
            bool: True if the host powers on successfully.

        Raises:
            KeywordException: If the host fails to power on within the
                expected time.
        """
        IPMIToolChassisPowerKeywords(self.ssh_connection, host_name).power_on()
        if not self.is_powered_on(host_name):
            raise KeywordException(
                f"Power on host failed. Reason(s): {self._last_power_on_failure_reason}"
            )
        return True

    def _get_mtc_agent_uptime_seconds(self) -> int | None:
        """Return the elapsed time (in seconds) that mtcAgent has been running.

        Uses ``ps -p $(cat /var/run/mtcAgent.pid) -o etimes=`` on the
        active controller.

        Returns:
            int | None: The uptime in seconds, or None if it cannot be
            determined (e.g. PID file missing, process not running).
        """
        output = self.ssh_connection.send("ps -p $(cat /var/run/mtcAgent.pid) -o etimes=")
        # send() returns a list of strings (one per line)
        if isinstance(output, list):
            for line in output:
                stripped = line.strip()
                if stripped.isdigit():
                    return int(stripped)
        else:
            stripped = str(output).strip()
            if stripped.isdigit():
                return int(stripped)
        return None

    def _wait_for_mtc_agent_ready(self, timeout: int = 120) -> bool:
        """Wait until the mtcAgent has been running for at least the minimum uptime.

        After an unlock, the mtcAgent has a 20-second inline delay before
        it starts adding hosts. This method ensures we don't proceed until
        the agent is past that initialization window.

        Args:
            timeout (int): Maximum time in seconds to wait for the
                mtcAgent to reach the required uptime.

        Returns:
            bool: True if the mtcAgent reached the minimum uptime within
            the timeout; False otherwise.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            uptime = self._get_mtc_agent_uptime_seconds()
            if uptime is not None and uptime >= MTC_AGENT_MIN_UPTIME_SECONDS:
                get_logger().log_info(
                    f"mtcAgent has been running for {uptime}s "
                    f"(>= {MTC_AGENT_MIN_UPTIME_SECONDS}s required). Proceeding."
                )
                return True
            time.sleep(5)

        get_logger().log_info(
            f"mtcAgent did not reach {MTC_AGENT_MIN_UPTIME_SECONDS}s uptime "
            f"within {timeout}s timeout."
        )
        return False

    def is_powered_on(self, host_name: str, power_on_wait_timeout: int = 1800) -> bool:
        """Check that the host is powered on and in a good state.

        Args:
            host_name (str): The name of the host.
            power_on_wait_timeout (int): The time to wait for the host to
                be powered on, in seconds.

        Returns:
            bool: True if the host is powered on, healthy, has no
            failure alarms, and mtcAgent is ready; False otherwise.
        """
        timeout = time.time() + power_on_wait_timeout
        refresh_time = 5

        is_power_on = False
        is_host_list_ok = False
        is_alarms_list_ok = False
        blocking_alarms: list[str] = []

        while time.time() < timeout:

            try:
                status = IPMIToolChassisStatusKeywords(self.ssh_connection, host_name).get_ipmi_chassis_status()
                if status.system_power == "on":
                    get_logger().log_info("The host is powered on.")
                    is_power_on = True

                # Check System Host-List
                host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
                is_host_list_ok = host_value.is_host_healthy()

                # Check the alarms of the host
                alarms = AlarmListKeywords(self.ssh_connection).alarm_list()
                is_alarms_list_ok = True
                blocking_alarms = []
                for alarm in alarms:
                    if alarm.get_alarm_id() in BLOCKING_ALARM_IDS:
                        is_alarms_list_ok = False
                        blocking_alarms.append(alarm.get_alarm_id())
                if is_alarms_list_ok:
                    get_logger().log_info("There are no critical failure alarms.")
                else:
                    get_logger().log_info(
                        f"Blocking alarm(s) still active: {', '.join(blocking_alarms)}. "
                        "Waiting for them to clear."
                    )

                # Exit the loop once all conditions are met.
                if is_host_list_ok and is_alarms_list_ok and is_power_on:
                    # Wait for mtcAgent to be ready before declaring success
                    if not self._wait_for_mtc_agent_ready():
                        get_logger().log_info(
                            "mtcAgent is not ready yet. Continuing to wait."
                        )
                        continue
                    return True

            except Exception:
                get_logger().log_info(
                    f"Found an exception when checking the health of the system. "
                    f"Trying again after {refresh_time} seconds."
                )

            time.sleep(refresh_time)

        # Build failure reason from the already-collected state
        failure_details = []
        if not is_power_on:
            failure_details.append("chassis did not power on")
        if not is_host_list_ok:
            failure_details.append("host is not in a healthy state")
        if not is_alarms_list_ok:
            failure_details.append(
                f"blocking alarm(s) active: {', '.join(blocking_alarms)}"
            )
        if is_power_on and is_host_list_ok and is_alarms_list_ok:
            failure_details.append(
                f"mtcAgent did not reach {MTC_AGENT_MIN_UPTIME_SECONDS}s uptime"
            )

        self._last_power_on_failure_reason = (
            "; ".join(failure_details) if failure_details else "unknown cause"
        )
        get_logger().log_info(
            f"Power on timed out for host '{host_name}'. "
            f"Failed condition(s): {self._last_power_on_failure_reason}."
        )

        return False

    def power_off(self, host_name: str) -> bool:
        """Power off the host.

        Args:
            host_name (str): The name of the host.

        Returns:
            bool: True if the host is powered off successfully.

        Raises:
            KeywordException: If the host fails to power off within the
                expected time.
        """
        IPMIToolChassisPowerKeywords(self.ssh_connection, host_name).power_off()
        if not self.is_powered_off(host_name):
            host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
            raise KeywordException("Power off host did not power off in the required time. Host values were: " f"Operational: {host_value.get_operational()} " f"Administrative: {host_value.get_administrative()} " f"Availability: {host_value.get_availability()}")
        return True

    def is_powered_off(self, host_name: str) -> bool:
        """Wait for the host to be powered off.

        Args:
            host_name (str): The name of the host.

        Returns:
            bool: True if the host is powered off and host operations
            are disabled; False otherwise.
        """
        timeout = time.time() + 600
        is_power_off = False
        is_host_list_ok = False

        while time.time() < timeout:
            try:
                status = IPMIToolChassisStatusKeywords(self.ssh_connection, host_name).get_ipmi_chassis_status()
                if status.system_power == "off":
                    get_logger().log_info("The host is powered off.")
                    is_power_off = True

                host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
                if host_value.get_availability() == "offline" and host_value.get_operational() == "disabled":
                    is_host_list_ok = True

                if is_power_off and is_host_list_ok:
                    return True
            except Exception:
                get_logger().log_info("Found an exception when checking the health of the system. Trying again")

            time.sleep(5)

        return False

    def power_cycle(self, host_name: str) -> None:
        """Power cycle the host.

        Args:
            host_name (str): The name of the host.
        """
        IPMIToolChassisPowerKeywords(self.ssh_connection, host_name).power_cycle()

    def set_boot_device_pxe(self, host_name: str) -> bool:
        """Set the next boot device of the host to PXE (network boot).

        Args:
            host_name (str): The name of the host.

        Returns:
            bool: True if the boot device was successfully set to PXE.
        """
        return IPMIToolChassisBootdevKeywords(self.ssh_connection, host_name).set_chassis_bootdev_pxe()
