from typing import Dict

from config.ptp.objects.ptp_nic_connection import PTPNicConnection
from config.ptp.objects.sma_connector import SMAConnector
from config.ptp.objects.ufl_connector import UFLConnector


class PTPNic:
    """
    Class to handle PTP NIC associated with the lab configuration.
    """

    def __init__(self, nic_name: str, nic_dict: Dict[str, str]):
        """
        Constructor.

        Args:
            nic_name (str): The name associated with this nic.
            nic_dict (Dict[str, str]): The dictionary read from the JSON config file associated with this NIC.

        """
        self.name = nic_name
        self.gpio_switch_port = None
        self.pci_slot = None
        self.base_port = None
        self.sma1 = None
        self.sma2 = None
        self.ufl1 = None
        self.ufl2 = None
        self.nic_connection = None
        self.conn_to_spirent = None
        self.spirent_port = None

        # Store the raw dictionary for JINJA templating.
        self.nic_dictionary = nic_dict

        if "gpio_switch_port" in nic_dict and nic_dict["gpio_switch_port"]:
            self.gpio_switch_port = nic_dict["gpio_switch_port"]

        if "pci_slot" in nic_dict and nic_dict["pci_slot"]:
            self.pci_slot = nic_dict["pci_slot"]

        if "base_port" in nic_dict and nic_dict["base_port"]:
            self.base_port = nic_dict["base_port"]

        if "nic_connection" in nic_dict and nic_dict["nic_connection"]:
            self.nic_connection = PTPNicConnection(self.name, nic_dict["nic_connection"])

        if "conn_to_spirent" in nic_dict and nic_dict["conn_to_spirent"]:
            self.conn_to_spirent = nic_dict["conn_to_spirent"]

        if "spirent_port" in nic_dict and nic_dict["spirent_port"]:
            self.spirent_port = nic_dict["spirent_port"]

    def __str__(self):
        """
        String representation of this object.

        Returns (str): String representation of this object.

        """
        return self.name

    def to_dictionary(self) -> Dict[str, str]:
        """
        This function will return a dictionary view of the PTPNic.

        This is mostly used for substitution in JINJA templates.

        Returns:
            Dict[str, str]: Dictionary representation

        """
        return self.nic_dictionary

    def get_name(self) -> str:
        """
        Gets the Name of this PTP NIC.

        Returns (str):
            The name of the NIC

        """
        return self.name

    def get_gpio_switch_port(self) -> str:
        """
        Gets the GPIO switch port.

        Returns (str):
            The GPIO switch port.

        """
        return self.gpio_switch_port

    def get_pci_slot(self) -> str:
        """
        Gets the pci slot

        Returns (str):
            The pci slot

        """
        return self.pci_slot

    def get_base_port(self) -> str:
        """
        Gets the base port.

        Returns (str):
            The base port.
        """
        return self.base_port

    def get_sma1(self) -> SMAConnector:
        """
        Gets the SMAConnector associated with sma1

        Returns (SMAConnector):
            The SMAConnector
        """
        return self.sma1

    def set_sma1(self, sma_connector: SMAConnector) -> None:
        """
        Sets the SMAConnector associated with sma1

        Args:
            sma_connector (SMAConnector): the SMAConnector

        Returns: None

        """
        self.sma1 = sma_connector

    def get_sma2(self) -> SMAConnector:
        """
        Gets the SMAConnector associated with sma2

        Returns (SMAConnector):
            The SMAConnector
        """
        return self.sma2

    def set_sma2(self, sma_connector: SMAConnector) -> None:
        """
        Sets the SMAConnector associated with sma2

        Args:
            sma_connector (SMAConnector): the SMAConnector

        Returns: None

        """
        self.sma2 = sma_connector

    def get_ufl1(self) -> UFLConnector:
        """
        Gets the UFLConnector associated with ufl1

        Returns (UFLConnector):
            The UFLConnector
        """
        return self.ufl1

    def set_ufl1(self, ufl_connector: UFLConnector) -> None:
        """
        Sets the UFLConnector associated with ufl1

        Args:
            ufl_connector (UFLConnector): the UFLConnector

        Returns: None

        """
        self.ufl1 = ufl_connector

    def get_ufl2(self) -> UFLConnector:
        """
        Gets the UFLConnector associated with ufl2

        Returns (UFLConnector):
            The UFLConnector
        """
        return self.ufl2

    def set_ufl2(self, ufl_connector: UFLConnector) -> None:
        """
        Sets the UFLConnector associated with ufl2

        Args:
            ufl_connector (UFLConnector): the UFLConnector

        Returns: None

        """
        self.ufl2 = ufl_connector

    def get_conn_to_spirent(self) -> str:
        """
        Gets the connection to Spirent.

        Returns (str):
            The connection to Spirent.
        """
        return self.conn_to_spirent

    def get_spirent_port(self) -> str:
        """
        Gets the Spirent port.

        Returns (str):
            The Spirent port.
        """
        return self.spirent_port
