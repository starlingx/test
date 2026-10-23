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

            if value["hostname"]:
                system_host_label_object.set_host_name(value["hostname"])

            if value["label key"]:
                system_host_label_object.set_label_key(value["label key"])

            if value["label value"]:
                system_host_label_object.set_label_value(value["label value"])

            self.system_host_labels.append(system_host_label_object)

    def get_hosts_labels(self) -> list[SystemHostLabelObject]:
        """Return the list of system host label objects.

        Returns:
            list[SystemHostLabelObject]: the parsed host label objects.
        """
        return self.system_host_labels

    def get_label_value(self, label_key: str) -> str:
        """Return the value of the label with the given key.

        Args:
            label_key (str): the key name to get the value for.

        Returns:
            str: the label value, or None if the key was not found.
        """
        label_keys = list(filter(lambda label: label.get_label_key() == label_key, self.system_host_labels))
        if len(label_keys) == 0:
            return None  # no key was found

        return label_keys[0].get_label_value()

    def is_label_present(self, label_key: str) -> bool:
        """Check whether a label key is present in this output.

        Args:
            label_key (str): The label key to look for (e.g. 'kube-cpu-mgr-policy').

        Returns:
            bool: True if the label key is present, False otherwise.
        """
        return self.get_label_value(label_key) is not None

    def is_label_value_set(self, label_key: str, label_value: str) -> bool:
        """Check whether a label key is set to a specific value in this output.

        Args:
            label_key (str): The label key to look for (e.g. 'kube-cpu-mgr-policy').
            label_value (str): The expected label value (e.g. 'static').

        Returns:
            bool: True if the label key is present and equals label_value, False otherwise.
        """
        return self.get_label_value(label_key) == label_value
