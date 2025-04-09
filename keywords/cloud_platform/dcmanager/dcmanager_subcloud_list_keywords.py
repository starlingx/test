import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_output import DcManagerSubcloudListOutput


class DcManagerSubcloudListKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud list' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_list(self) -> DcManagerSubcloudListOutput:
        """Gets the 'dcmanager subcloud list' output.

        Args: None

        Returns:
            DcManagerSubcloudListOutput: a DcManagerSubcloudListOutput object representing
            the output of the command 'dcmanager subcloud list'.

        """
        output = self.ssh_connection.send(source_openrc("dcmanager subcloud list"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_subcloud_list_output = DcManagerSubcloudListOutput(output)

        return dcmanager_subcloud_list_output

    def validate_subcloud_status(self, subcloud_name: str, status: str) -> bool:
        """Validates the status of specified subcloud until reaches the desired status.

        Args:
            subcloud_name (str): a str name for the subcloud.
            status (str): a str status for the subcloud.

        Returns:
            bool: True if the subcloud reaches the desired status, False otherwise.

        Raises:
            Exception: if the subcloud is in a failed state.

        """
        failed_status = ["bootstrap-failed", "install-failed", "create-failed"]
        time_out = 3600
        polling_sleep_time = 60
        end_time = time.time() + time_out

        while time.time() < end_time:
            sc_list_out = self.get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
            sc_status = sc_list_out.get_deploy_status()
            msg = f"Subcloud {subcloud_name} is in {sc_status} state"
            if sc_status == status:
                return True
            else:
                if sc_status in failed_status:
                    raise Exception(msg)
            time.sleep(polling_sleep_time)
        get_logger().log_error(msg)
        raise TimeoutError(msg)
