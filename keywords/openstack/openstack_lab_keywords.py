from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class OpenstackLabKeywords(BaseKeyword):
    """Keywords for OpenStack lab setup and cleanup operations."""

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def setup_lab(self, script_path: str = "./lab_setup.sh", config_file: str = "lab_setup.conf") -> object:
        """
        Execute lab setup script.

        Args:
            script_path (str): Path to lab setup script
            config_file (str): Configuration file for setup

        Returns:
            object: Command output or None if script not found
        """
        get_logger().log_info(f"Executing lab setup script: {script_path}")
        if not FileKeywords(self.ssh_connection).file_exists(script_path):
            get_logger().log_error(f"{script_path} file not found on controller")
            return None

        FileKeywords(self.ssh_connection).make_executable(script_path)
        command = export_k8s_config(f"{script_path} -f {config_file}")
        cmd_out = self.ssh_connection.send(command, reconnect_timeout=3600)
        get_logger().log_info(cmd_out)
        return cmd_out

    def cleanup_lab(self, script_path: str = "./lab_cleanup.sh") -> object:
        """
        Execute lab cleanup script.

        Args:
            script_path (str): Path to lab cleanup script

        Returns:
            object: Command output or None if script not found
        """
        get_logger().log_info(f"Executing lab cleanup script: {script_path}")
        if not FileKeywords(self.ssh_connection).file_exists(script_path):
            get_logger().log_error(f"{script_path} file not found on controller")
            return None

        FileKeywords(self.ssh_connection).make_executable(script_path)
        cleanup_cmd = export_k8s_config(script_path)
        cleanup_out = self.ssh_connection.send(cleanup_cmd, reconnect_timeout=7200)
        get_logger().log_info(cleanup_out)
        return cleanup_out
