import os

from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
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

    def sync_subcloud_assets(self, subcloud_name: str, destination_ssh: SSHConnection):
        """
        Sync all deployment assets of a given subcloud from the origin controller to the destination system controller.

        Args:
            subcloud_name (str): Name of the subcloud to sync.
            destination_ssh (SSHConnection): SSH connection object for the destination system controller.
        """
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        lab_config = ConfigurationManager.get_lab_config()
        user = lab_config.get_admin_credentials().get_user_name()
        password = lab_config.get_admin_credentials().get_password()

        # Get the subcloud assets folder path on origin
        subcloud_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        origin_folder = os.path.dirname(subcloud_assets.get_bootstrap_file()) + "/"

        # Ensure the folder exists on the destination
        FileKeywords(destination_ssh).create_directory(origin_folder)

        # Rsync the folder recursively from origin to destination
        FileKeywords(self.ssh_connection).rsync_to_remote_server(local_dest_path=origin_folder, remote_server=destination_ssh.get_name(), remote_user=user, remote_password=password, remote_path=origin_folder, recursive=True)
