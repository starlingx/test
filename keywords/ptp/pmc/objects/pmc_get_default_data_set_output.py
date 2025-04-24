from framework.exceptions.keyword_exception import KeywordException
from keywords.ptp.pmc.objects.pmc_get_default_data_set_object import PMCGetDefaultDataSetObject
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser


class PMCGetDefaultDataSetOutput:
    """
    This class parses the output of commands such as 'pmc GET_DEFAULT_DATASET'

    Example:
        sending: GET DEFAULT_DATA_SET
    507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT DEFAULT_DATA_SET
        twoStepFlag            1
        slaveOnly              0
        numberPorts            1
        priority1              128
        clockClass             248
        clockAccuracy          0xfe
        offsetScaledLogVariance 0xffff
        priority2              128
        clockIdentity          507c6f.fffe.0b5a4d
        domainNumber           0.

    """

    def __init__(self, pmc_output: list[str]):
        """
        Constructor.

            Create an internal PMCGetDefaultDataSet from the passed parameter.

        Args:
            pmc_output (list[str]): a list of strings representing the output of the pmc command

        """
        pmc_table_parser = PMCTableParser(pmc_output)
        output_values_list = pmc_table_parser.get_output_values_dict()

        if len(output_values_list) > 1:
            raise KeywordException("More then one default data set was found")
        output_values = output_values_list[0]

        self.pmc_get_default_data_set_object = PMCGetDefaultDataSetObject()

        if "twoStepFlag" in output_values:
            self.pmc_get_default_data_set_object.set_two_step_flag(int(output_values["twoStepFlag"]))

        if "slaveOnly" in output_values:
            self.pmc_get_default_data_set_object.set_slave_only(int(output_values["slaveOnly"]))

        if "socket_priority" in output_values:
            self.pmc_get_default_data_set_object.set_socket_priority(int(output_values["socket_priority"]))

        if "numberPorts" in output_values:
            self.pmc_get_default_data_set_object.set_number_ports(int(output_values["numberPorts"]))

        if "priority1" in output_values:
            self.pmc_get_default_data_set_object.set_priority1(int(output_values["priority1"]))

        if "clockClass" in output_values:
            self.pmc_get_default_data_set_object.set_clock_class(int(output_values["clockClass"]))

        if "clockAccuracy" in output_values:
            self.pmc_get_default_data_set_object.set_clock_accuracy(output_values["clockAccuracy"])

        if "offsetScaledLogVariance" in output_values:
            self.pmc_get_default_data_set_object.set_offset_scaled_log_variance(output_values["offsetScaledLogVariance"])

        if "priority2" in output_values:
            self.pmc_get_default_data_set_object.set_priority2(int(output_values["priority2"]))

        if "clockIdentity" in output_values:
            self.pmc_get_default_data_set_object.set_clock_identity(output_values["clockIdentity"])

        if "domainNumber" in output_values:
            self.pmc_get_default_data_set_object.set_domain_number(output_values["domainNumber"])

        if "free_running" in output_values:
            self.pmc_get_default_data_set_object.set_free_running(int(output_values["free_running"]))

        if "freq_est_interval" in output_values:
            self.pmc_get_default_data_set_object.set_freq_est_interval(int(output_values["freq_est_interval"]))

        if "dscp_event" in output_values:
            self.pmc_get_default_data_set_object.set_dscp_event(int(output_values["dscp_event"]))

        if "dscp_general" in output_values:
            self.pmc_get_default_data_set_object.set_dscp_general(int(output_values["dscp_general"]))

        if "dataset_comparison" in output_values:
            self.pmc_get_default_data_set_object.set_dataset_comparison(output_values["dataset_comparison"])

        if "maxStepsRemoved" in output_values:
            self.pmc_get_default_data_set_object.set_max_steps_removed(int(output_values["maxStepsRemoved"]))

        if "#utc_offset" in output_values:
            self.pmc_get_default_data_set_object.set_utc_offset(int(output_values["#utc_offset"]))

    def get_pmc_get_default_data_set_object(self) -> PMCGetDefaultDataSetObject:
        """
        Getter for pmc_get_default_data_set_object object.

        Returns:
            PMCGetDefaultDataSetObject: A PMCGetDefaultDataSetObject

        """
        return self.pmc_get_default_data_set_object
