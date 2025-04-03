from config.configuration_manager import ConfigurationManager
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

    def dcmanager_subcloud_prestage(self, subcloud_name: str, syspass: str) -> None:
        """
        Runs dcmanager subcloud prestage command.

        Args:
            subcloud_name (str): The name of the subcloud to check.
            syspass (str): The sysadmin password to be passed to the command.

        """
        lab_config = ConfigurationManager.get_lab_config()
        pasw = lab_config.get_admin_credentials().get_password()

        command = source_openrc(f"dcmanager subcloud prestage --for-sw-deploy {subcloud_name}" f" --sysadmin-password {pasw}")

        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        # Wait for the subcloud to acheive 'prestaging-packages' status
        self.wait_for_prestage(prestaging_packages=True, subcloud=subcloud_name, check_interval=2, timeout=10)

        # Wait for the subcloud to complete prestage operation
        self.wait_for_prestage(subcloud=subcloud_name)

    def wait_for_prestage(
        self,
        subcloud: str,
        prestaging_packages: bool = False,
        check_interval: int = 30,
        timeout: int = 120,
    ) -> None:
        """
        Waits for the prestage verification to be completed.

        Args:
            subcloud (str): Subcloud name.
            prestaging_packages (bool): Sets the value to check if should wait for prestaging-packages status or complete status.
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
                return prestaged == "prestaging-packages"
            else:
                return prestaged == "complete"

        validate_equals_with_retry(
            function_to_execute=check_prestage,
            expected_value=True,
            validation_description=f"Waiting for {subcloud} prestage.",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )
