"""Keywords for creating Calico IPPool resources."""

import yaml

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCreateIppoolKeywords(K8sBaseKeyword):
    """Class for creating Calico IPPool resources via the crd.projectcalico.org/v1 API.

    The aggregated projectcalico.org/v3 API is served by calico-apiserver, which the
    Calico operator does not deploy by default; the underlying CRD (crd.projectcalico.org/v1)
    is always present, so IPPools are created through it.
    """

    def create_ippool(self, pool_name: str, cidr: str, block_size: int, nat_outgoing: bool = True) -> None:
        """Create a Calico IPPool.

        The manifest is written to a file on the target and applied from there, so no
        value is interpolated into a shell command.

        Args:
            pool_name (str): The metadata.name for the IP pool.
            cidr (str): The pool CIDR (e.g. '192.168.200.0/24' or 'fd00:10:96::/112').
            block_size (int): The block size for the pool (e.g. 26 for IPv4, 122 for IPv6).
            nat_outgoing (bool): Whether NAT outgoing is enabled. Defaults to True.

        Raises:
            KeywordException: If the manifest file could not be written on the target.
        """
        get_logger().log_info(f"Creating Calico IPPool '{pool_name}' with CIDR {cidr}")
        pool_definition = {
            "apiVersion": "crd.projectcalico.org/v1",
            "kind": "IPPool",
            "metadata": {"name": pool_name},
            "spec": {
                "cidr": cidr,
                "natOutgoing": nat_outgoing,
                "nodeSelector": "all()",
                "blockSize": block_size,
                "ipipMode": "Never",
                "vxlanMode": "Never",
                "disabled": False,
            },
        }
        remote_path = f"/tmp/ippool_{pool_name}.yaml"
        file_keywords = FileKeywords(self.ssh_connection)
        if not file_keywords.create_file_with_heredoc(remote_path, yaml.safe_dump(pool_definition)):
            raise KeywordException(f"Failed to write the IPPool manifest {remote_path}")
        KubectlFileApplyKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).apply_resource_from_yaml(remote_path)
        file_keywords.delete_file(remote_path)
