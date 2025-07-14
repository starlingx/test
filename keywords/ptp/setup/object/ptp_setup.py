from typing import Dict, List

from keywords.ptp.setup.object.clock_setup import ClockSetup
from keywords.ptp.setup.object.phc2sys_setup import PHC2SysSetup
from keywords.ptp.setup.object.ptp4l_expected_dict import PTP4LExpectedDict
from keywords.ptp.setup.object.ptp4l_setup import PTP4LSetup
from keywords.ptp.setup.object.ptp_host_interface_setup import PTPHostInterfaceSetup
from keywords.ptp.setup.object.ts2phc_setup import TS2PHCSetup


class PTPSetup:
    """
    This class represents a PTP Setup.
    """

    def __init__(self, setup_dict: Dict[str, Dict]):
        """
        Constructor.

        Args:
            setup_dict (Dict[str, Dict]): The dictionary read from the JSON config file associated with this ptp_setup.

        """
        self.ptp4l_setup_list: List[PTP4LSetup] = []
        self.phc2sys_setup_list: List[PHC2SysSetup] = []
        self.ts2phc_setup_list: List[TS2PHCSetup] = []
        self.clock_setup_list: List[ClockSetup] = []
        self.host_ptp_if_dict: Dict[str, PTPHostInterfaceSetup] = {}  # Name -> PTPHostInterfaceSetup
        self.ptp4l_expected_list: List[PTP4LExpectedDict] = []

        if "ptp_instances" not in setup_dict:
            raise Exception("You must define a ptp_instances section in your ptp setup_dict")

        if "ptp_host_ifs" not in setup_dict:
            raise Exception("You must define a ptp_host_ifs section in your ptp setup_dict")

        ptp_host_ifs = setup_dict["ptp_host_ifs"]
        for ptp_host_if in ptp_host_ifs:
            ptp_host_if_object = PTPHostInterfaceSetup(ptp_host_if)
            ptp_host_if_name = ptp_host_if_object.get_name()
            self.host_ptp_if_dict[ptp_host_if_name] = ptp_host_if_object

        ptp_instances_dict = setup_dict["ptp_instances"]
        if "ptp4l" in ptp_instances_dict:
            ptp4l_list = ptp_instances_dict["ptp4l"]
            for ptp4l_entry_dict in ptp4l_list:
                ptp4l_setup = PTP4LSetup(ptp4l_entry_dict, self.host_ptp_if_dict)
                self.ptp4l_setup_list.append(ptp4l_setup)

        if "phc2sys" in ptp_instances_dict:
            phc2sys_list = ptp_instances_dict["phc2sys"]
            for phc2sys_entry_dict in phc2sys_list:
                phc2sys_setup = PHC2SysSetup(phc2sys_entry_dict, self.host_ptp_if_dict)
                self.phc2sys_setup_list.append(phc2sys_setup)

        if "ts2phc" in ptp_instances_dict:
            ts2phc_list = ptp_instances_dict["ts2phc"]
            for ts2phc_entry_dict in ts2phc_list:
                ts2phc_setup = TS2PHCSetup(ts2phc_entry_dict, self.host_ptp_if_dict)
                self.ts2phc_setup_list.append(ts2phc_setup)

        if "clock" in ptp_instances_dict:
            clock_list = ptp_instances_dict["clock"]
            for clock_entry_dict in clock_list:
                clock_setup = ClockSetup(clock_entry_dict, self.host_ptp_if_dict)
                self.clock_setup_list.append(clock_setup)

        expected_dict = setup_dict.get("expected_dict", {})
        self.ptp4l_expected_list.extend(PTP4LExpectedDict(item) for item in expected_dict.get("ptp4l", []))

    def __str__(self) -> str:
        """
        String representation of this object.

        Returns:
            str: String representation of this object.

        """
        return "PTPSetup"

    def get_ptp4l_setup_list(self) -> List[PTP4LSetup]:
        """
        Getter for the list of ptp4l setups.

        Returns:
            List[PTP4LSetup]: list of ptp4l setups
        """
        return self.ptp4l_setup_list

    def get_ptp4l_setup(self, setup_name: str) -> PTP4LSetup:
        """
        Getter for the PTP4LSetup with the specified name.

        Args:
            setup_name (str): Name of the specified setup.

        Returns:
            PTP4LSetup: The setup matching that name.
        """
        for setup in self.ptp4l_setup_list:
            if setup.get_name() == setup_name:
                return setup
        raise Exception(f"There is no ptp4l setup named {setup_name}")

    def get_phc2sys_setup_list(self) -> List[PHC2SysSetup]:
        """
        Getter for the list of phc2sys setups.

        Returns:
            List[PHC2SysSetup]: list of phc2sys setups
        """
        return self.phc2sys_setup_list

    def get_phc2sys_setup(self, setup_name: str) -> PHC2SysSetup:
        """
        Getter for the PHC2SysSetup with the specified name.

        Args:
            setup_name (str): Name of the specified setup.

        Returns:
            PHC2SysSetup: The setup matching that name.
        """
        for setup in self.phc2sys_setup_list:
            if setup.get_name() == setup_name:
                return setup
        raise Exception(f"There is no phc2sys setup named {setup_name}")

    def get_ts2phc_setup_list(self) -> List[TS2PHCSetup]:
        """
        Getter for the list of ts2phc setups.

        Returns:
            List[TS2PHCSetup]: list of ts2phc setups
        """
        return self.ts2phc_setup_list

    def get_ts2phc_setup(self, setup_name: str) -> TS2PHCSetup:
        """
        Getter for the TS2PHCSetup with the specified name.

        Args:
            setup_name (str): Name of the specified setup.

        Returns:
            TS2PHCSetup: The setup matching that name.
        """
        for setup in self.ts2phc_setup_list:
            if setup.get_name() == setup_name:
                return setup
        raise Exception(f"There is no ts2phc setup named {setup_name}")

    def get_clock_setup_list(self) -> List[ClockSetup]:
        """
        Getter for the list of clock setups.

        Returns:
            List[ClockSetup]: list of clock setups
        """
        return self.clock_setup_list

    def get_clock_setup(self, setup_name: str) -> ClockSetup:
        """
        Getter for the ClockSetup with the specified name.

        Args:
            setup_name (str): Name of the specified setup.

        Returns:
            ClockSetup: The setup matching that name.
        """
        for setup in self.clock_setup_list:
            if setup.get_name() == setup_name:
                return setup
        raise Exception(f"There is no clock setup named {setup_name}")

    def get_expected_ptp4l_list(self) -> List[PTP4LExpectedDict]:
        """
        Getter for the list of expected ptp4l list.

        Returns:
            List[PTP4LExpectedDict]: list of ptp4l expected dict
        """
        return self.ptp4l_expected_list

    def get_ptp4l_expected_by_name(self, name: str) -> PTP4LExpectedDict:
        """
        Getter for ptp4l expected by name.

        Args:
            name (str): The name of the instance.

        Returns:
            PTP4LExpectedDict: ptp4l expected by name
        """
        ptp4l_expected_obj = next((obj for obj in self.ptp4l_expected_list if obj.get_name() == name), None)
        if not ptp4l_expected_obj:
            raise ValueError(f"No expected PTP4L object found for name: {name}")
        return ptp4l_expected_obj
