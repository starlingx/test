from typing import Dict, List

from config.ptp.objects.ptp_nic import PTPNic
from config.ptp.objects.sma_connector import SMAConnector
from config.ptp.objects.ufl_connector import UFLConnector


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

        self.sma_connectors = self._extract_sma_connectors(host_dict)
        self.ufl_connectors = self._extract_ufl_connectors(host_dict)
        self.nics = self._extract_nics(host_dict)

        # Set the SMA and UFL values for every NIC.
        self._add_sma_connectors_to_nics()
        self._add_ufl_connectors_to_nics()

    def _extract_sma_connectors(self, host_dict: Dict[str, Dict]) -> List[SMAConnector]:
        """
        Build the SMAConnector objects from the dictionary

        Args:
            host_dict (Dict[str, Dict]): JSON representation of the Host config

        Returns:
            List[SMAConnector]: List of SMAConnector
        """
        sma_connectors = []
        if "sma_connectors" in host_dict:
            sma_connectors_dict = host_dict["sma_connectors"]
            for sma_connector_key in sma_connectors_dict.keys():
                sma_connector = SMAConnector(sma_connector_key, sma_connectors_dict[sma_connector_key])
                sma_connectors.append(sma_connector)

        return sma_connectors

    def _extract_ufl_connectors(self, host_dict: Dict[str, Dict]) -> List[UFLConnector]:
        """
        Build the UFLConnector objects from the dictionary

        Args:
            host_dict (Dict[str, Dict]): JSON representation of the Host config

        Returns:
            List[UFLConnector]: List of UFLConnector
        """
        ufl_connectors = []
        if "ufl_connectors" in host_dict:
            ufl_connectors_dict = host_dict["ufl_connectors"]
            for ufl_connector_key in ufl_connectors_dict.keys():
                ufl_connector = UFLConnector(ufl_connector_key, ufl_connectors_dict[ufl_connector_key])
                ufl_connectors.append(ufl_connector)

        return ufl_connectors

    def _extract_nics(self, host_dict: Dict[str, Dict]) -> List[PTPNic]:
        """
        Build the PTPNic objects from the dictionary

        Args:
            host_dict (Dict[str, Dict]): JSON representation of the Host config

        Returns:
            List[PTPNic]: List of PTPNic

        """
        nics = []
        if "nics" not in host_dict:
            raise Exception(f"You must provide 'nics' information for host {self.name}")
        nics_dict = host_dict["nics"]

        for nic_name in nics_dict.keys():
            nic = PTPNic(nic_name, nics_dict[nic_name])
            nics.append(nic)

        return nics

    def _add_sma_connectors_to_nics(self) -> None:
        """
        This function will adjust the PTPNic objects to be linked to the sma_connectors

        """
        for sma_connector in self.sma_connectors:

            input_nic_name = sma_connector.get_input_nic()
            input_nic = self.get_nic(input_nic_name)

            if sma_connector.get_input_sma() == "sma1":
                input_nic.set_sma1(sma_connector)
            elif sma_connector.get_input_sma() == "sma2":
                input_nic.set_sma2(sma_connector)
            else:
                raise Exception(f"sma_connectors can only be associated with sma1 or sma2. Invalid: {sma_connector.get_input_sma()}")

            output_nic_name = sma_connector.get_output_nic()
            output_nic = self.get_nic(output_nic_name)

            if sma_connector.get_output_sma() == "sma1":
                output_nic.set_sma1(sma_connector)
            elif sma_connector.get_output_sma() == "sma2":
                output_nic.set_sma2(sma_connector)
            else:
                raise Exception(f"sma_connectors can only be associated with sma1 or sma2. Invalid: {sma_connector.get_output_sma()}")

    def _add_ufl_connectors_to_nics(self) -> None:
        """
        This function will adjust the PTPNic objects to be linked to the ufl_connectors

        """
        for ufl_connector in self.ufl_connectors:

            input_nic_name = ufl_connector.get_input_nic()
            input_nic = self.get_nic(input_nic_name)

            if ufl_connector.get_input_ufl() == "ufl1":
                input_nic.set_ufl1(ufl_connector)
            elif ufl_connector.get_input_ufl() == "ufl2":
                input_nic.set_ufl2(ufl_connector)
            else:
                raise Exception(f"ufl_connectors can only be associated with ufl1 or ufl2. Invalid: {ufl_connector.get_input_ufl()}")

            output_nic_name = ufl_connector.get_output_nic()
            output_nic = self.get_nic(output_nic_name)

            if ufl_connector.get_output_ufl() == "ufl1":
                output_nic.set_ufl1(ufl_connector)
            elif ufl_connector.get_output_ufl() == "ufl2":
                output_nic.set_ufl2(ufl_connector)
            else:
                raise Exception(f"ufl_connectors can only be associated with ufl1 or ufl2. Invalid: {ufl_connector.get_output_ufl()}")

    def __str__(self):
        """
        String representation override.

        Returns (str): String representation of this object.

        """
        return self.name

    def get_all_nics_dictionary(self) -> Dict[str, Dict]:
        """
        This function will return a dictionary view of the PTPHost.

        This is mostly used for substitution in JINJA templates.

        Returns:
            Dict[str, Dict]: Dictionary representation

        """
        dictionary_view = {}
        for nic in self.get_all_nics():
            dictionary_view[nic.get_name()] = nic.to_dictionary()

        return dictionary_view

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
            (List[PTPNic]): All the nics

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
        raise Exception(f"There is no PTP NIC called {nic_name} associated with the host {self.name} in the PTP config.")
