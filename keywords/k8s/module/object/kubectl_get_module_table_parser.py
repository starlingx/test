from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlGetModuleTableParser(K8sTableParserBase):
    """Class for parsing the output of kubectl get module commands."""

    def __init__(self, k8s_output: str | list[str]):
        """Initialize parser.

        Args:
            k8s_output (str | list[str]): Raw output of a kubernetes command that returns a table.
        """
        super().__init__(k8s_output)
        self.possible_headers = [
            "NAME",
            "AGE",
        ]
