import json
from shlex import quote

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.daemonsets.objects.kubectl_get_daemonsets_output import KubectlGetDaemonsetsOutput
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.object.daemonset_workload_output import DaemonSetWorkloadOutput


class KubectlGetDaemonsetsKeywords(K8sBaseKeyword):
    """
    Kubectl get daemonsets keywords class
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        super().__init__(ssh_connection, kubeconfig_path)

    def get_daemonsets(self, namespace: str = None) -> KubectlGetDaemonsetsOutput:
        """Get the daemonsets returned by the kubectl get daemonsets command.

        Args:
            namespace (str, optional): namespace to query (-n <namespace>). When None, the command
                runs without a namespace flag, preserving the previous default-namespace behaviour.

        Returns:
            KubectlGetDaemonsetsOutput: Parsed daemonsets output.
        """
        namespace_arg = f" -n {namespace}" if namespace else ""
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get daemonsets{namespace_arg}"))
        self.validate_success_return_code(self.ssh_connection)
        get_daemonsets_output = KubectlGetDaemonsetsOutput(output)

        return get_daemonsets_output

    def get_daemonset_workload(self, namespace: str, daemonset_name: str | None = None) -> DaemonSetWorkloadOutput:
        """Read one DaemonSet and the complete node inventory.

        Args:
            namespace (str): Namespace containing the DaemonSet.
            daemonset_name (str | None): DaemonSet name; None requires exactly one in the namespace.

        Returns:
            DaemonSetWorkloadOutput: Fresh scheduling and rollout snapshot.
        """
        resource_keywords = KubectlGetResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())
        daemonset_output = json.loads(resource_keywords.get_resource_field("daemonsets", quote(daemonset_name) if daemonset_name else "", "{@}", quote(namespace)))
        daemonsets = [daemonset_output] if daemonset_name else daemonset_output["items"]
        if len(daemonsets) != 1:
            raise ValueError("Expected exactly one DaemonSet")
        nodes = json.loads(resource_keywords.get_resource_field("nodes", "", "{@}"))["items"]
        return DaemonSetWorkloadOutput(daemonsets[0], nodes)
