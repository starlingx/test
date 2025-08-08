from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_kube_strategy_step_show_output import DcmanagerKubeStrategyStepShowOutput


class DcmanagerKubeStrategyKeywords(BaseKeyword):
    """
    This class executes kube-upgrade-strategy commands
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def wait_kube_upgrade(
        self,
        expected_status: str,
        check_interval: int = 30,
        timeout: int = 240,
    ) -> None:
        """
        Waits for kube upgrade method to return True.
        """

        def check_kube_deployment() -> str:
            """
            Checks if the kube upgrade operation has been completed, either 'initial' or 'apply'.

            Returns:
                str: Expected status for kube deployment.
            """
            kube_deployment_status = self.get_dcmanager_kube_strategy_step_show().get_dcmanager_kube_strategy_step_show().get_state()
            return kube_deployment_status

        validate_equals_with_retry(
            function_to_execute=check_kube_deployment,
            expected_value=expected_status,
            validation_description=f"Waiting for sw_deployment_status {expected_status}.",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )

    def dcmanager_kube_upgrade_strategy_create(self, subcloud: str, kube_version: str) -> DcmanagerKubeStrategyStepShowOutput:
        """
        Kube-strategy create.

        Args:
            subcloud (str): Subcloud name.
            kube_version (str): Kubernetes version to be upgraded to.

        Returns:
            DcmanagerKubeStrategyStepShowOutput: An object containing details of the kubernetes strategy .
        """
        command = source_openrc(f"dcmanager kube-upgrade-strategy create {subcloud} --to-version {kube_version}")

        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        self.wait_kube_upgrade(expected_status="initial")

        return DcmanagerKubeStrategyStepShowOutput(output)

    def dcmanager_kube_upgrade_strategy_apply(self) -> DcmanagerKubeStrategyStepShowOutput:
        """
        Kube-strategy apply.

        Returns:
            DcmanagerKubeStrategyStepShowOutput: An object containing details of the kubernetes strategy .
        """
        command = source_openrc("dcmanager kube-upgrade-strategy apply")

        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        self.wait_kube_upgrade(expected_status="complete")

        return DcmanagerKubeStrategyStepShowOutput(output)

    def get_dcmanager_kube_strategy_step_show(self) -> DcmanagerKubeStrategyStepShowOutput:
        """
        Gets the dcmanager kube-upgrade-strategy show.

        Returns:
            DcmanagerKubeStrategyStepShowOutput: An object containing details of the strategy step.
        """
        command = source_openrc("dcmanager kube-upgrade-strategy show")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerKubeStrategyStepShowOutput(output)

    def dcmanager_kube_strategy_delete(self) -> DcmanagerKubeStrategyStepShowOutput:
        """
        Delete the kubernetes upgrade strategy.

        Returns:
            DcmanagerKubeStrategyStepShowOutput: An object containing details of
            the kubernetes strategy .
        """
        command = source_openrc("dcmanager kube-upgrade-strategy delete.")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerKubeStrategyStepShowOutput(output)
