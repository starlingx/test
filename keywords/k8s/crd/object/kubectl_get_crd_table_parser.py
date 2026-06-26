"""Table parser for kubectl get crd output."""

from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlGetCrdTableParser(K8sTableParserBase):
    """Class for parsing the output of kubectl get crd commands."""

    def __init__(self, k8s_output: str | list[str]):
        """Initialize parser.

        Args:
            k8s_output (str | list[str]): Raw output of kubectl get crd.
        """
        super().__init__(k8s_output)
        self.possible_headers = [
            "NAME",
            "CREATED AT",
        ]
