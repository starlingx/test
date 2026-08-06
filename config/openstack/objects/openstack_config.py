from typing import List

import json5

from config.openstack.objects.custom_installer import CustomInstaller
from config.openstack.objects.remote_installer import RemoteInstaller


class OpenstackConfig:
    """
    Class to hold configuration of the openstack
    """

    def __init__(self, config):

        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the openstack config file: {config}")
            raise

        openstack_dict = json5.load(json_data)

        self.app_name = openstack_dict['app_name']
        self.version_cmd = openstack_dict['version_cmd']
        self.custom_config = CustomInstaller(openstack_dict["custom"])
        self.remote_config = RemoteInstaller(openstack_dict["remote"])


    def get_app_name(self) -> str:
        """Getter for the application name.

        Returns:
            str: The application name.
        """
        return self.app_name

    def set_app_name(self, app_name: str) -> None:
        """Set the application name (used for runtime override).

        Also updates the version_cmd path to match the new app name.

        Args:
            app_name (str): The detected application name.
        """
        old_app_name = self.app_name
        self.app_name = app_name
        if old_app_name in self.version_cmd:
            self.version_cmd = self.version_cmd.replace(old_app_name, app_name)

    def get_version_cmd(self) :
        """
        Getter for the application version command with file path.
        Returns: the command for retrieving application version.

        """
        return self.version_cmd

    def get_custom_config(self) -> CustomInstaller:
        """
        Getter for the custom config object.
        Returns: the custom config object.

        """

        return self.custom_config

    def get_remote_config(self) -> RemoteInstaller:
        """
        Getter for the remote config object.
        Returns: the custom  config object.

        """
        return self.remote_config
