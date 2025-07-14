from framework.exceptions.keyword_exception import KeywordException
from keywords.ptp.pmc.objects.pmc_get_time_status_np_object import PMCGetTimeStatusNpObject
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser


class PMCGetTimeStatusNpOutput:
    """
    This class parses the output of commands such as 'pmc TIME_STATUS_NP'

    Example:
        sending: GET TIME_STATUS_NP
                507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT TIME_STATUS_NP
                        master_offset              -62
                        ingress_time               0
                        cumulativeScaledRateOffset +0.000000000
                        scaledLastGmPhaseChange    0
                        gmTimeBaseIndicator        0
                        lastGmPhaseChange          0x0000'0000000000000000.0000
                        gmPresent                  false
                        gmIdentity                 507c6f.fffe.0b5a4d
    """

    def __init__(self, pmc_output: list[str]):
        """
        Constructor.

            Create an internal TIME_STATUS_NP from the passed parameter.

        Args:
            pmc_output (list[str]): a list of strings representing the output of the pmc command

        """
        pmc_table_parser = PMCTableParser(pmc_output)
        output_values_list = pmc_table_parser.get_output_values_dict()

        if len(output_values_list) > 1:
            raise KeywordException("More then one time status sets was found")
        output_values = output_values_list[0]

        self.pmc_get_time_status_np_object = PMCGetTimeStatusNpObject()

        if "master_offset" in output_values:
            self.pmc_get_time_status_np_object.set_master_offset(int(output_values["master_offset"]))

        if "ingress_time" in output_values:
            self.pmc_get_time_status_np_object.set_ingress_time(int(output_values["ingress_time"]))

        if "cumulativeScaledRateOffset" in output_values:
            self.pmc_get_time_status_np_object.set_cumulative_scaled_rate_offset(output_values["cumulativeScaledRateOffset"])

        if "scaledLastGmPhaseChange" in output_values:
            self.pmc_get_time_status_np_object.set_scaled_last_gm_phase_change(int(output_values["scaledLastGmPhaseChange"]))

        if "gmTimeBaseIndicator" in output_values:
            self.pmc_get_time_status_np_object.set_gm_time_base_indicator(int(output_values["gmTimeBaseIndicator"]))

        if "lastGmPhaseChange" in output_values:
            self.pmc_get_time_status_np_object.set_last_gm_phase_change(output_values["lastGmPhaseChange"])

        if "gmPresent" in output_values:
            self.pmc_get_time_status_np_object.set_gm_present(output_values["gmPresent"] == "true")

        if "gmIdentity" in output_values:
            self.pmc_get_time_status_np_object.set_gm_identity(output_values["gmIdentity"])

    def get_pmc_get_time_status_np_object(self) -> PMCGetTimeStatusNpObject:
        """
        Getter for pmc_get_time_status_np_object object.

        Returns:
            PMCGetTimeStatusNpObject: A PMCGetTimeStatusNpObject

        """
        return self.pmc_get_time_status_np_object
