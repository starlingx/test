import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.bmc.ipmitool.chassis.power.ipmitool_chassis_power_keywords import IPMIToolChassisPowerKeywords
from keywords.bmc.ipmitool.chassis.status.ipmitool_chassis_status_keywords import IPMIToolChassisStatusKeywords
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class PowerKeywords(BaseKeyword):
    """
    Class for generic power keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def power_on(self, host_name: str) -> bool:
        """
        Powers on the given host and waits for the host to be in a good state

        Args:
            host_name (str): the name of the host

        Returns:
            bool: True if host powers on successfully

        Raises:
            KeywordException: if host fails to power on within the expected time
        """
        IPMIToolChassisPowerKeywords(self.ssh_connection, host_name).power_on()
        if not self.is_powered_on(host_name):
            host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
            raise KeywordException("Power on host did not power on in the required time. Host values were: " f"Operational: {host_value.get_operational()} " f"Administrative: {host_value.get_administrative()} " f"Availability: {host_value.get_availability()}")
        return True

    def is_powered_on(self, host_name: str, power_on_wait_timeout: int = 1800) -> bool:
        """
        Checks that the host is powered on and in a good state

        Args:
            host_name (str): the name of the host
            power_on_wait_timeout (int): the time to wait for the host to be powered on

        Returns:
            bool: True if the host is powered on, healthy and has no failure alarms ; False otherwise
        """
        timeout = time.time() + power_on_wait_timeout
        refresh_time = 5

        is_power_on = False
        is_host_list_ok = False
        is_alarms_list_ok = False

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
                for alarm in alarms:
                    if alarm.get_alarm_id() == "200.004" or alarm.get_alarm_id() == "200.005" or alarm.get_alarm_id() == "750.006":  #
                        is_alarms_list_ok = False
                if is_alarms_list_ok:
                    get_logger().log_info("There are no critical failures alarms")

                # Exit the loop once all conditions are met.
                if is_host_list_ok and is_alarms_list_ok and is_power_on:
                    return True

            except Exception:
                get_logger().log_info(f"Found an exception when checking the health of the system. Trying again after {refresh_time} seconds")

            time.sleep(refresh_time)

        return False

    def power_off(self, host_name: str) -> bool:
        """
        Powers off the host

        Args:
            host_name (str): the name of the host

        Returns:
            bool: True if powered off

        Raises:
            KeywordException: if host fails to power off within the expected time
        """
        IPMIToolChassisPowerKeywords(self.ssh_connection, host_name).power_off()
        if not self.is_powered_off(host_name):
            host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
            raise KeywordException("Power off host did not power off in the required time. Host values were: " f"Operational: {host_value.get_operational()} " f"Administrative: {host_value.get_administrative()} " f"Availability: {host_value.get_availability()}")
        return True

    def is_powered_off(self, host_name: str) -> bool:
        """
        Waits for the host to be powered off

        Args:
            host_name (str): the name of the host

        Returns:
            bool: True if host powered off and host operations are disabled; False otherwise
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

    def power_cycle(self, host_name: str):
        """
        Powers cycle the host

        Args:
            host_name (str): the name of the host
        """
        IPMIToolChassisPowerKeywords(self.ssh_connection, host_name).power_cycle()
