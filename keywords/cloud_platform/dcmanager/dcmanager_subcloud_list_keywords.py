import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
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
        failed_status = ["bootstrap-failed", "install-failed", "create-failed", "config-failed", "pre-enroll-failed", "enroll-failed", "pre-init-enroll-failed", "init-enroll-failed"]
        time_out = 4800
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

    def validate_subcloud_availability_status(self, subcloud_name: str) -> bool:
        """Validates the availability status of the specified subcloud until reaches online state.

        Args:
            subcloud_name (str): a str name for the subcloud.

        Returns:
            bool: True if the subcloud reaches the desired status.

        Raises:
            Exception: if the subcloud is offline.

        """

        def get_availability():
            sc_list_out = self.get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
            sc_availability = sc_list_out.get_availability()
            msg = f"Subcloud {subcloud_name} is in {sc_availability} state"
            get_logger().log_info(msg)

            return sc_availability

        validate_equals_with_retry(get_availability, "online", "Validate if subcloud is in online state.")

    def validate_subcloud_sync_status(self, subcloud_name: str, expected_sync_status: str) -> None:
        """
        Validates the sync status of the specified subcloud. The function will raise if the expected_sync_status isn't reached.

        Args:
            subcloud_name (str): a str name for the subcloud.
            expected_sync_status (str): The expected sync status of the subcloud. e.g. 'in-sync'

        """

        def get_sync():
            sc_list_out = self.get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
            actual_sync_status = sc_list_out.get_sync()
            get_logger().log_info(f"Subcloud {subcloud_name} is {actual_sync_status}")

            return actual_sync_status

        validate_equals_with_retry(get_sync, expected_sync_status, f"Sync status of {subcloud_name}", timeout=1200)
