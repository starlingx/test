"""Keywords for validating controller failover after a graceful ``sudo reboot``.

Backs the spontaneous-reboot-loop regression test. Issuing ``sudo reboot`` on
the active controller must produce a single clean failover:

    * the peer takes over and an active controller is maintained;
    * the rebooted node rejoins as standby (uptime reset to a single boot),
      not active;
    * there is no watchdog-forced crashdump / kernel panic that would drive a
      second spontaneous reboot.

The reboot is issued on the target controller's own connection, while the
rejoin is awaited over a fresh active-controller (floating-IP) connection that
follows the active role across the failover - the same pattern used by the
existing active-controller reboot tests.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.linux.log.log_grep_keywords import LogGrepKeywords

# Logs and markers for the watchdog-forced crashdump / kernel panic.
HOSTWD_LOG_PATH = "/var/log/hostwd.log"
KERN_LOG_PATH = "/var/log/kern.log"
HOSTWD_CRASHDUMP_MARKER = "forcing a crashdump"
HOSTWD_UNHEALTHY_MARKER = "declaring system unhealthy"
KERNEL_PANIC_MARKER = "Kernel panic"

# Service-parameter coordinates for the maintenance heartbeat period.
MTCE_SERVICE = "platform"
MTCE_SECTION = "maintenance"
HEARTBEAT_PERIOD_PARAM = "heartbeat_period"


class SudoRebootFailoverKeywords(BaseKeyword):
    """Drive a graceful reboot of the active controller and verify clean failover."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller
                (floating IP), used for status queries.
        """
        self.ssh_connection = ssh_connection
        self.host_list_keywords = SystemHostListKeywords(ssh_connection)
        self.service_parameter_keywords = SystemServiceParameterKeywords(ssh_connection)
        self.rebooted_host_name = ""

    def get_heartbeat_period(self) -> str:
        """Return the current maintenance ``heartbeat_period`` value.

        Returns:
            str: The configured heartbeat period, or an empty string if the
            parameter is not explicitly set.
        """
        output = self.service_parameter_keywords.list_service_parameters(service=MTCE_SERVICE, section=MTCE_SECTION)
        for parameter in output.get_parameters():
            if parameter.get_name() == HEARTBEAT_PERIOD_PARAM:
                value = parameter.get_value()
                get_logger().log_info(f"Current heartbeat_period: {value}")
                return value
        get_logger().log_info("heartbeat_period is not explicitly set")
        return ""

    def set_heartbeat_period(self, heartbeat_period: int) -> None:
        """Set and apply the maintenance ``heartbeat_period``.

        Args:
            heartbeat_period (int): The heartbeat period in milliseconds.
        """
        get_logger().log_info(f"Setting heartbeat_period to {heartbeat_period}")
        self.service_parameter_keywords.modify_service_parameter(MTCE_SERVICE, MTCE_SECTION, HEARTBEAT_PERIOD_PARAM, str(heartbeat_period))
        self.service_parameter_keywords.apply_service_parameters(MTCE_SERVICE)

    def reboot_active_controller_and_wait(self, reboot_timeout: int = 1800) -> bool:
        """Gracefully reboot the active controller and wait for it to rejoin.

        Issues a graceful ``sudo reboot`` on the active controller over its own
        connection, then reuses ``SystemHostRebootKeywords.wait_for_force_reboot``
        over a fresh active-controller (floating-IP) connection - which follows
        the active role across the failover - to wait for the rebooted node to
        come back unlocked/enabled/available with its uptime reset (a single
        reboot cycle rather than a loop).

        Args:
            reboot_timeout (int): Maximum number of seconds to wait for the
                controller to reboot and rejoin.

        Returns:
            bool: True if the controller rebooted once and rejoined healthy.
        """
        active_controller = self.host_list_keywords.get_active_controller()
        self.rebooted_host_name = active_controller.get_host_name()
        prev_uptime = self.host_list_keywords.get_uptime(self.rebooted_host_name)
        get_logger().log_info(f"Active controller '{self.rebooted_host_name}' pre-reboot uptime: {prev_uptime}")

        reboot_ssh = LabConnectionKeywords().get_ssh_for_hostname(self.rebooted_host_name)
        SystemHostRebootKeywords(reboot_ssh).host_graceful_reboot()

        # Wait over a fresh active-controller connection; the floating IP follows
        # the active role to the peer while the rebooted host is down.
        wait_ssh = LabConnectionKeywords().get_active_controller_ssh()
        return SystemHostRebootKeywords(wait_ssh).wait_for_force_reboot(self.rebooted_host_name, prev_uptime, reboot_timeout)

    def get_rebooted_host_name(self) -> str:
        """Return the host name of the controller that was rebooted.

        Returns:
            str: The rebooted controller host name.
        """
        return self.rebooted_host_name

    def rebooted_node_rejoined_as_standby(self) -> bool:
        """Return whether the rebooted node rejoined as standby with a peer active.

        Confirms the clean role swap: the rebooted controller holds the standby
        personality and a different controller holds the active personality.
        The test is gated on ``lab_has_standby_controller``, so a distinct
        active/standby pair is guaranteed at this point.

        Returns:
            bool: True if the rebooted node is standby and the peer is active.
        """
        wait_ssh = LabConnectionKeywords().get_active_controller_ssh()
        host_list_keywords = SystemHostListKeywords(wait_ssh)
        active_host_name = host_list_keywords.get_active_controller().get_host_name()
        standby_host_name = host_list_keywords.get_standby_controller().get_host_name()
        is_standby = standby_host_name == self.rebooted_host_name
        peer_active = active_host_name != self.rebooted_host_name
        get_logger().log_info(f"Rebooted '{self.rebooted_host_name}' standby={is_standby}, peer active={peer_active}")
        return is_standby and peer_active

    def has_crashdump_or_panic(self, host_name: str) -> bool:
        """Check whether a host logged a watchdog crashdump or kernel panic.

        Inspects hostwd.log for the watchdog crashdump / unhealthy markers and
        kern.log for the kernel-panic marker described in the ticket.

        Args:
            host_name (str): The host whose logs should be inspected.

        Returns:
            bool: True if any crashdump / panic marker is present.
        """
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host_name)
        log_grep_keywords = LogGrepKeywords(host_ssh)
        hostwd_crashdump = log_grep_keywords.grep_log_for_errors(HOSTWD_LOG_PATH, HOSTWD_CRASHDUMP_MARKER)
        hostwd_unhealthy = log_grep_keywords.grep_log_for_errors(HOSTWD_LOG_PATH, HOSTWD_UNHEALTHY_MARKER)
        kernel_panic = log_grep_keywords.grep_log_for_errors(KERN_LOG_PATH, KERNEL_PANIC_MARKER)
        found = bool(hostwd_crashdump) or bool(hostwd_unhealthy) or bool(kernel_panic)
        get_logger().log_info(f"Crashdump/panic markers on '{host_name}': {found}")
        return found
