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

        # GNSS server information
        self.gnss_server_host = ptp_dict["gnss_server_host"]
        self.gnss_server_username = ptp_dict["gnss_server_username"]
        self.gnss_server_password = ptp_dict["gnss_server_password"]

        # Extract the NIC Connections and Host information from the dictionary
        self.ptp_hosts = self._extract_ptp_hosts(ptp_dict)

    def get_gnss_server_host(self) -> str:
        """
        Getter for the GNSS server host.

        Returns:
            str: gnss server host
        """
        return self.gnss_server_host

    def get_gnss_server_username(self) -> str:
        """
        Getter for the GNSS server username.

        Returns:
            str: gnss server username
        """
        return self.gnss_server_username

    def get_gnss_server_password(self) -> str:
        """
        Getter for the GNSS server password.

        Returns:
            str: gnss server password
        """
        return self.gnss_server_password

    def _extract_ptp_hosts(self, ptp_dict: Dict[str, str]) -> List[PTPHost]:
        """
        Build the PTPHost objects from the dictionary

        Args:
            ptp_dict (Dict[str, str]): JSON representation of the PTP config

        Returns:
            List[PTPHost]: List of PTPHost
        """
        ptp_hosts = []
        ptp_hosts_dict = {}
        if "hosts" in ptp_dict:
            ptp_hosts_dict = ptp_dict["hosts"]

        for ptp_host_name in ptp_hosts_dict.keys():
            host = PTPHost(ptp_host_name, ptp_hosts_dict[ptp_host_name])
            ptp_hosts.append(host)

        return ptp_hosts

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
