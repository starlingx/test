"""Table parser for 'calicoctl get workloadendpoints'."""

from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class CalicoctlWorkloadEndpointsTableParser(K8sTableParserBase):
    """Table parser for the column-aligned 'calicoctl get workloadendpoints' output."""

    def __init__(self, k8s_output: list[str]):
        """Initialize the parser.

        Args:
            k8s_output (list[str]): The output lines, starting with the header line.
        """
        super().__init__(k8s_output)
        self.possible_headers = ["NAMESPACE", "WORKLOAD", "NODE", "NETWORKS", "INTERFACE"]
