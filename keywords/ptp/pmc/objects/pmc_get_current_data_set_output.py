from framework.exceptions.keyword_exception import KeywordException
from keywords.ptp.pmc.objects.pmc_get_current_data_set_object import PMCGetCurrentDataSetObject
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser


class PMCGetCurrentDataSetOutput:
    """
    This class parses the output of commands such as 'pmc CURRENT_DATA_SET'

    Example:
        sending: GET CURRENT_DATA_SET
                507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT CURRENT_DATA_SET
                        stepsRemoved     0
                        offsetFromMaster 0.0
                        meanPathDelay    0.0
    """

    def __init__(self, pmc_output: list[str]):
        """
        Constructor.

            Create an internal PMCGetCurrentDataSet from the passed parameter.

        Args:
            pmc_output (list[str]): a list of strings representing the output of the pmc command

        """
        pmc_table_parser = PMCTableParser(pmc_output)
        output_values_list = pmc_table_parser.get_output_values_dict()

        if len(output_values_list) > 1:
            raise KeywordException("More then one current data set was found")

        output_values = output_values_list[0]

        self.pmc_get_current_data_set_object = PMCGetCurrentDataSetObject()

        if "stepsRemoved" in output_values:
            self.pmc_get_current_data_set_object.set_steps_removed(int(output_values["stepsRemoved"]))

        if "offsetFromMaster" in output_values:
            self.pmc_get_current_data_set_object.set_offset_from_master(float(output_values["offsetFromMaster"]))

        if "meanPathDelay" in output_values:
            self.pmc_get_current_data_set_object.set_mean_path_delay(float(output_values["meanPathDelay"]))

    def get_pmc_get_current_data_set_object(self) -> PMCGetCurrentDataSetObject:
        """
        Getter for pmc_get_current_data_set_object object.

        Returns:
            PMCGetCurrentDataSetObject: A PMCGetCurrentDataSetObject

        """
        return self.pmc_get_current_data_set_object
