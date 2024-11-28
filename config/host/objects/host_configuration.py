from typing import List

import json5
from config.lab.objects.credentials import Credentials


class HostConfiguration:
    def __init__(self, host_config):
        try:
            self.host_config_file = host_config
            json_data = open(host_config)
        except FileNotFoundError:
            print(f"Could not find the lab config file: {host_config}")
            raise

        lab_dict = json5.load(json_data)

        self.host = lab_dict['host']

        self.ssh_port: int = 22
        if 'ssh_port' in lab_dict:
            self.ssh_port = int(lab_dict['ssh_port'])

        self.credentials = Credentials(lab_dict['credentials'])

    def get_host(self) -> str:
        """
        Getter for host
        Returns:

        """
        return self.host

    def get_ssh_port(self) -> int:
        """
        Getter for the ssh_port
        Returns: The SSH port

        """
        return self.ssh_port

    def get_credentials(self) -> Credentials:
        """
        Getter for credentials
        Returns:

        """
        return self.credentials

    def get_host_config_file(self) -> str:
        """
        Getter for host config file
        Returns:

        """
        return self.host_config_file

    def to_log_strings(self) -> List[str]:
        """
        This function will return a list of strings that can be logged to show all the Host Config.
        Returns: A List of strings to be sent to the logger.

        """
        log_strings = []
        log_strings.append(f"host: {self.get_host()}")
        log_strings.append(f"ssh_port: {self.get_ssh_port()}")
        log_strings.append(f"admin_credentials: {self.get_credentials().to_string()}")

        return log_strings
