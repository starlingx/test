from framework.exceptions.keyword_exception import KeywordException
from keywords.ptp.pmc.objects.pmc_get_grandmaster_settings_np_object import PMCGetGrandmasterSettingsNpObject
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser


class PMCGetGrandmasterSettingsNpOutput:
    """
    This class parses the output of commands such as 'pmc GRANDMASTER_SETTINGS_NP'

    Example:
        sending: GET GRANDMASTER_SETTINGS_NP
                507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT GRANDMASTER_SETTINGS_NP
                        clockClass              6
                        clockAccuracy           0x20
                        offsetScaledLogVariance 0x4e5d
                        currentUtcOffset        37
                        leap61                  0
                        leap59                  0
                        currentUtcOffsetValid   0
                        ptpTimescale            1
                        timeTraceable           1
                        frequencyTraceable      1
                        timeSource              0x20
    """

    def __init__(self, pmc_output: list[str]):
        """
        Constructor.

            Create an internal GRANDMASTER_SETTINGS_NP from the passed parameter.

        Args:
            pmc_output (list[str]): a list of strings representing the output of the pmc command

        """
        pmc_table_parser = PMCTableParser(pmc_output)

        output_values_list = pmc_table_parser.get_output_values_dict()

        if len(output_values_list) > 1:
            raise KeywordException("More then one grandmaster settings was found")

        output_values = output_values_list[0]

        self.pmc_get_grandmaster_settings_np_object = PMCGetGrandmasterSettingsNpObject()

        if "clockClass" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_clock_class(int(output_values["clockClass"]))

        if "clockAccuracy" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_clock_accuracy(output_values["clockAccuracy"])

        if "offsetScaledLogVariance" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_offset_scaled_log_variance(output_values["offsetScaledLogVariance"])

        if "currentUtcOffset" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_current_utc_offset(int(output_values["currentUtcOffset"]))

        if "leap61" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_leap61(int(output_values["leap61"]))

        if "leap59" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_leap59(int(output_values["leap59"]))

        if "currentUtcOffsetValid" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_current_utc_off_set_valid(int(output_values["currentUtcOffsetValid"]))

        if "ptpTimescale" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_ptp_time_scale(int(output_values["ptpTimescale"]))

        if "timeTraceable" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_time_traceable(int(output_values["timeTraceable"]))

        if "frequencyTraceable" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_frequency_traceable(int(output_values["frequencyTraceable"]))

        if "timeSource" in output_values:
            self.pmc_get_grandmaster_settings_np_object.set_time_source(output_values["timeSource"])

    def get_pmc_get_grandmaster_settings_np_object(self) -> PMCGetGrandmasterSettingsNpObject:
        """
        Getter for pmc_get_grandmaster_settings_np_object object.

        Returns:
            PMCGetGrandmasterSettingsNpObject: A PMCGetGrandmasterSettingsNpObject

        """
        return self.pmc_get_grandmaster_settings_np_object
