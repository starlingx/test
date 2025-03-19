from typing import Dict


class PTPNicConnection:
    """
    Class to handle a PTP Connection between nics on different controllers.
    """

    def __init__(self, from_nic: str, nic_connection_dict: Dict[str, str]):
        """
        Constructor.

        Args:
            from_nic (str): The nic of this nic_connection
            nic_connection_dict (Dict[str, str]): The dictionary read from the JSON config file associated with this NIC Connection.

        """
        self.validate_nic_connection_dict(nic_connection_dict)

        self.from_nic = from_nic
        self.to_host = nic_connection_dict["to_host"]
        self.to_nic = nic_connection_dict["to_nic"]
        self.interface = nic_connection_dict["interface"]

    def __str__(self):
        """
        String representation of this object.

        Returns (str): String representation of this object.

        """
        return f"{self.from_nic} to {self.to_host}:{self.to_nic}"

    def validate_nic_connection_dict(self, nic_connection_dict: Dict[str, str]) -> None:
        """
        Checks if the nic_connection_dict contains all the necessary fields.

        Args:
            nic_connection_dict (Dict[str, str]): Dictionary from the config.

        """
        required_fields = ["to_host", "to_nic", "interface"]
        for field in required_fields:
            if field not in nic_connection_dict:
                raise Exception(f"Invalid PTP config. NIC connection is missing required field: {field}")

    def get_from_nic(self) -> str:
        """
        Retrieves the source NIC of the NIC connection.

        Returns (str):
            The source NIC.
        """
        return self.from_nic

    def get_to_host(self) -> str:
        """
        Retrieves the destination host of the NIC connection.

        Returns (str):
            The destination host.
        """
        return self.to_host

    def get_to_nic(self) -> str:
        """
        Retrieves the destination NIC of the NIC connection.

        Returns (str):
            The destination NIC.
        """
        return self.to_nic

    def get_interface(self) -> str:
        """
        Retrieves the interface from the NIC connection.

        Returns (str):
            The interface.
        """
        return self.interface
