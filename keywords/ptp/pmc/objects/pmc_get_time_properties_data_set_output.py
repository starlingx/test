from keywords.ptp.pmc.objects.pmc_get_time_properties_data_set_object import PMCGetTimePropertiesDataSetObject
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser


class PMCGetTimePropertiesDataSetOutput:
    """
    This class parses the output of commands such as 'pmc TIME_PROPERTIES_DATA_SET'

    Example:
        sending: GET TIME_PROPERTIES_DATA_SET
                507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT TIME_PROPERTIES_DATA_SET
                        currentUtcOffset      37
                        leap61                0
                        leap59                0
                        currentUtcOffsetValid 0
                        ptpTimescale          1
                        timeTraceable         1
                        frequencyTraceable    0
                        timeSource            0x20
    """

    def __init__(self, pmc_output: [str]):
        """
        Constructor.
            Create an internal TIME_PROPERTIES_DATA_SET from the passed parameter.
        Args:
            pmc_output (list[str]): a list of strings representing the output of the pmc command

        """
        pmc_table_parser = PMCTableParser(pmc_output)
        output_values = pmc_table_parser.get_output_values_dict()
        self.pmc_get_time_properties_data_set_object = PMCGetTimePropertiesDataSetObject()

        if 'currentUtcOffset' in output_values:
            self.pmc_get_time_properties_data_set_object.set_current_utc_offset(int(output_values['currentUtcOffset']))

        if 'leap61' in output_values:
            self.pmc_get_time_properties_data_set_object.set_leap61(int(output_values['leap61']))

        if 'leap59' in output_values:
            self.pmc_get_time_properties_data_set_object.set_leap59(int(output_values['leap59']))

        if 'currentUtcOffsetValid' in output_values:
            self.pmc_get_time_properties_data_set_object.set_current_utc_off_set_valid(int(output_values['currentUtcOffsetValid']))

        if 'ptpTimescale' in output_values:
            self.pmc_get_time_properties_data_set_object.set_ptp_time_scale(int(output_values['ptpTimescale']))

        if 'timeTraceable' in output_values:
            self.pmc_get_time_properties_data_set_object.set_time_traceable(int(output_values['timeTraceable']))

        if 'frequencyTraceable' in output_values:
            self.pmc_get_time_properties_data_set_object.set_frequency_traceable(int(output_values['frequencyTraceable']))

        if 'timeSource' in output_values:
            self.pmc_get_time_properties_data_set_object.set_time_source(output_values['timeSource'])


    def get_pmc_get_time_properties_data_set_object(self) -> PMCGetTimePropertiesDataSetObject:
        """
        Getter for pmc_get_time_properties_data_set_object object.

        Returns:
            A PMCGetTimePropertiesDataSetObject

        """
        return self.pmc_get_time_properties_data_set_object
