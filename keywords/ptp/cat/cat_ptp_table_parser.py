from framework.exceptions.keyword_exception import KeywordException


class CatPtpTableParser:
    """
    Class for cat PTP table parsing
    Example:
        twoStepFlag             1
        slaveOnly               0
        socket_priority         0
        priority1               128
        priority2               128
        domainNumber            0
        #utc_offset             37
        clockClass              248
        clockAccuracy           0xFE
        offsetScaledLogVariance 0xFFFF
        free_running            0
        freq_est_interval       1
        dscp_event              0
        dscp_general            0
        dataset_comparison      ieee1588
        G.8275.defaultDS.localPriority  128
        maxStepsRemoved         255
    """

    def __init__(self, cat_ptp_output):
        """
        Constructor
        Args:
            cat_ptp_output (list[str]): a list of strings representing the output of a 'cat ptp' command.
        """
        self.cat_ptp_output = cat_ptp_output

    def get_output_values_dict(
            self,
    ):
        """
        Getter for output values dict
        Returns: the output values dict

        """

        output_values_dict = {}

        for row in self.cat_ptp_output:
            values = row.split(None, 1)  # split once
            if len(values) == 2:
                key, value = values
                output_values_dict[key.strip()] = value.strip()
            else:
                raise KeywordException(f"Line with values: {row} was not in the expected format")
        return output_values_dict
