import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class SystemHostLockKeywords(BaseKeyword):
    """
    Keywords for System Host Lock commands
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): the ssh connection
        """
        self.ssh_connection = ssh_connection

    def lock_host(self, host_name: str) -> bool:
        """
        Locks the given host name. It's expected that the host will already be unlocked

        Args:
            host_name (str): the name of the host

        Returns:
            bool: True if it's successful

        Raises:
            KeywordException: If lock does not occur in the given amount of time

        """
        self.ssh_connection.send(source_openrc(f"system host-lock {host_name}"))
        self.validate_success_return_code(self.ssh_connection)
        is_host_locked = SystemHostLockKeywords(self.ssh_connection).wait_for_host_locked(host_name)
        if not is_host_locked:
            host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
            raise KeywordException("Lock host did not lock in the required time. Host values were: " f"Operational: {host_value.get_operational()} " f"Administrative: {host_value.get_administrative()} " f"Availability: {host_value.get_availability()}")
        return True

    def lock_host_with_error(self, host_name: str) -> str:
        """
        Locks the given host name. It's expected that the cmd returns error

        Args:
            host_name (str): the name of the host

        Returns:
            str: a str of error message

        """
        msg = self.ssh_connection.send(source_openrc(f"system host-lock {host_name}"))
        return msg[0]

    def wait_for_host_locked(self, host_name: str) -> bool:
        """
        Waits for the given host name to be locked

        Args:
            host_name (str): the host name

        Returns:
            bool: True if lock successful

        """
        timeout = time.time() + 600

        while time.time() < timeout:
            if self.is_host_locked(host_name):
                return True
            time.sleep(5)

        return False

    def is_host_locked(self, host_name: str) -> bool:
        """
        Returns true if the host is locked

        Args:
            host_name (str): the name of the host

        Returns:
            bool: True is host is locked

        """
        host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
        if host_value.get_availability() == "online" and host_value.get_administrative() == "locked" and host_value.get_operational() == "disabled":
            return True
        return False

    def unlock_host(self, host_name: str) -> bool:
        """
        Unlocks the given host

        Args:
            host_name (str): the host name

        Returns:
            bool: True if the unlock is successful

        Raises:
            KeywordException: If unlock does not occur in the given time

        """
        self.unlock_host_pre_check()
        self.ssh_connection.send(source_openrc(f"system host-unlock {host_name}"))
        self.validate_success_return_code(self.ssh_connection)
        is_host_unlocked = self.wait_for_host_unlocked(host_name)
        if not is_host_unlocked:
            host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
            raise KeywordException("Unlock host did not unlock in the required time. Host values were: " f"Operational: {host_value.get_operational()} " f"Administrative: {host_value.get_administrative()} " f"Availability: {host_value.get_availability()}")
        return True

    def unlock_host_pre_check(self):
        """
        Checks to ensure no apps are currently applying as this will cause unlock to fail

        """
        # check not apps are applying
        alarm = AlarmListObject()
        alarm.set_alarm_id("750.004")
        try:
            AlarmListKeywords(self.ssh_connection).wait_for_alarms_cleared([alarm])
        except TimeoutError:  # Alarm still exists, we can't unlock
            raise KeywordException("Failed unlock pre-check. Application apply was in progress")

    def wait_for_host_unlocked(self, host_name: str, unlock_wait_timeout: int = 1800) -> bool:
        """
        Wait for the host to be unlocked

        Args:
            host_name (str): the host name
            unlock_wait_timeout (int): the amount of time in secs to wait for the host to unlock

        Returns:
            bool: True if host is unlocked

        """
        timeout = time.time() + unlock_wait_timeout
        refresh_time = 5

        while time.time() < timeout:

            try:
                if self.is_host_unlocked(host_name):
                    return True
            except Exception:
                get_logger().log_info(f"Found an exception when checking the health of the system. Trying again after {refresh_time} seconds")

            time.sleep(refresh_time)
        return False

    def is_host_unlocked(self, host_name: str) -> bool:
        """
        Returns true if the host is unlocked

        Args:
            host_name (str): the name of the host

        Returns:
            bool: True is host is unlocked

        """
        is_host_list_ok = False

        # Check System Host-List
        host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
        if host_value.get_availability() == "available" and host_value.get_administrative() == "unlocked" and host_value.get_operational() == "enabled":
            get_logger().log_info("The host is in a good state from system host list.")
            is_host_list_ok = True

        # Check the alarms of the host
        alarms = AlarmListKeywords(self.ssh_connection).alarm_list()
        is_alarms_list_ok = True
        for alarm in alarms:
            # Configuration is out-of-date or apps need re-apply or app being reapplied
            if alarm.get_alarm_id() == "250.001" or alarm.get_alarm_id() == "750.006" or alarm.get_alarm_id() == "750.004":
                is_alarms_list_ok = False
        if is_alarms_list_ok:
            get_logger().log_info("There are no Config-out-of-date alarms")

        # Exit the loop once all conditions are met.
        if is_host_list_ok and is_alarms_list_ok:
            return True

        return False

    def unlock_multiple_hosts(ssh_connection: SSHConnection, host_names: list[str]) -> None:
        """
        Unlocks multiple hosts in succession without waiting between each unlock.

        Args:
            host_names (list[str]): List of host names to unlock
        """
        for host_name in host_names:
            get_logger().log_info(f"Sending unlock command for host: {host_name}")
            SystemHostLockKeywords(ssh_connection).unlock_host_pre_check()
            ssh_connection.send(source_openrc(f"system host-unlock {host_name}"))
            SystemHostLockKeywords(ssh_connection).validate_success_return_code(ssh_connection)

        for host_name in host_names:
            if not SystemHostLockKeywords(ssh_connection).wait_for_host_unlocked(host_name):
                raise RuntimeError(f"{host_name} was not unlocked successfully.")

    def lock_multiple_hosts(ssh_connection: SSHConnection, host_names: list[str]) -> None:
        """
        Locks multiple hosts in succession without waiting between each lock.

        Args:
            host_names (list[str]): List of host names to lock
        """
        for host_name in host_names:
            get_logger().log_info(f"Sending lock command for host: {host_name}")
            ssh_connection.send(source_openrc(f"system host-lock {host_name}"))
            SystemHostLockKeywords(ssh_connection).validate_success_return_code(ssh_connection)

            is_host_locked = SystemHostLockKeywords(ssh_connection).wait_for_host_locked(host_name)
            if not is_host_locked:
                raise RuntimeError(f"{host_name} was not locked successfully.")
