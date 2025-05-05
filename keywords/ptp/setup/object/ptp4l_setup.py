from typing import Any, Dict, List

from keywords.ptp.setup.object.ptp_host_interface_setup import PTPHostInterfaceSetup


class PTP4LSetup:
    """
    Class models a ptp4l setup
    """

    def __init__(self, setup_dict: Dict[str, Any], ptp_host_ifs_dict: Dict[str, PTPHostInterfaceSetup]):
        """
        Constructor.

        Args:
            setup_dict (Dict[str, Any]): The dictionary read from the JSON setup template file associated with this ptp4l setup.
            ptp_host_ifs_dict (Dict[str, PTPHostInterfaceSetup]): The dictionary that maps the name of thePTPHostInterfaceSetup to its associated object.

        """
        if "name" not in setup_dict:
            raise Exception("Every PTP4L entry should have a name.")
        self.name = setup_dict["name"]

        if "instance_hostnames" not in setup_dict:
            raise Exception(f"The ptp4l entry {self.name} must have instance_hostnames defined.")
        self.instance_hostnames = setup_dict["instance_hostnames"]

        if "instance_parameters" not in setup_dict:
            raise Exception(f"The ptp4l entry {self.name} must have instance_parameters defined.")
        self.instance_parameters = setup_dict["instance_parameters"]

        if "ptp_interface_names" not in setup_dict:
            raise Exception(f"The ptp4l entry {self.name} must have ptp_interface_names defined.")

        ptp_interfaces = []
        for ptp_interface_name in setup_dict["ptp_interface_names"]:
            if ptp_interface_name not in ptp_host_ifs_dict:
                raise Exception(f"The ptp_host_if entry {ptp_interface_name} must be defined.")
            ptp_interfaces.append(ptp_host_ifs_dict[ptp_interface_name])
        self.ptp_interfaces = ptp_interfaces

    def __str__(self) -> str:
        """
        String representation of this object.

        Returns:
            str: String representation of this object.

        """
        return self.get_name()

    def get_name(self) -> str:
        """
        Gets the name of this ptp4l setup.

        Returns:
            str: The name of this ptp4l setup.
        """
        return self.name

    def get_instance_hostnames(self) -> list[str]:
        """
        Gets the list of instance hostnames.

        Returns:
            list[str]: The list of instance hostnames.
        """
        return self.instance_hostnames

    def get_instance_parameters(self) -> str:
        """
        Gets the instance parameters as a string.

        Returns:
            str: The  instance parameters as a string
        """
        return self.instance_parameters

    def get_ptp_interfaces(self) -> List[PTPHostInterfaceSetup]:
        """
        Gets the list of PTP interfaces.

        Returns:
            List[PTPHostInterfaceSetup]: The list of PTP interfaces.
        """
        return self.ptp_interfaces

    def get_ptp_interface(self, interface_name: str) -> PTPHostInterfaceSetup:
        """
        Gets the PTP interface with the name specified

        Args:
            interface_name (str): Name of the interface that we are looking for

        Returns:
            PTPHostInterfaceSetup: the matching setup
        """
        for ptp_interface in self.ptp_interfaces:
            if ptp_interface.get_name() == interface_name:
                return ptp_interface
        raise Exception(f"There is no ptp interface named {interface_name} in the ptp4l setup.")
