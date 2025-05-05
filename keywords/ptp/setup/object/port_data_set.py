from typing import Any, Dict


class PortDataSet:
    """
    Class models a port data set
    """

    def __init__(self, expected_dict: Dict[str, Any]):
        """
        Constructor.

        Args:
            expected_dict (Dict[str, Any]): The dictionary read from the JSON setup template file associated with this port data set

        """
        self.port_identity = None
        if "interface" in expected_dict:
            self.interface = expected_dict["interface"]

        self.port_state = None
        if "port_state" in expected_dict:
            self.port_state = expected_dict["port_state"]

        self.parent_port_identity = None
        if "parent_port_identity" in expected_dict:
            self.parent_port_identity = expected_dict["parent_port_identity"]

    def get_interface(self) -> str:
        """
        Gets the interface.

        Returns:
            str: The interface.
        """
        return self.interface

    def get_port_state(self) -> str:
        """
        Gets the port state.

        Returns:
            str: The port state.
        """
        return self.port_state

    def get_parent_port_identity(self) -> str:
        """
        Gets the parent port identity.

        Returns:
            str: The parent port identity.
        """
        return self.parent_port_identity
