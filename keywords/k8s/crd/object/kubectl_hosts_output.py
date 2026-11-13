from typing import List

from framework.logging.automation_logger import get_logger
from keywords.k8s.crd.object.kubectl_hosts_object import KubectlHostsObject
from keywords.k8s.crd.object.kubectl_hosts_table_parser import KubectlHostsTableParser


class KubectlHostsOutput:
    """Parsed output of the 'kubectl get hosts' command."""

    def __init__(self, kubectl_get_hosts_output: str | list):
        """Constructor.

        Args:
            kubectl_get_hosts_output (str | list): Raw output from running a "kubectl get hosts -n deployment" command, as returned by the SSH connection.

        Raises:
            ValueError: If a host in the output has no NAME.
        """
        self.kubectl_hosts_objects: List[KubectlHostsObject] = []
        kubectl_get_hosts_table_parser = KubectlHostsTableParser(kubectl_get_hosts_output)
        output_values_list = kubectl_get_hosts_table_parser.get_output_values_list()
        get_logger().log_debug(f"Parsed 'kubectl get hosts' output values: {output_values_list}")

        for host in output_values_list:
            if "NAME" not in host:
                raise ValueError(f"There is no NAME associated with the host: {host}")

            hosts = KubectlHostsObject(host["NAME"])

            if "INSYNC" in host:
                hosts.set_insync(host["INSYNC"])

            if "RECONCILED" in host:
                hosts.set_reconcile(host["RECONCILED"])

            self.kubectl_hosts_objects.append(hosts)

    def get_hosts(self) -> List[KubectlHostsObject]:
        """Get all hosts objects.

        Returns:
            List[KubectlHostsObject]: List of all hosts objects.
        """
        return self.kubectl_hosts_objects

    def get_host(self, name: str) -> KubectlHostsObject:
        """Get a specific host by name.

        Args:
            name (str): Host name.

        Returns:
            KubectlHostsObject: The host object.

        Raises:
            ValueError: If no host with the specified name is found.
        """
        for host in self.kubectl_hosts_objects:
            if host.get_name() == name:
                return host
        raise ValueError(f"There is no host with the name {name}.")

    def is_all_reconciled(self) -> bool:
        """Check if all hosts are reconciled.

        Like KubectlSystemsOutput, this is True when the output has no hosts.
        A host without a RECONCILED value counts as not reconciled.

        Returns:
            bool: True if all hosts have reconciled=true.
        """
        return all(host.get_reconcile() == "true" for host in self.kubectl_hosts_objects)

    def is_all_insync(self) -> bool:
        """Check if all hosts are insync.

        Like KubectlSystemsOutput, this is True when the output has no hosts.
        A host without an INSYNC value counts as not insync.

        Returns:
            bool: True if all hosts have insync=true.
        """
        return all(host.get_insync() == "true" for host in self.kubectl_hosts_objects)
