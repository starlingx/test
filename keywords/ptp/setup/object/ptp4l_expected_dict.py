from typing import Any, Dict, List

from keywords.ptp.setup.object.port_data_set import PortDataSet


class PTP4LExpectedDict:
    """
    Class models a ptp4l expected dict
    """

    def __init__(self, expected_dict: Dict[str, Any]):
        """
        Constructor.

        Args:
            expected_dict (Dict[str, Any]): The dictionary read from the JSON setup template file associated with this ptp4l expected dict

        """
        if "name" not in expected_dict:
            raise Exception("Every PTP4L expected dict should have a name.")
        self.name = expected_dict["name"]

        if "ptp_role" not in expected_dict:
            raise Exception("Every PTP4L expected dict should have a ptp_role.")
        self.ptp_role = expected_dict["ptp_role"]

        self.controller_0_port_data_set = None
        if "controller_0_port_data_set" in expected_dict:
            self.controller_0_port_data_set = expected_dict["controller_0_port_data_set"]

        self.controller_1_port_data_set = None
        if "controller_1_port_data_set" in expected_dict:
            self.controller_1_port_data_set = expected_dict["controller_1_port_data_set"]

        self.compute_0_port_data_set = None
        if "compute_0_port_data_set" in expected_dict:
            self.compute_0_port_data_set = expected_dict["compute_0_port_data_set"]

    def __str__(self) -> str:
        """
        String representation of this object.

        Returns:
            str: String representation of this object.

        """
        return self.get_name()

    def get_name(self) -> str:
        """
        Gets the name of this ptp4l expected dict.

        Returns:
            str: The name of this ptp4l expected dict.
        """
        return self.name

    def get_ptp_role(self) -> str:
        """
        Gets the ptp role.

        Returns:
            str: The ptp role.
        """
        return self.ptp_role

    def get_port_data_set_for_hostname(self, hostname: str) -> List[PortDataSet]:
        """
        Gets the list of port data set for hostname.

        Args:
            hostname (str): The name of the host.

        Returns:
            List[PortDataSet]: The list of port data set for hostname.
        """
        hostname_to_port_data_set = {
            "controller-0": self.controller_0_port_data_set,
            "controller-1": self.controller_1_port_data_set,
            "compute-0": self.compute_0_port_data_set,
        }.get(hostname)

        if not hostname_to_port_data_set:
            raise Exception(f"Expected port data set not found for hostname: {hostname}")

        return [PortDataSet(port_data_set) for port_data_set in hostname_to_port_data_set]
