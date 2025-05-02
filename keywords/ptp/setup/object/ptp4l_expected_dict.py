from typing import Any, Dict, List

from starlingx.keywords.ptp.setup.object.port_data_set import PortDataSet


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

    def get_controller_0_port_data_set(self) -> List[PortDataSet]:
        """
        Gets the list of controller-0 port data set.

        Returns:
            List[PortDataSet]: The list of controller-0 port data set.
        """
        port_data_set_list = []
        for port_data_set in self.controller_0_port_data_set:
            port_data_set_object = PortDataSet(port_data_set)
            port_data_set_list.append(port_data_set_object)
        return port_data_set_list

    def get_controller_1_port_data_set(self) -> List[PortDataSet]:
        """
        Gets the list of controller-1 port data set.

        Returns:
            List[PortDataSet]: The list of controller-1 port data set.
        """
        port_data_set_list = []
        for port_data_set in self.controller_1_port_data_set:
            port_data_set_object = PortDataSet(port_data_set)
            port_data_set_list.append(port_data_set_object)
        return port_data_set_list

    def get_compute_0_port_data_set(self) -> List[PortDataSet]:
        """
        Gets the list of compute-0 port data set.

        Returns:
            List[PortDataSet]: The list of compute-0 port data set.
        """
        port_data_set_list = []
        for port_data_set in self.compute_0_port_data_set:
            port_data_set_object = PortDataSet(port_data_set)
            port_data_set_list.append(port_data_set_object)
        return port_data_set_list
