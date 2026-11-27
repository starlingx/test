import shlex

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_patch_strategy_config_output import DcmanagerPatchStrategyConfigOutput


class DcmanagerStrategyConfigKeywords(BaseKeyword):
    """
    This class contains the keywords related to the 'dcmanager strategy-config' commands.

    Note: 'dcmanager strategy-config' is the current name of the command. Older releases
    also accept 'dcmanager patch-strategy-config' as an alias for it (see
    DcmanagerPatchStrategyConfigKeywords).
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initializes DcmanagerStrategyConfigKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_strategy_config_update(
        self,
        subcloud_name: str,
        storage_apply_type: str,
        worker_apply_type: str,
        max_parallel_workers: int,
        alarm_restriction_type: str,
        default_instance_action: str,
    ) -> None:
        """
        Runs 'dcmanager strategy-config update' for a subcloud.

        The CLI requires all five options on every update, so all of them are required here.

        Args:
            subcloud_name (str): Name of the subcloud the config applies to.
            storage_apply_type (str): Value for --storage-apply-type ('parallel' or 'serial').
            worker_apply_type (str): Value for --worker-apply-type ('parallel' or 'serial').
            max_parallel_workers (int): Value for --max-parallel-workers.
            alarm_restriction_type (str): Value for --alarm-restriction-type ('strict' or 'relaxed').
            default_instance_action (str): Value for --default-instance-action ('stop-start' or 'migrate').

        Raises:
            AssertionError: If the command does not return success.
        """
        options = [
            f"--storage-apply-type {shlex.quote(storage_apply_type)}",
            f"--worker-apply-type {shlex.quote(worker_apply_type)}",
            f"--max-parallel-workers {int(max_parallel_workers)}",
            f"--alarm-restriction-type {shlex.quote(alarm_restriction_type)}",
            f"--default-instance-action {shlex.quote(default_instance_action)}",
        ]

        command = " ".join(["dcmanager strategy-config update", shlex.quote(subcloud_name)] + options)
        self.ssh_connection.send(source_openrc(command))
        self.validate_success_return_code(self.ssh_connection)

    def get_dcmanager_strategy_config_list(self) -> DcmanagerPatchStrategyConfigOutput:
        """
        Runs 'dcmanager strategy-config list'.

        The list uses the same table columns as 'dcmanager patch-strategy-config list',
        so the existing output parser is reused.

        Returns:
            DcmanagerPatchStrategyConfigOutput: The parsed strategy config entries.
        """
        command = source_openrc("dcmanager strategy-config list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPatchStrategyConfigOutput(output)
