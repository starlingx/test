"""Keywords for kubectl get pv operations."""

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter
from keywords.k8s.pv.object.kubectl_get_pv_output import KubectlGetPvOutput
from keywords.k8s.pv.object.kubectl_pv_rbd_volume_object import KubectlPvRbdVolumeObject


class KubectlGetPvKeywords(BaseKeyword):
    """Keywords for kubectl get pv commands."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path.
        """
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)

    def get_pvs(self) -> KubectlGetPvOutput:
        """Get all PersistentVolumes in the cluster.

        Returns:
            KubectlGetPvOutput: Parsed output containing all PVs.
        """
        output = self.ssh_connection.send(self.k8s_config.export("kubectl get pv"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetPvOutput(output)

    def get_rbd_volume(self, pv_name: str) -> KubectlPvRbdVolumeObject:
        """Get the Ceph RBD pool and image name backing a CSI PersistentVolume.

        Reads the 'pool' and 'imageName' CSI volume attributes set by the Ceph RBD CSI driver.

        Args:
            pv_name (str): The PersistentVolume name.

        Returns:
            KubectlPvRbdVolumeObject: The RBD pool and image name of the PersistentVolume.

        Raises:
            KeywordException: If the PV does not expose RBD CSI volume attributes.
        """
        cmd = f"kubectl get pv {pv_name} -o jsonpath='{{.spec.csi.volumeAttributes.pool}} {{.spec.csi.volumeAttributes.imageName}}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        attributes = "".join(output).split()
        if len(attributes) != 2:
            raise KeywordException(f"Could not resolve the RBD pool and image name of PV '{pv_name}'. Raw output: '{' '.join(attributes)}'")
        pool, image_name = attributes
        return KubectlPvRbdVolumeObject(pool, image_name)
