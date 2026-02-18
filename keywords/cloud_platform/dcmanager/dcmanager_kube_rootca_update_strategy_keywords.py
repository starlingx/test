from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_kube_rootca_update_strategy_show_output import DcmanagerKubeRootcaUpdateStrategyShowOutput


class DcmanagerKubeRootcaUpdateStrategyKeywords(BaseKeyword):
    """
    This class executes kube-rootca-update-strategy commands
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def wait_kube_upgrade(self, expected_status: str, check_interval: int = 30, timeout: int = 240) -> None:
        """
        Waits for kube upgrade method to return True.
        """

        def check_kube_deployment() -> str:
            """
            Checks if the kube upgrade operation has been completed, either 'initial' or 'apply'.

            Returns:
                str: Expected status for kube deployment.
            """
            kube_deployment_status = self.get_dcmanager_kube_rootca_update_strategy_step_show().get_dcmanager_kube_rootca_update_strategy_step_show().get_state()
            return kube_deployment_status

        validate_equals_with_retry(
            function_to_execute=check_kube_deployment,
            expected_value=expected_status,
            validation_description=f"Waiting for sw_deployment_status {expected_status}.",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )

    def dcmanager_kube_rootca_update_strategy_create(self, subcloud_apply_type: Optional[str] = None, max_parallel_subclouds: Optional[str] = None, stop_on_failure: Optional[bool] = None, group: Optional[str] = None, subject: Optional[str] = None, expiry_date: Optional[str] = None, force: Optional[bool] = None, subcloud_name: Optional[str] = None) -> DcmanagerKubeRootcaUpdateStrategyShowOutput:
        """
        Create kube-rootca-update-strategy

        Args:
            subcloud_apply_type (Optional[str]): Subcloud apply type.
            max_parallel_subclouds (Optional[str]): Maximum parallel subclouds.
            stop_on_failure (Optional[bool]): Stop on failure.
            group (Optional[str]): Group.
            subject (Optional[str]): Subject.
            expiry_date (Optional[str]): Expiry date.
            force (Optional[bool]): Force flag.
            subcloud_name (Optional[str]): subloud name.

        Returns:
            DcmanagerKubeRootcaUpdateStrategyShowOutput: An object containing details of the kubernetes strategy .
        """
        cmd = "dcmanager kube-rootca-update-strategy create"

        if subcloud_apply_type:
            cmd += f" --subcloud-apply-type {subcloud_apply_type}"
        if max_parallel_subclouds:
            cmd += f" --max-parallel-subclouds {max_parallel_subclouds}"
        if stop_on_failure:
            cmd += " --stop-on-failure"
        if group:
            cmd += f" --group {group}"
        if subject:
            cmd += f" --subject='{subject}'"
        if expiry_date:
            cmd += f" --expiry-date {expiry_date}"
        if force:
            cmd += " --force"
        if subcloud_name:
            cmd += f" {subcloud_name}"

        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        self.wait_kube_upgrade(expected_status="initial")

        return DcmanagerKubeRootcaUpdateStrategyShowOutput(output)

    def dcmanager_kube_rootca_update_strategy_apply(self) -> DcmanagerKubeRootcaUpdateStrategyShowOutput:
        """
        Apply kube-rootca-update-strategy

        Returns:
            DcmanagerKubeRootcaUpdateStrategyShowOutput: An object containing details of the kubernetes strategy .
        """
        cmd = "dcmanager kube-rootca-update-strategy apply"

        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        self.wait_kube_upgrade(expected_status="complete", check_interval=60, timeout=3600)

        return DcmanagerKubeRootcaUpdateStrategyShowOutput(output)

    def get_dcmanager_kube_rootca_update_strategy_step_show(self) -> DcmanagerKubeRootcaUpdateStrategyShowOutput:
        """
        Gets the dcmanager kube-rootca-update-strategy show

        Returns:
            DcmanagerKubeRootcaUpdateStrategyShowOutput: An object containing details of the strategy step.
        """
        cmd = "dcmanager kube-rootca-update-strategy show"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerKubeRootcaUpdateStrategyShowOutput(output)

    def dcmanager_kube_rootca_update_strategy_delete(self) -> DcmanagerKubeRootcaUpdateStrategyShowOutput:
        """
        Delete kube-rootca-update-strategy

        Returns:
            DcmanagerKubeRootcaUpdateStrategyShowOutput: An object containing details of the kubernetes strategy.
        """
        cmd = "dcmanager kube-rootca-update-strategy delete"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerKubeRootcaUpdateStrategyShowOutput(output)

    def get_future_date(self, days: int) -> str:
        """
        Get future date in YYYY-MM-DD format.

        Args:
            days (int): Number of days in the future.

        Returns:
            str: Date string in YYYY-MM-DD format.
        """
        cmd = f"date +'%Y-%m-%d' --date='{days} days'"
        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return output[0].strip()

    def wait_for_strategy_deletion(self, timeout: int = 300) -> bool:
        """
        Wait for strategy to be fully deleted.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            bool: True if strategy deleted, False if timeout.
        """
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            self.ssh_connection.send(source_openrc("dcmanager kube-rootca-update-strategy show"))
            if self.ssh_connection.get_return_code() != 0:
                return True
            time.sleep(5)
        return False
