"""Kubernetes PersistentVolumeClaim patch kubectl keywords."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords
from keywords.k8s.pvc.object.kubectl_get_pvcs_output import KubectlGetPvcsOutput


class KubectlPatchPvcKeywords(K8sBaseKeyword):
    """Keywords for 'kubectl patch pvc' operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize PVC patch keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path.
                If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def expand_pvc(self, pvc_name: str, new_size: str, namespace: str = "default") -> KubectlGetPvcsOutput:
        """Expand a PVC by patching its requested storage size.

        Asserts the patch command succeeds and then returns the current PVC state so the
        caller can read what it needs (e.g. capacity, status) from the object.

        Args:
            pvc_name (str): Name of the PVC to expand.
            new_size (str): New storage request (e.g., '10Gi').
            namespace (str): Namespace of the PVC. Defaults to 'default'.

        Returns:
            KubectlGetPvcsOutput: Parsed PVC collection after the patch was applied.
        """
        patch = f'{{"spec":{{"resources":{{"requests":{{"storage":"{new_size}"}}}}}}}}'
        cmd = f"kubectl patch pvc {pvc_name} -n {namespace} --type=merge -p '{patch}'"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetPvcKeywords(self.ssh_connection).get_pvc(pvc_name, namespace=namespace)

    def expand_pvc_with_error(self, pvc_name: str, new_size: str, namespace: str = "default") -> str:
        """Attempt to expand a PVC and return the command output without asserting success.

        Use this for negative testing where the patch is expected to be rejected (e.g. a
        StorageClass with allowVolumeExpansion false). The return code is not validated.

        Args:
            pvc_name (str): Name of the PVC to expand.
            new_size (str): New storage request (e.g., '10Gi').
            namespace (str): Namespace of the PVC. Defaults to 'default'.

        Returns:
            str: The raw output of the 'kubectl patch pvc' command.
        """
        patch = f'{{"spec":{{"resources":{{"requests":{{"storage":"{new_size}"}}}}}}}}'
        cmd = f"kubectl patch pvc {pvc_name} -n {namespace} --type=merge -p '{patch}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        return "\n".join(output) if isinstance(output, list) else output
