from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.healthquery.objects.system_health_query_kube_upgrade_output import SystemHealthQueryKubeUpgradeOutput


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
