from keywords.ptp.pmc.objects.pmc_get_parent_data_set_object import PMCGetParentDataSetObject
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser


class PMCGetParentDataSetOutput:
    """
    This class parses the output of commands such as 'pmc GET_PARENT_DATASET'

    Example:
        sending: GET PARENT_DATA_SET
    507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT PARENT_DATA_SET
        parentPortIdentity                    507c6f.fffe.0b5a4d-0
        parentStats                           0
        observedParentOffsetScaledLogVariance 0xffff
        observedParentClockPhaseChangeRate    0x7fffffff
        grandmasterPriority1                  128
        gm.ClockClass                         248
        gm.ClockAccuracy                      0xfe
        gm.OffsetScaledLogVariance            0xffff
        grandmasterPriority2                  128
        grandmasterIdentity                   507c6f.fffe.0b5a4d
    """

    def __init__(self, pmc_output):
        """
        Constructor.
            Create an internal PMCGetDefaultDataSet from the passed parameter.
        Args:
            pmc_output (list[str]): a list of strings representing the output of the pmc command

        """
        pmc_table_parser = PMCTableParser(pmc_output)
        output_values = pmc_table_parser.get_output_values_dict()
        self.pmc_get_parent_data_set_object = PMCGetParentDataSetObject()

        if 'parentPortIdentity' in output_values:
            self.pmc_get_parent_data_set_object.set_parent_port_identity(output_values['parentPortIdentity'])

        if 'parentStats' in output_values:
            self.pmc_get_parent_data_set_object.set_parent_stats(output_values['parentStats'])

        if 'observedParentOffsetScaledLogVariance' in output_values:
            self.pmc_get_parent_data_set_object.set_observed_parent_offset_scaled_log_variance(output_values['observedParentOffsetScaledLogVariance'])

        if 'observedParentClockPhaseChangeRate' in output_values:
            self.pmc_get_parent_data_set_object.set_observed_parent_clock_phase_change_rate(output_values['observedParentClockPhaseChangeRate'])

        if 'grandmasterPriority1' in output_values:
            self.pmc_get_parent_data_set_object.set_grandmaster_priority1(int(output_values['grandmasterPriority1']))

        if 'gm.ClockClass' in output_values:
            self.pmc_get_parent_data_set_object.set_gm_clock_class(int(output_values['gm.ClockClass']))

        if 'gm.ClockAccuracy' in output_values:
            self.pmc_get_parent_data_set_object.set_gm_clock_accuracy(output_values['gm.ClockAccuracy'])

        if 'gm.OffsetScaledLogVariance' in output_values:
            self.pmc_get_parent_data_set_object.set_gm_offset_scaled_log_variance(output_values['gm.OffsetScaledLogVariance'])

        if 'grandmasterPriority2' in output_values:
            self.pmc_get_parent_data_set_object.set_grandmaster_priority2(int(output_values['grandmasterPriority2']))

        if 'grandmasterIdentity' in output_values:
            self.pmc_get_parent_data_set_object.set_grandmaster_identity(output_values['grandmasterIdentity'])

    def get_pmc_get_parent_data_set_object(self) -> PMCGetParentDataSetObject:
        """
        Getter for pmc_get_parent_data_set_object object.

        Returns:
            A PMCGetParentDataSetObject

        """
        return self.pmc_get_parent_data_set_object
