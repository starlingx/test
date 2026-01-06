from typing import Any, Dict, List

from config.configuration_manager import ConfigurationManager


class PTPHostInterfaceSetup:
    """
    This class models a PTP Host interface setup.
    """

    def __init__(self, setup_dict: Dict[str, Any]):
        """
        Constructor.

        Args:
            setup_dict (Dict[str, Any]): The dictionary read from the JSON setup template file associated with this ptp host interface setup.

        Raises:
            Exception: If the setup_dict does not contain required keys.
            Exception: If the setup_dict does not contain required PTPHostInterfaceSetup entries.
            Exception: If the setup_dict does not contain required controller interfaces.
            Exception: If the setup_dict does not contain required compute interfaces.
        """
        lab_type = ConfigurationManager.get_lab_config().get_lab_type()

        if "name" not in setup_dict:
            raise Exception("Every ptp host interface entry should have a name.")
        self.name = setup_dict["name"]

        if "ptp_interface_parameter" not in setup_dict:
            raise Exception(f"The ptp host interface entry {self.name} must have ptp_interface_parameter defined.")
        self.ptp_interface_parameter = setup_dict["ptp_interface_parameter"]

        if "controller_0_interfaces" not in setup_dict:
            raise Exception(f"The ptp host interface entry {self.name} must have controller_0_interfaces defined.")
        self.controller_0_interfaces = setup_dict["controller_0_interfaces"]

        if "controller_1_interfaces" not in setup_dict and lab_type != "Simplex":
            raise Exception(f"The ptp host interface entry {self.name} must have controller_1_interfaces defined.")
        self.controller_1_interfaces = setup_dict.get("controller_1_interfaces")

        self.compute_0_interfaces = None
        if "compute_0_interfaces" in setup_dict:
            self.compute_0_interfaces = setup_dict.get("compute_0_interfaces")

    def __str__(self) -> str:
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

    def get_interfaces_for_hostname(self, hostname: str) -> List[str]:
        """
        Gets the interfaces for the given hostname in this PTP host interface setup.

        Args:
            hostname (str): The name of the host.

        Returns:
            List[str]: The interfaces for the given hostname in this PTP host interface setup.
        """
        interfaces_to_hostname_mapping = {
            "controller-0": self.controller_0_interfaces,
            "controller-1": self.controller_1_interfaces,
            "compute-0": self.compute_0_interfaces,
        }
        return interfaces_to_hostname_mapping.get(hostname)
