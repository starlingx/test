from keywords.cloud_platform.system.host.objects.system_host_label_object import SystemHostLabelObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostLabelAssignOutput:
    """
    Class for System Host Label Output from 'system host-label-assign'
    """

    def __init__(self, system_host_label_output):
        """
            Parses the output of the system host-label-assign command. A sample output is shown below:

            +-------------+--------------------------------------+
            | Property    | Value                                |
            +-------------+--------------------------------------+
            | uuid        | b800c011-2065-4912-b1fd-4b4717cd5620 |
            | host_uuid   | 4feff42d-bc8d-4006-9922-a7fa10a6ee19 |
            | label_key   | kube-cpu-mgr-policy                  |
            | label_value | static                               |
            +-------------+--------------------------------------+
            +-------------+--------------------------------------+
            | Property    | Value                                |
            +-------------+--------------------------------------+
            | uuid        | 0260240f-bcca-41f5-9f32-b3acc030dfb0 |
            | host_uuid   | 4feff42d-bc8d-4006-9922-a7fa10a6ee19 |
            | label_key   | kube-topology-mgr-policy             |
            | label_value | best-effort                          |
            +-------------+--------------------------------------+

        Args:
            system_host_label_output: output of the system host-label-assign command
        """

        self.system_host_labels: [SystemHostLabelObject] = []
        system_table_parser = SystemTableParser(system_host_label_output)
        output_values = system_table_parser.get_output_values_list()

        # The table parser will treat all the rows has having two columns "Property" and "Value".
        # Sample output_values:
        # [{'Property': 'uuid', 'Value': 'b800c011-2065-4912-b1fd-4b4717cd5620'}
        #  {'Property': 'host_uuid', 'Value': '4feff42d-bc8d-4006-9922-a7fa10a6ee19'}
        #  {'Property': 'label_key', 'Value': 'kube-cpu-mgr-policy'}
        #  {'Property': 'label_value', 'Value': 'static'}
        #  {'Property': 'uuid', 'Value': '0260240f-bcca-41f5-9f32-b3acc030dfb0'}
        #  {'Property': 'host_uuid', 'Value': '4feff42d-bc8d-4006-9922-a7fa10a6ee19'}
        #  {'Property': 'label_key', 'Value': 'kube-topology-mgr-policy'}
        #  {'Property': 'label_value', 'Value': 'best-effort'}]

        system_host_label_object = SystemHostLabelObject()
        for value in output_values:

            if value['Property'] == 'uuid':  # Every time we hit a uuid, we are encountering a new object.
                system_host_label_object = SystemHostLabelObject()
                system_host_label_object.set_uuid(value['Value'])
                self.system_host_labels.append(system_host_label_object)

            if value['Property'] == 'host_uuid':
                system_host_label_object.set_host_uuid(value['Value'])

            if value['Property'] == 'label_key':
                system_host_label_object.set_label_key(value['Value'])

            if value['Property'] == 'label_value':
                system_host_label_object.set_label_value(value['Value'])

    def get_all_host_labels(self) -> [SystemHostLabelObject]:
        """
        Gets all the host label objects that were assigned
        Returns: List of all the SystemHostLabelObject

        """
        return self.system_host_labels
