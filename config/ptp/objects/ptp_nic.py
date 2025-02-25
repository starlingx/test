from typing import Dict


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
        self.gnss_switch_port = None
        self.sma1_to_nic1 = None
        self.sma2_to_nic1 = None
        self.sma1_to_nic2 = None
        self.sma2_to_nic2 = None
        self.base_port = None
        self.conn_to_ctrl0_nic1 = None
        self.conn_to_ctrl0_nic2 = None
        self.conn_to_ctrl1_nic1 = None
        self.conn_to_ctrl1_nic2 = None
        self.conn_to_spirent = None
        self.spirent_port = None

        if "gnss_switch_port" in nic_dict and nic_dict["gnss_switch_port"]:
            self.gnss_switch_port = nic_dict["gnss_switch_port"]

        if "sma1_to_nic1" in nic_dict and nic_dict["sma1_to_nic1"]:
            self.sma1_to_nic1 = nic_dict["sma1_to_nic1"]

        if "sma2_to_nic1" in nic_dict and nic_dict["sma2_to_nic1"]:
            self.sma2_to_nic1 = nic_dict["sma2_to_nic1"]

        if "sma1_to_nic2" in nic_dict and nic_dict["sma1_to_nic2"]:
            self.sma1_to_nic2 = nic_dict["sma1_to_nic2"]

        if "sma2_to_nic2" in nic_dict and nic_dict["sma2_to_nic2"]:
            self.sma2_to_nic2 = nic_dict["sma2_to_nic2"]

        if "base_port" in nic_dict and nic_dict["base_port"]:
            self.base_port = nic_dict["base_port"]

        if "conn_to_ctrl0_nic1" in nic_dict and nic_dict["conn_to_ctrl0_nic1"]:
            self.conn_to_ctrl0_nic1 = nic_dict["conn_to_ctrl0_nic1"]

        if "conn_to_ctrl0_nic2" in nic_dict and nic_dict["conn_to_ctrl0_nic2"]:
            self.conn_to_ctrl0_nic2 = nic_dict["conn_to_ctrl0_nic2"]

        if "conn_to_ctrl1_nic1" in nic_dict and nic_dict["conn_to_ctrl1_nic1"]:
            self.conn_to_ctrl1_nic1 = nic_dict["conn_to_ctrl1_nic1"]

        if "conn_to_ctrl1_nic2" in nic_dict and nic_dict["conn_to_ctrl1_nic2"]:
            self.conn_to_ctrl1_nic2 = nic_dict["conn_to_ctrl1_nic2"]

        if "conn_to_spirent" in nic_dict and nic_dict["conn_to_spirent"]:
            self.conn_to_spirent = nic_dict["conn_to_spirent"]

        if "spirent_port" in nic_dict and nic_dict["spirent_port"]:
            self.spirent_port = nic_dict["spirent_port"]

    def __str__(self):
        """
        String representation of this object.

        Returns (str): String representation of this object.

        """
        return f"PTPNic - {self.name}"

    def get_name(self) -> str:
        """
        Gets the Name of this PTP NIC.

        Returns (str):
            The name of the NIC

        """
        return self.name

    def get_gnss_switch_port(self) -> str:
        """
        Gets the GNSS switch port.

        Returns (str):
            The GNSS switch port.

        """
        return self.gnss_switch_port

    def get_sma1_to_nic1(self) -> str:
        """
        Gets the SMA1 to NIC1 connection.

        Returns (str):
            The SMA1 to NIC1 connection.
        """
        return self.sma1_to_nic1

    def get_sma2_to_nic1(self) -> str:
        """
        Gets the SMA2 to NIC1 connection.

        Returns (str):
            The SMA2 to NIC1 connection.
        """
        return self.sma2_to_nic1

    def get_sma1_to_nic2(self) -> str:
        """
        Gets the SMA1 to NIC2 connection.

        Returns (str):
            The SMA1 to NIC2 connection.
        """
        return self.sma1_to_nic2

    def get_sma2_to_nic2(self) -> str:
        """
        Gets the SMA2 to NIC2 connection.

        Returns (str):
            The SMA2 to NIC2 connection.
        """
        return self.sma2_to_nic2

    def get_base_port(self) -> str:
        """
        Gets the base port.

        Returns (str):
            The base port.
        """
        return self.base_port

    def get_conn_to_ctrl0_nic1(self) -> str:
        """
        Gets the connection to controller 0 NIC1.

        Returns (str):
            The connection to controller 0 NIC1.
        """
        return self.conn_to_ctrl0_nic1

    def get_conn_to_ctrl0_nic2(self) -> str:
        """
        Gets the connection to controller 0 NIC2.

        Returns (str):
            The connection to controller 0 NIC2.
        """
        return self.conn_to_ctrl0_nic2

    def get_conn_to_ctrl1_nic1(self) -> str:
        """
        Gets the connection to controller 1 NIC1.

        Returns (str):
            The connection to controller 1 NIC1.
        """
        return self.conn_to_ctrl1_nic1

    def get_conn_to_ctrl1_nic2(self) -> str:
        """
        Gets the connection to controller 1 NIC2.

        Returns (str):
            The connection to controller 1 NIC2.
        """
        return self.conn_to_ctrl1_nic2

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
