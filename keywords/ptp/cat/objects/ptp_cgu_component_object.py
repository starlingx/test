from keywords.ptp.cat.objects.ptp_cgu_eec_dpll_object import PtpCguEecDpllObject
from keywords.ptp.cat.objects.ptp_cgu_input_object import PtpCguInputObject
from keywords.ptp.cat.objects.ptp_cgu_pps_dpll_object import PtpCguPpsDpllObject


class PtpCguComponentObject:
    """
    Class for PTP CGU Component Object.
    """

    def __init__(self, config_version: str, fw_version: str, chip_model: str):

        self.config_version = config_version
        self.fw_version = fw_version
        self.chip_model = chip_model
        self.cgu_inputs: list[PtpCguInputObject] = []
        self.eec_dpll: PtpCguEecDpllObject = None
        self.pps_dpll: PtpCguPpsDpllObject = None

    def get_config_version(self) -> str:
        """
        Gets the configuration version.

        Returns:
            str: the configuration version
        """
        return self.config_version

    def set_config_version(self, config_version: str):
        """
        Setter for config version.

        Args:
            config_version (str): the config version.

        """
        self.config_version = config_version

    def get_fw_version(self) -> str:
        """
        Gets the firmware version.

        Returns:
            str: the firmware version
        """
        return self.fw_version

    def set_fw_version(self, fw_version: str):
        """
        Setter for firmware version.

        Args:
            fw_version (str): the firmware version.

        """
        self.fw_version = fw_version

    def get_chip_model(self) -> str:
        """
        Gets the chip model.

        Returns:
            str: the chip model
        """
        return self.chip_model

    def set_chip_model(self, chip_model: str):
        """
        Setter for chip model.

        Args:
            chip_model (str): the chip model.

        """
        self.chip_model = chip_model

    def get_cgu_inputs(self) -> list[PtpCguInputObject]:
        """
        Gets the list of CGU input configurations.

        Returns:
            list[PtpCguInputObject]: a list of PtpCguInputObjects.
        """
        return self.cgu_inputs

    def get_cgu_input(self, input_name: str) -> PtpCguInputObject:
        """
        Gets the cgu input with the given input_name.

        Args:
            input_name (str): the input name.

        Returns:
            PtpCguInputObject: the PtpCguInputObject.

        """
        input_objects = list(
            filter(
                lambda input_object: input_object.get_name() == input_name,
                self.cgu_inputs,
            )
        )
        if len(input_objects) == 1:
            return input_objects[0]
        return None

    def set_cgu_inputs(self, cgu_inputs: list[PtpCguInputObject]):
        """
        Setter for cgu inputs.

        Args:
            cgu_inputs (list[PtpCguInputObject]): the cgu inputs.

        """
        self.cgu_inputs = cgu_inputs

    def append_cgu_input(self, cgu_input: PtpCguInputObject):
        """
        Appends to the current list.

        Args:
            cgu_input (PtpCguInputObject): the cgu input.

        """
        self.cgu_inputs.append(cgu_input)

    def get_eec_dpll(self) -> PtpCguEecDpllObject:
        """
        Gets the EEC DPLL configuration.

        Returns:
            PtpCguEecDpllObject: the PtpCguEecDpllObject object
        """
        return self.eec_dpll

    def set_eec_dpll(self, eec_dpll: PtpCguEecDpllObject):
        """
        Setter for eec_dpll.

        Args:
            eec_dpll (PtpCguEecDpllObject): the eec_dpll object.

        """
        self.eec_dpll = eec_dpll

    def get_pps_dpll(self) -> PtpCguPpsDpllObject:
        """
        Gets the PPD DPLL configuration.

        Returns:
            PtpCguPpsDpllObject: a PtpCguPpsDpllObject.
        """
        return self.pps_dpll

    def set_pps_dpll(self, pps_dpll: PtpCguPpsDpllObject) -> None:
        """
        Setter for pps_dpll.

        Args:
            pps_dpll (PtpCguPpsDpllObject): a PtpCguPpsDpllObject.

        """
        self.pps_dpll = pps_dpll
