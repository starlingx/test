from keywords.ptp.pmc.objects.pmc_get_port_data_set_object import PMCGetPortDataSetObject
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser


class PMCGetPortDataSetOutput:
    """
    This class parses the output of commands such as 'GET PORT_DATA_SET'

    Example:
        sending: GET PORT_DATA_SET
                507c6f.fffe.21b929-1 seq 0 RESPONSE MANAGEMENT PORT_DATA_SET
                        portIdentity            507c6f.fffe.21b929-1
                        portState               MASTER
                        logMinDelayReqInterval  0
                        peerMeanPathDelay       0
                        logAnnounceInterval     1
                        announceReceiptTimeout  3
                        logSyncInterval         0
                        delayMechanism          1
                        logMinPdelayReqInterval 0
                        versionNumber           2
    """

    def __init__(self, pmc_output: list[str]):
        """
        Constructor.

            Create an internal PMCGetPortDataSet from the passed parameter.

        Args:
            pmc_output (list[str]): a list of strings representing the output of the pmc command
        """
        pmc_table_parser = PMCTableParser(pmc_output)
        output_values_list = pmc_table_parser.get_output_values_dict()
        self.pmc_get_port_data_set_object_list = []
        for output_values in output_values_list:
            pmc_get_port_data_set_object = PMCGetPortDataSetObject()
            if "portIdentity" in output_values:
                pmc_get_port_data_set_object.set_port_identity(output_values["portIdentity"])
            if "portState" in output_values:
                pmc_get_port_data_set_object.set_port_state(output_values["portState"])
            if "logMinDelayReqInterval" in output_values:
                pmc_get_port_data_set_object.set_log_min_delay_req_interval(int(output_values["logMinDelayReqInterval"]))
            if "peerMeanPathDelay" in output_values:
                pmc_get_port_data_set_object.set_peer_mean_path_delay(int(output_values["peerMeanPathDelay"]))
            if "logAnnounceInterval" in output_values:
                pmc_get_port_data_set_object.set_log_announce_interval(int(output_values["logAnnounceInterval"]))
            if "announceReceiptTimeout" in output_values:
                pmc_get_port_data_set_object.set_announce_receipt_timeout(int(output_values["announceReceiptTimeout"]))
            if "logSyncInterval" in output_values:
                pmc_get_port_data_set_object.set_log_sync_interval(int(output_values["logSyncInterval"]))
            if "delayMechanism" in output_values:
                pmc_get_port_data_set_object.set_delay_mechanism(int(output_values["delayMechanism"]))
            if "logMinPdelayReqInterval" in output_values:
                pmc_get_port_data_set_object.set_log_min_p_delay_req_interval(int(output_values["logMinPdelayReqInterval"]))
            if "versionNumber" in output_values:
                pmc_get_port_data_set_object.set_version_number(int(output_values["versionNumber"]))
            self.pmc_get_port_data_set_object_list.append(pmc_get_port_data_set_object)

    def get_pmc_get_port_data_set_objects(self) -> list[PMCGetPortDataSetObject]:
        """
        Getter for pmc_get_port_data_set_object object.

        Returns:
            list[PMCGetPortDataSetObject]: A PMCGetPortDataSetObject
        """
        return self.pmc_get_port_data_set_object_list
