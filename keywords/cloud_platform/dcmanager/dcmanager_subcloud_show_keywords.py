import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_show_output import DcManagerSubcloudShowOutput


class DcManagerSubcloudShowKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud show' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_show(self, subcloud_name: str) -> DcManagerSubcloudShowOutput:
        """Gets the 'dcmanager subcloud show <subcloud name>' output.

        Args:
            subcloud_name (str): The name of the subcloud to show.

        Returns:
            DcManagerSubcloudShowOutput: a DcManagerSubcloudShowOutput object representing the
            output of the command 'dcmanager subcloud show <subcloud name>'.
        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager subcloud show {subcloud_name}"))
        self.validate_success_return_code(self.ssh_connection)
        return DcManagerSubcloudShowOutput(output)

    def wait_for_state(self, subcloud_name: str, field: str, expected_status: str, timeout: int = 300, check_interval: int = 10) -> DcManagerSubcloudShowOutput:
        """
        Waits for the subcloud to reach a specific state.

        Args:
            subcloud_name (str): The name of the subcloud.
            field (str): The field to check in the subcloud status.
            expected_status (str): The expected status of the field.
            timeout (int): Maximum time to wait for the status change.
            check_interval (int): Time interval between checks.

        Returns:
            DcManagerSubcloudShowOutput: The output of the subcloud show command when the expected status is reached.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            sc_show_obj = self.get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object()
            # Dynamically call the method
            method_name = f"get_{field}"
            result = getattr(sc_show_obj, method_name)()  # Call the method
            if result == expected_status:
                return sc_show_obj
            get_logger().log_info(f"Waiting for {field} to reach state '{expected_status}'. Current state: '{result}'")
            # Sleep for the specified interval before checking again
            time.sleep(check_interval)
        raise TimeoutError(f"Timed out waiting for {field} to reach state '{expected_status}' after {timeout} seconds.")
