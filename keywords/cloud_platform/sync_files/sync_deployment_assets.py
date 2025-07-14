import os

from config.configuration_manager import ConfigurationManager
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords


class SyncDeploymentAssets:
    """
    A class for sync deployment assets in between controllers.
    """

    def __init__(self, ssh_connection: str):
        """Initializes AnsiblePlaybookKeywords with an SSH connection.

        Args:
            ssh_connection (str): SSH connection to the target system.

        """
        self.ssh_connection = ssh_connection

    def sync_assets(self):
        """Function to Sync assets between active and standby controllers"""
        # Sync the lab configuration between active and standby controller
        lab_config = ConfigurationManager.get_lab_config()
        password = lab_config.get_admin_credentials().get_password()
        user = lab_config.get_admin_credentials().get_user_name()
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()

        # get the source controller from where we have to copy data
        src_controller = LabConnectionKeywords().get_ssh_for_hostname(deployment_assets_config.get_controller_deployment_assets().get_controller_name())
        deployment_config_file = deployment_assets_config.get_controller_deployment_assets().get_deployment_config_file()
        base_file_path = f"{os.path.dirname(deployment_config_file)}/"

        # get other controlller name
        dest_controller = lab_config.get_counterpart_controller(src_controller.get_name())
        # rsync files
        file_kw = FileKeywords(src_controller)
        file_kw.rsync_to_remote_server(base_file_path, dest_controller.get_name(), user, password, base_file_path, True)
