from typing import List

from framework.logging.automation_logger import get_logger
from keywords.k8s.crd.object.kubectl_hosts_object import KubectlHostsObject
from keywords.k8s.crd.object.kubectl_hosts_table_parser import KubectlHostsTableParser


class KubectlHostsOutput:
    def __init__(self, kubectl_get_hosts_output: str):
        """
        Constructor

        Args:
            Kubectl get hosts -n deployment output: Raw string output from running a "kubectl get hosts -n deployment" command.

        """

        self.kubectl_hosts_objects: [KubectlHostsObject] = []
        kubectl_get_hosts_table_parser = KubectlHostsTableParser(kubectl_get_hosts_output)
        output_values_list = kubectl_get_hosts_table_parser.get_output_values_list()
        print("This is the output values list:", output_values_list)

        for host in output_values_list:
            if 'NAME' not in host:
                raise ValueError(f"There is no NAME associated with the host: {host}")

            hosts = KubectlHostsObject(host['NAME'])

            if 'INSYNC' in host:
                hosts.set_insync(host['INSYNC'])

            if 'RECONCILED' in host:
                hosts.set_reconcile(host['RECONCILED'])

            self.kubectl_hosts_objects.append(hosts)
           

