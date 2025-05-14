from typing import Any, Dict, List

from keywords.ptp.setup.object.grandmaster_settings import GrandmasterSettings
from keywords.ptp.setup.object.parent_data_set import ParentDataSet
from keywords.ptp.setup.object.port_data_set import PortDataSet
from keywords.ptp.setup.time_properties_data_set import TimePropertiesDataSet


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
        self.expected_dict = expected_dict

        if "name" not in expected_dict:
            raise Exception("Every PTP4L expected dict should have a name.")
        self.name = expected_dict["name"]

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

    def get_parent_data_set_for_hostname(self, hostname: str) -> ParentDataSet:
        """
        Gets the of parent data set for hostname.

        Args:
            hostname (str): The name of the host.

        Returns:
            ParentDataSet: The of parent data set for hostname.
        """
        host_specific_data = self.expected_dict.get(hostname)

        if not host_specific_data:
            raise Exception(f"Expected host specific data : {hostname} is not found for instance: {self.name}")

        parent_data_set_raw = host_specific_data.get("parent_data_set")
        if not parent_data_set_raw:
            raise Exception(f"Expected parent data set not found for hostname: {hostname}")

        return ParentDataSet(parent_data_set_raw)

    def get_time_properties_data_set_for_hostname(self, hostname: str) -> TimePropertiesDataSet:
        """
        Gets the of time properties data set for hostname.

        Args:
            hostname (str): The name of the host.

        Returns:
            TimePropertiesDataSet: The of time properties data set for hostname.
        """
        host_specific_data = self.expected_dict.get(hostname)

        if not host_specific_data:
            raise Exception(f"Expected host specific data : {hostname} is not found for instance: {self.name}")

        time_properties_data_set_raw = host_specific_data.get("time_properties_data_set")
        if not time_properties_data_set_raw:
            raise Exception(f"Expected time properties data set not found for hostname: {hostname}")

        return TimePropertiesDataSet(time_properties_data_set_raw)

    def get_grandmaster_settings_for_hostname(self, hostname: str) -> GrandmasterSettings:
        """
        Gets the of grandmaster settings for hostname.

        Args:
            hostname (str): The name of the host.

        Returns:
            GrandmasterSettings: The of grandmaster settings for hostname.
        """
        host_specific_data = self.expected_dict.get(hostname)

        if not host_specific_data:
            raise Exception(f"Expected host specific data : {hostname} is not found for instance: {self.name}")

        grandmaster_settings_raw = host_specific_data.get("grandmaster_settings")
        if not grandmaster_settings_raw:
            raise Exception(f"Expected grandmaster settings not found for hostname: {hostname}")

        return GrandmasterSettings(grandmaster_settings_raw)

    def get_port_data_set_for_hostname(self, hostname: str) -> List[PortDataSet]:
        """
        Gets the list of port data set for hostname.

        Args:
            hostname (str): The name of the host.

        Returns:
            List[PortDataSet]: The list of port data set for hostname.
        """
        host_specific_data = self.expected_dict.get(hostname)

        if not host_specific_data:
            raise Exception(f"Expected host specific data : {hostname} is not found for instance: {self.name}")

        port_data_set_list_raw = host_specific_data.get("port_data_set")
        if not port_data_set_list_raw:
            raise Exception(f"Expected port data set not found for hostname: {hostname}")

        return [PortDataSet(port_data_set) for port_data_set in port_data_set_list_raw]
