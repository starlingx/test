"""Table parser for kubectl get lease output."""

from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlGetLeaseTableParser(K8sTableParserBase):
    """Class for parsing the output of kubectl get lease commands."""

    def __init__(self, k8s_output: str | list[str]):
        """Initialize parser.

        Args:
            k8s_output (str | list[str]): Raw output of kubectl get lease.
        """
        super().__init__(k8s_output)
        self.possible_headers = [
            "NAME",
            "HOLDER",
            "AGE",
        ]
