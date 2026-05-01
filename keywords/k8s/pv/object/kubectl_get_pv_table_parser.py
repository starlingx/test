"""Table parser for kubectl get pv output."""

from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlGetPvTableParser(K8sTableParserBase):
    """Parser for kubectl get pv command output."""

    def __init__(self, k8s_output: str):
        """Constructor.

        Args:
            k8s_output (str): Raw output from kubectl get pv command.
        """
        super().__init__(k8s_output)
        self.possible_headers = [
            "NAME",
            "CAPACITY",
            "ACCESS MODES",
            "RECLAIM POLICY",
            "STATUS",
            "CLAIM",
            "STORAGECLASS",
            "REASON",
            "AGE",
            "VOLUMEMODE",
        ]
