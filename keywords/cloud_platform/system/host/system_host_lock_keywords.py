import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class SystemHostLockKeywords(BaseKeyword):
    """
    Keywords for System Host Lock commands
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def lock_host(self, host_name: str) -> bool:
        """
        Locks the given host name. It's expected that the host will already be unlocked
        Args:
            host_name (): the name of the host

        Returns: True if it's successful

        """
        self.ssh_connection.send(source_openrc(f'system host-lock {host_name}'))
        self.validate_success_return_code(self.ssh_connection)
        is_host_locked = SystemHostLockKeywords(self.ssh_connection).wait_for_host_locked(host_name)
        if not is_host_locked:
            host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
            raise KeywordException(
                "Lock host did not lock in the required time. Host values were: "
                f"Operational: {host_value.get_operational()} "
                f"Administrative: {host_value.get_administrative()} "
                f"Availability: {host_value.get_availability()}"
            )
        return True

    def wait_for_host_locked(self, host_name: str) -> bool:
        """
        Waits for the given host name to be locked
        Args:
            host_name (): the host name

        Returns:

        """
        timeout = time.time() + 600

        while time.time() < timeout:
            if self.is_host_locked(host_name):
                return True
            time.sleep(5)

        return False

    def is_host_locked(self, host_name: str):
        """
        Returns true if the host is locked
        Args:
            host_name (): the name of the host

        Returns:

        """
        host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
        if host_value.get_availability() == 'online' and host_value.get_administrative() == 'locked' and host_value.get_operational() == 'disabled':
            return True
        return False

    def unlock_host(self, host_name: str) -> bool:
        """
        Unlocks the given host
        Args:
            ssh_connection (): the ssh connection
            host_name (): the host name

        Returns:

        """
        self.ssh_connection.send(source_openrc(f'system host-unlock {host_name}'))
        self.validate_success_return_code(self.ssh_connection)
        is_host_unlocked = self.wait_for_host_unlocked(host_name)
        if not is_host_unlocked:
            host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
            raise KeywordException(
                "Lock host did not lock in the required time. Host values were: "
                f"Operational: {host_value.get_operational()} "
                f"Administrative: {host_value.get_administrative()} "
                f"Availability: {host_value.get_availability()}"
            )
        return True

    def wait_for_host_unlocked(self, host_name: str, unlock_wait_timeout=1800) -> bool:
        """
        Wait for the host to be unlocked
        Args:
            host_name (): the host name
            unlock_wait_timeout: the amount of time in secs to wait for the host to unlock

        Returns:

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

    def is_host_unlocked(self, host_name: str):
        """
        Returns true if the host is unlocked
        Args:
            host_name ():

        Returns:

        """

        is_host_list_ok = False

        # Check System Host-List
        host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
        if host_value.get_availability() == 'available' and host_value.get_administrative() == 'unlocked' and host_value.get_operational() == 'enabled':
            get_logger().log_info("The host is in a good state from system host list.")
            is_host_list_ok = True

        # Check the alarms of the host
        alarms = AlarmListKeywords(self.ssh_connection).alarm_list()
        is_alarms_list_ok = True
        for alarm in alarms:
            if alarm.get_alarm_id() == "250.001":  # Configuration is out-of-date
                is_alarms_list_ok = False
        if is_alarms_list_ok:
            get_logger().log_info("There are no Config-out-of-date alarms")

        # Exit the loop once all conditions are met.
        if is_host_list_ok and is_alarms_list_ok:
            return True

        return False
