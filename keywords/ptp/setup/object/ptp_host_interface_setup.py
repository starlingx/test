from typing import Any, Dict, List


class PTPHostInterfaceSetup:
    """
    This class models a PTP Host interface setup.
    """

    def __init__(self, setup_dict: Dict[str, Any]):
        """
        Constructor.

        Args:
            setup_dict (Dict[str, Any]): The dictionary read from the JSON setup template file associated with this ptp host interface setup.

        """
        if "name" not in setup_dict:
            raise Exception("Every ptp host interface entry should have a name.")
        self.name = setup_dict["name"]

        if "ptp_interface_parameter" not in setup_dict:
            raise Exception(f"The ptp host interface entry {self.name} must have ptp_interface_parameter defined.")
        self.ptp_interface_parameter = setup_dict["ptp_interface_parameter"]

        if "controller_0_interfaces" not in setup_dict:
            raise Exception(f"The ptp host interface entry {self.name} must have controller_0_interfaces defined.")
        self.controller_0_interfaces = setup_dict["controller_0_interfaces"]

        if "controller_1_interfaces" not in setup_dict:
            raise Exception(f"The ptp host interface entry {self.name} must have controller_1_interfaces defined.")
        self.controller_1_interfaces = setup_dict["controller_1_interfaces"]

    def __str__(self):
        """
        String representation of this object.

        Returns:
            str: String representation of this object.

        """
        return self.get_name()

    def get_name(self) -> str:
        """
        Gets the name of this ptp host interface setup.

        Returns:
            str: The name of this ptp host interface setup.
        """
        return self.name

    def get_ptp_interface_parameter(self) -> str:
        """
        Gets the ptp_interface_parameter of this ptp host interface setup.

        Returns:
            str: The ptp_interface_parameter of this ptp host interface setup.
        """
        return self.ptp_interface_parameter

    def get_controller_0_interfaces(self) -> List[str]:
        """
        Gets the controller_0_interfaces of this ptp host interface setup.

        Returns:
            List[str]: The controller_0_interfaces of this ptp host interface setup.
        """
        return self.controller_0_interfaces

    def get_controller_1_interfaces(self) -> List[str]:
        """
        Gets the controller_1_interfaces of this ptp host interface setup.

        Returns:
            List[str]: The controller_1_interfaces of this ptp host interface setup.
        """
        return self.controller_1_interfaces
