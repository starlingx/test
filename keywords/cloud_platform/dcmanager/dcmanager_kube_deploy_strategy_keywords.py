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

    def dcmanager_kube_upgrade_strategy_create(self, kube_version: str = None, subcloud: str = None, subcloud_group: str = None, subcloud_apply_type: str = None, max_parallel_subclouds: int = None) -> DcmanagerKubeStrategyStepShowOutput:
        """
        Kube-strategy create.

        Args:
            kube_version (str): Kubernetes version to be upgraded to. If None, dcmanager uses latest available.
            subcloud (str): Subcloud name. If None (and no group), the strategy targets all managed online subclouds.
            subcloud_group (str): Subcloud group name.
            subcloud_apply_type (str): 'parallel' or 'serial'. Controls whether subclouds are upgraded concurrently.
            max_parallel_subclouds (int): Maximum number of subclouds to upgrade in parallel (only meaningful with parallel apply type).

        Returns:
            DcmanagerKubeStrategyStepShowOutput: An object containing details of the kubernetes strategy .
        """
        cmd_parts = ["dcmanager kube-upgrade-strategy create"]
        if subcloud_group:
            cmd_parts.append(f"--group {subcloud_group}")
        if subcloud_apply_type:
            cmd_parts.append(f"--subcloud-apply-type {subcloud_apply_type}")
        if max_parallel_subclouds:
            cmd_parts.append(f"--max-parallel-subclouds {max_parallel_subclouds}")
        if kube_version:
            cmd_parts.append(f"--to-version {kube_version}")
        # A specific subcloud name (positional) is only added when no group is targeted.
        if subcloud and not subcloud_group:
            cmd_parts.append(subcloud)

        command = source_openrc(" ".join(cmd_parts))

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
        self.wait_kube_upgrade(expected_status="complete", timeout=3600)

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

    def dcmanager_kube_strategy_delete(self, timeout: int = 300) -> None:
        """
        Delete the kubernetes upgrade strategy and wait until it is fully removed.

        The 'dcmanager kube-upgrade-strategy delete' request only transitions the strategy
        to the 'deleting' state; the actual removal is asynchronous. This issues the delete
        (tolerating the case where no strategy exists or one is already being deleted) and
        then polls until 'dcmanager kube-upgrade-strategy show' reports no strategy, so a
        subsequent create cannot race the in-progress deletion.

        Args:
            timeout (int): Maximum time in seconds to wait for the strategy to be removed.
        """
        command = source_openrc("dcmanager kube-upgrade-strategy delete")
        self.ssh_connection.send(command)
        # Do not assert the delete return code: it is non-zero when the strategy is already
        # absent or still in the 'deleting' state. Correctness is confirmed by waiting for
        # the strategy to disappear below.

        def strategy_is_gone() -> bool:
            """Check whether no kubernetes strategy exists any more.

            Returns:
                bool: True once 'show' reports no strategy, False while it still exists.
            """
            show_output = self.ssh_connection.send(source_openrc("dcmanager kube-upgrade-strategy show"))
            output_str = "".join(show_output)
            return "not found" in output_str or "doesn't exist" in output_str

        validate_equals_with_retry(
            function_to_execute=strategy_is_gone,
            expected_value=True,
            validation_description="Waiting for kubernetes strategy to be deleted",
            timeout=timeout,
            polling_sleep_time=10,
        )
