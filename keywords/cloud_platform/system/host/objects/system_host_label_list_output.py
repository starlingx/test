from keywords.cloud_platform.system.host.objects.system_host_label_object import SystemHostLabelObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostLabelListOutput:
    """
    Class for System Host Label Output
    """

    def __init__(self, system_host_label_output):
        self.system_host_labels: [SystemHostLabelObject] = []
        system_table_parser = SystemTableParser(system_host_label_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            system_host_label_object = SystemHostLabelObject()

            if value['hostname']:
                system_host_label_object.set_host_name(value['hostname'])

            if value['label key']:
                system_host_label_object.set_label_key(value['label key'])

            if value['label value']:
                system_host_label_object.set_label_value(value['label value'])

            self.system_host_labels.append(system_host_label_object)

    def get_hosts_labels(self) -> [SystemHostLabelObject]:
        """
        Returns the list of system host label objects
        Returns:

        """
        return self.system_host_labels

    def get_label_value(self, label_key: str) -> SystemHostLabelObject:
        """
        Returns the value of the key with the given label
        Args:
            label_key (): the key name to get the value for

        Returns:

        """
        label_keys = list(filter(lambda label: label.get_label_key() == label_key, self.system_host_labels))
        if len(label_keys) == 0:
            return None  # no key was found

        return label_keys[0].get_label_value()
