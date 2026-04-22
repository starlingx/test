from framework.exceptions.validation_failure_error import ValidationFailureError
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords


class DcmanagerSubcloudPrestage(BaseKeyword):
    """
    This class executes subcloud prestage command
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_prestage(self, subcloud_name: str, syspass: str, release: str = None, for_sw_deploy: bool = False, wait_completion: bool = True) -> bool:
        """
        Runs dcmanager subcloud prestage command.

        Args:
            subcloud_name (str): The name of the subcloud to check.
            syspass (str): The sysadmin password to be passed to the command.
            release (str): Release to use for prestage.
            for_sw_deploy (bool): whether to enable --for-sw-deploy flag.
            wait_completion (bool): whether to wait for prestage to complete
        Returns:
            bool: If prestage succeeded.

        """
        cmd_options = f"--release {release}" if release else ""
        cmd_options += " --for-sw-deploy" if for_sw_deploy else ""
        command = source_openrc(f"dcmanager subcloud prestage {cmd_options} {subcloud_name}" f" --sysadmin-password {syspass}")

        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        try:
            # Wait for the subcloud to acheive 'prestaging-packages' status
            self.wait_for_prestage(prestaging_packages=True, subcloud=subcloud_name, check_interval=2, timeout=10)

            if wait_completion:
                # Wait for the subcloud to complete prestage operation
                self.wait_for_prestage(subcloud=subcloud_name)

            return True
        except ValidationFailureError:
            return False

    def wait_for_prestage(
        self,
        subcloud: str,
        prestaging_packages: bool = False,
        check_interval: int = 10,
        timeout: int = 600,
    ) -> None:
        """
        Waits for the prestage verification to be completed.

        Args:
            subcloud (str): Subcloud name.
            prestaging_packages (bool): Sets the value to check if should wait for prestaging status or complete status.
            check_interval (int): Interval to wait before looping again.
            timeout (int): Sets the await timeout.
        """

        def check_prestage() -> bool:
            """
            Checks if the prestage has been completed.

            Returns:
                bool: If prestage status is correct.
            """
            prestaged = DcManagerSubcloudShowKeywords(self.ssh_connection).get_dcmanager_subcloud_show(subcloud).get_dcmanager_subcloud_show_object().get_prestage_status()
            if prestaging_packages:
                return prestaged == "prestaging"
            else:
                if prestaged == "failed":
                    return "prestage failed"
                else:
                    return prestaged == "complete"

        validate_equals_with_retry(function_to_execute=check_prestage, expected_value=True, validation_description=f"Waiting for {subcloud} prestage.", timeout=timeout, polling_sleep_time=check_interval, failure_values=["prestage failed"])
