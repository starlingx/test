from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.object.system_application_update_input import SystemApplicationUpdateInput
from keywords.cloud_platform.system.application.system_application_update_keywords import SystemApplicationUpdateKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class OpenstackUtilityKeywords(BaseKeyword):
    """Utility keywords for OpenStack application management."""

    def __init__(self, ssh_connection: SSHConnection, app_name):
        self.app_name = app_name
        self.ssh_connection = ssh_connection

    def download_upgrade_package(self, url: str, output_file: str) -> bool:
        """
        Download upgrade package from URL.

        Args:
            url (str): URL to download from
            output_file (str): Output file path

        Returns:
            bool: True if download successful, False otherwise
        """
        download_cmd = f"wget -O {output_file} {url}"
        self.ssh_connection.send(download_cmd)
        return self.ssh_connection.get_return_code() == 0

    def update_application(self, tar_file_path: str, timeout: int = 3600, check_interval: int = 30) -> object:
        """
        Update application with tar file.

        Args:
            tar_file_path (str): Path to tar file
            timeout (int): Timeout in seconds
            check_interval (int): Check interval in seconds

        Returns:
            object: Result of system application update
        """
        update_input = SystemApplicationUpdateInput()
        update_input.set_app_name(self.app_name)
        update_input.set_tar_file_path(tar_file_path)
        update_input.set_timeout_in_seconds(timeout)
        update_input.set_check_interval_in_seconds(check_interval)
        return SystemApplicationUpdateKeywords(self.ssh_connection).system_application_update(update_input)

    def execute_script(self, script_path: str, args: str = "", timeout: int = 3600) -> object:
        """
        Execute a script on the controller.

        Args:
            script_path (str): Path to script
            args (str): Script arguments
            timeout (int): Timeout in seconds

        Returns:
            object: Script output or None if script not found
        """
        if not FileKeywords(self.ssh_connection).file_exists(script_path):
            return None
        FileKeywords(self.ssh_connection).make_executable(script_path)
        command = export_k8s_config(f"{script_path} {args}")
        return self.ssh_connection.send(command, command_timeout=timeout, reconnect_timeout=timeout)
