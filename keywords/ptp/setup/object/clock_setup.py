from typing import Any, Dict, List

from keywords.ptp.setup.object.ptp_host_interface_setup import PTPHostInterfaceSetup


class ClockSetup:
    """
    Class models a clock setup
    """

    def __init__(self, setup_dict: Dict[str, Any], ptp_host_ifs_dict: Dict[str, PTPHostInterfaceSetup]):
        """
        Constructor.

        Args:
            setup_dict (Dict[str, Any]): The dictionary read from the JSON setup template file associated with this clock setup.
            ptp_host_ifs_dict (Dict[str, PTPHostInterfaceSetup]): The dictionary that maps the name of thePTPHostInterfaceSetup to its associated object.

        """
        if "name" not in setup_dict:
            raise Exception("Every clock entry should have a name.")
        self.name = setup_dict["name"]

        if "instance_hostnames" not in setup_dict:
            raise Exception(f"The clock entry {self.name} must have instance_hostnames defined.")
        self.instance_hostnames = setup_dict["instance_hostnames"]

        if "instance_parameters" not in setup_dict:
            raise Exception(f"The clock entry {self.name} must have instance_parameters defined.")
        self.instance_parameters = setup_dict["instance_parameters"]

        if "ptp_interface_names" not in setup_dict:
            raise Exception(f"The clock entry {self.name} must have ptp_interface_names defined.")

        ptp_interfaces = []
        for ptp_interface_name in setup_dict["ptp_interface_names"]:
            if ptp_interface_name not in ptp_host_ifs_dict:
                raise Exception(f"The ptp_host_if entry {ptp_interface_name} must be defined.")
            ptp_interfaces.append(ptp_host_ifs_dict[ptp_interface_name])
        self.ptp_interfaces = ptp_interfaces

    def __str__(self):
        """
        String representation of this object.

        Returns:
            str: String representation of this object.

        """
        return self.get_name()

    def get_name(self) -> str:
        """
        Gets the name of this clock setup.

        Returns:
            str: The name of this clock setup.
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

    def get_ptp_interface(self, ptp_host_if_name: str) -> PTPHostInterfaceSetup:
        """
        Gets the PTP interface associated with the name ptp_host_if_name.

        Args:
            ptp_host_if_name (str): Name of the ptp_host_if associated with this clock setup with the provided name.

        Returns:
            PTPHostInterfaceSetup: PTPHostInterfaceSetup with the name passed in.
        """
        for ptp_interface in self.ptp_interfaces:
            if ptp_interface.get_name() == ptp_host_if_name:
                return ptp_interface
        raise Exception(f"There is no ptp host interface with the name {ptp_host_if_name} associated with the clock setup {self.get_name()}")
