import re

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.health_query.objects.system_health_query_kube_upgrade_output import SystemHealthQueryKubeUpgradeOutput
from keywords.cloud_platform.system.health_query.objects.system_health_query_object import SystemHealthQueryObject
from keywords.cloud_platform.system.health_query.objects.system_health_query_output import SystemHealthQueryOutput


class SystemHealthQueryKeywords(BaseKeyword):
    """
    System Health Query Keywords class for health-related system commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize SystemHealthQueryKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_health_status(self) -> SystemHealthQueryOutput:
        """Get system health status.

        Returns:
            SystemHealthQueryOutput: Parsed health check results.
        """
        command = source_openrc("system health-query")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SystemHealthQueryOutput(output)

    def get_kube_upgrade_health_status(self) -> SystemHealthQueryKubeUpgradeOutput:
        """Get detailed health status for Kubernetes upgrade.

        Returns:
            SystemHealthQueryKubeUpgradeOutput: Parsed health check results.
        """
        command = source_openrc("system health-query-kube-upgrade")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SystemHealthQueryKubeUpgradeOutput(output)

    def is_system_healthy_for_kube_upgrade(self) -> bool:
        """Check if the system is healthy for Kubernetes upgrade.

        Returns:
            bool: True if system is healthy for upgrade. If not healthy, return the reason for failure.

        Raises:
            KeywordException: If system is not healthy with details of failed checks.
        """
        health_status = self.get_kube_upgrade_health_status()

        if health_status.is_all_healthy():
            return True

        failed_checks = health_status.get_failed_checks()
        failed_details = []
        for check in failed_checks:
            detail = f"{check.get_check_name()}: {check.get_status()}"
            if check.get_reason():
                detail += f" - {check.get_reason()}"
            failed_details.append(detail)
        raise KeywordException(f"System not healthy for kube upgrade. Failed checks: {', '.join(failed_details)}")

    def count_blocking_health_failures(self, failed_checks: list[SystemHealthQueryObject]) -> int:
        """Count health-query-kube-upgrade failures that should block the upgrade.

        The 'No alarms' health check fails whenever any alarm is present, but its reason
        text reports how many of those alarms are management affecting (for example
        '[2] alarms found, [0] of which are management affecting ...'). A legacy
        Kubernetes upgrade tolerates non management-affecting alarms, so the alarms check
        is treated as blocking only when its management-affecting count is greater than
        zero. Every other failed health check is always blocking.

        Args:
            failed_checks (list[SystemHealthQueryObject]): SystemHealthQueryObject items whose status is not OK.

        Returns:
            int: Number of failed checks that block the Kubernetes upgrade.
        """
        blocking = 0
        for check in failed_checks:
            reason = check.get_reason() or ""
            match = re.search(r"\[(\d+)\]\s+of which are management affecting", reason)
            if match is not None:
                # This is the alarms check; block only if any alarm is management affecting.
                if int(match.group(1)) > 0:
                    get_logger().log_info(f"Blocking health failure (management-affecting alarms): {check.get_check_name()}: {check.get_status()} - {reason}")
                    blocking += 1
                else:
                    get_logger().log_info(f"Ignoring non management-affecting alarms for kube upgrade: {check.get_check_name()}: {reason}")
            else:
                get_logger().log_info(f"Blocking health failure: {check.get_check_name()}: {check.get_status()} - {reason}")
                blocking += 1
        return blocking
