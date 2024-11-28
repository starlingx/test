from typing import List

from framework.logging.automation_logger import get_logger
from keywords.k8s.daemonsets.objects.kubectl_get_daemonsets_object import KubectlDaemonsetsObject
from keywords.k8s.daemonsets.objects.kubectl_get_daemonsets_table_parser import KubectlGetDaemonsetsTableParser


class KubectlGetDaemonsetsOutput:

    def __init__(self, kubectl_get_daemonsets_output: str):
        """
        Constructor

        Args:
            kubectl_get_daemonsets_output: Raw string output from running a "kubectl get daemonsets" command.

        """

        self.kubectl_daemonesets: [KubectlDaemonsetsObject] = []
        kubectl_get_daemonsets_table_parser = KubectlGetDaemonsetsTableParser(kubectl_get_daemonsets_output)
        output_values_list = kubectl_get_daemonsets_table_parser.get_output_values_list()

        for daemonset_dict in output_values_list:

            if 'NAME' not in daemonset_dict:
                raise ValueError(f"There is no NAME associated with the daemonset: {daemonset_dict}")

            daemonset = KubectlDaemonsetsObject(daemonset_dict['NAME'])

            if 'DESIRED' in daemonset_dict:
                daemonset.set_desired(int(daemonset_dict['DESIRED']))

            if 'CURRENT' in daemonset_dict:
                daemonset.set_current(int(daemonset_dict['CURRENT']))

            if 'READY' in daemonset_dict:
                daemonset.set_ready(int(daemonset_dict['READY']))

            if 'UP-TO-DATE' in daemonset_dict:
                daemonset.set_up_to_date(int(daemonset_dict['UP-TO-DATE']))

            if 'AVAILABLE' in daemonset_dict:
                daemonset.set_available(int(daemonset_dict['AVAILABLE']))

            if 'NODE SELECTOR' in daemonset_dict:
                daemonset.set_node_selector(daemonset_dict['NODE SELECTOR'])

            if 'AGE' in daemonset_dict:
                daemonset.set_age(daemonset_dict['AGE'])

            self.kubectl_daemonesets.append(daemonset)

    def get_daemonsets(self) -> List[KubectlDaemonsetsObject]:
        """
        This function will get the list of all daemonsets available.

        Returns: List of KubectlDaemonsetObjects

        """
        return self.kubectl_daemonesets

    def get_daemonset(self, name) -> KubectlDaemonsetsObject:
        """
        This function will return the daemonset with the given name
        Args:
            name (): the name

        Returns:

        """

        daemonsets = list(filter(lambda daemonset: daemonset.get_name() == name, self.kubectl_daemonesets))

        if len(daemonsets) == 0:
            get_logger().log_error(f"unable to find daemonset with name {name}")
            return None

        # should only be 1
        return daemonsets[0]
