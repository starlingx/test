"""Kubernetes PersistentVolumeClaim table parser."""

from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlGetPvcsTableParser(K8sTableParserBase):
    """Parser for 'kubectl get pvc -o wide' table output."""

    def __init__(self, k8s_output: str) -> None:
        """Initialize PVC table parser.

        Args:
            k8s_output (str): Raw table output from 'kubectl get pvc'.
        """
        super().__init__(k8s_output)
        self.possible_headers = [
            "NAME",
            "NAMESPACE",
            "STATUS",
            "VOLUME",
            "CAPACITY",
            "ACCESS MODES",
            "STORAGECLASS",
            "VOLUMEATTRIBUTESCLASS",
            "AGE",
            "VOLUMEMODE",
        ]
