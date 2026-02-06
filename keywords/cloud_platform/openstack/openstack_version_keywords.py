from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_not_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


class OpenStackVersionKeywords(BaseKeyword):
    """
    Class for OpenStack version keywords
    """

    def __init__(self, ssh_connection: SSHConnection = None):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh object, if None will get active controller
        """
        self.ssh_connection = ssh_connection

    def get_openstack_version(self) -> dict:
        """
        Gets the current OpenStack version information

        Returns:
            dict: Dictionary containing app_name, app_version, and app_build_date
        """
        cmd = ConfigurationManager.get_openstack_config().get_version_cmd()
        
        ssh_connection = self.ssh_connection
        if not ssh_connection:
            lab_connect_keywords = LabConnectionKeywords()
            ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        
        cmd_out = ssh_connection.send(cmd)
        
        if cmd_out:
            version_info = {
                "app_name": cmd_out[0],
                "app_version": cmd_out[1], 
                "app_build_date": cmd_out[-1]
            }
            
            get_logger().log_info(f"App Name: {version_info['app_name']}")
            get_logger().log_info(f"App Version: {version_info['app_version']}")
            get_logger().log_info(f"App Build Date: {version_info['app_build_date']}")
            
            return version_info
        
        return {}

    def compare_versions(self, before_version: dict, after_version: dict) -> None:
        """
        Compares OpenStack versions before and after install/update

        Args:
            before_version (dict): Version info before operation
            after_version (dict): Version info after operation
        """
        get_logger().log_info("Comparing OpenStack versions:")
        get_logger().log_info(f"Before - Version: {before_version.get('app_version', 'N/A')}, Build Date: {before_version.get('app_build_date', 'N/A')}")
        get_logger().log_info(f"After - Version: {after_version.get('app_version', 'N/A')}, Build Date: {after_version.get('app_build_date', 'N/A')}")
        
        validate_not_equals(after_version.get('app_version'), before_version.get('app_version'), "OpenStack version should change after update")