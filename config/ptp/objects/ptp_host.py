from typing import Dict, List

from config.ptp.objects.ptp_nic import PTPNic


class PTPHost:
    """
    Class to handle PTP-specific information about Hosts and NICs associated with the lab configuration.
    """

    def __init__(self, host_name: str, host_dict: Dict[str, Dict]):
        """
        Constructor.

        Args:
            host_name (str): The name of the host associated with this PTP configuration
            host_dict (Dict[str, Dict]): The dictionary read from the JSON config file associated with this Host. It contains NIC cards information.

        """
        self.name = host_name
        self.nics = []
        for nic_name in host_dict:
            nic = PTPNic(nic_name, host_dict[nic_name])
            self.nics.append(nic)

    def __str__(self):
        """
        String representation override.

        Returns (str): String representation of this object.

        """
        return f"PTPHost - {self.name}"

    def get_name(self) -> str:
        """
        Getter for the name of this ptp_host.

        Returns (str): The name of this ptp_host

        """
        return self.name

    def get_all_nics(self) -> List[PTPNic]:
        """
        Getter for the NIC information associated with this host.

        Returns
            List[PTPNic]: All the nics

        """
        return self.nics

    def get_nic(self, nic_name: str) -> PTPNic:
        """
        Getter for the information about the specified NIC.

        Args:
            nic_name (str): Name of the NIC in the config

        Returns:
            PTPNic: The NIC object with the specified name.

        """
        for nic in self.nics:
            if nic.get_name() == nic_name:
                return nic
        raise Exception(
            f"There is no PTP NIC called {nic_name} associated with the host {self.name} in the PTP config."
        )
