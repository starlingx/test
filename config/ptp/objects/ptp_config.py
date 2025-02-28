from typing import Dict, List

import json5

from config.ptp.objects.ptp_host import PTPHost


class PTPConfig:
    """
    Class to hold configuration of the Cloud Platform's PTP Configuration.
    """

    def __init__(self, config):

        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the ptp config file: {config}")
            raise

        ptp_dict = json5.load(json_data)
        self.ptp_hosts = []
        for ptp_host in ptp_dict:
            host = PTPHost(ptp_host, ptp_dict[ptp_host])
            self.ptp_hosts.append(host)

    def __str__(self):
        """
        Returns the string representation for this class.

        Returns: (str)

        """
        return "PTPConfig"

    def get_all_hosts_dictionary(self) -> Dict[str, Dict]:
        """
        This function will return a dictionary view of the PTPConfig.

        This is mostly used for substitution in JINJA templates.

        Returns:
            Dict[str, Dict]: Dictionary representation

        """
        dictionary_view = {}
        for host in self.get_all_hosts():
            dictionary_view[host.get_name()] = host.get_all_nics_dictionary()

        return dictionary_view

    def get_all_hosts(self) -> List[PTPHost]:
        """
        Getter for the PTP information for every host defined in the config.

        Returns:
            List[PTPHost]: The list of all hosts.

        """
        return self.ptp_hosts

    def get_host(self, host_name: str) -> PTPHost:
        """
        Getter for the PTP information about the specified host_name.

        Args:
            host_name (str): Name of the host in the config.

        Returns:
            PTPHost: PTPHost

        """
        for host in self.ptp_hosts:
            if host.get_name() == host_name:
                return host
        raise Exception(f"There is no PTP Host called {host_name} in the PTP config.")
