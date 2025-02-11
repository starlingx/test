from keywords.ptp.cat.cat_ptp_table_parser import CatPtpTableParser
from keywords.ptp.cat.objects.port_data_set_object import PortDataSetObject


class PortDataSetOutput:
    """
    This class parses the output of Port Data Set

    Example:
        logAnnounceInterval     1
        logSyncInterval         0
        operLogSyncInterval     0
        logMinDelayReqInterval  0
        logMinPdelayReqInterval 0
        operLogPdelayReqInterval 0
        announceReceiptTimeout  3
        syncReceiptTimeout      0
        delayAsymmetry          0
        fault_reset_interval    4
        neighborPropDelayThresh 20000000
        masterOnly              0
        G.8275.portDS.localPriority     128
        asCapable               auto
        BMCA                    ptp
        inhibit_announce        0
        inhibit_delay_req       0
        ignore_source_id        0

    """

    def __init__(self, port_data_set_output: [str]):
        """
        Constructor.
            Create an internal PortDataSetObject from the passed parameter.
        Args:
            port_data_set_output (list[str]): a list of strings representing the port data set output

        """
        cat_ptp_table_parser = CatPtpTableParser(port_data_set_output)
        output_values = cat_ptp_table_parser.get_output_values_dict()
        self.port_data_set_object = PortDataSetObject()

        if 'logAnnounceInterval' in output_values:
            self.port_data_set_object.set_log_announce_interval(int(output_values['logAnnounceInterval']))

        if 'logSyncInterval' in output_values:
            self.port_data_set_object.set_log_sync_interval(int(output_values['logSyncInterval']))

        if 'operLogSyncInterval' in output_values:
            self.port_data_set_object.set_oper_log_sync_interval(int(output_values['operLogSyncInterval']))

        if 'logMinDelayReqInterval' in output_values:
            self.port_data_set_object.set_log_min_delay_req_interval(int(output_values['logMinDelayReqInterval']))

        if 'logMinPdelayReqInterval' in output_values:
            self.port_data_set_object.set_log_min_p_delay_req_interval(int(output_values['logMinPdelayReqInterval']))

        if 'operLogPdelayReqInterval' in output_values:
            self.port_data_set_object.set_oper_log_p_delay_req_interval(int(output_values['operLogPdelayReqInterval']))

        if 'announceReceiptTimeout' in output_values:
            self.port_data_set_object.set_announce_receipt_timeout(int(output_values['announceReceiptTimeout']))

        if 'syncReceiptTimeout' in output_values:
            self.port_data_set_object.set_sync_receipt_timeout(int(output_values['syncReceiptTimeout']))

        if 'delayAsymmetry' in output_values:
            self.port_data_set_object.set_delay_asymmetry(int(output_values['delayAsymmetry']))

        if 'fault_reset_interval' in output_values:
            self.port_data_set_object.set_fault_reset_interval(int(output_values['fault_reset_interval']))

        if 'neighborPropDelayThresh' in output_values:
            self.port_data_set_object.set_neighbor_prop_delay_thresh(int(output_values['neighborPropDelayThresh']))

        if 'masterOnly' in output_values:
            self.port_data_set_object.set_master_only(int(output_values['masterOnly']))

        if 'asCapable' in output_values:
            self.port_data_set_object.set_as_capable(output_values['asCapable'])

        if 'BMCA' in output_values:
            self.port_data_set_object.set_bmca(output_values['BMCA'])

        if 'inhibit_announce' in output_values:
            self.port_data_set_object.set_inhibit_announce(int(output_values['inhibit_announce']))

        if 'inhibit_delay_req' in output_values:
            self.port_data_set_object.set_inhibit_delay_req(int(output_values['inhibit_delay_req']))

        if 'ignore_source_id' in output_values:
            self.port_data_set_object.set_ignore_source_id(int(output_values['ignore_source_id']))

    def get_port_data_set_object(self) -> PortDataSetObject:
        """
        Getter for port_data_set_object object.

        Returns:
            A PortDataSetObject

        """
        return self.port_data_set_object
