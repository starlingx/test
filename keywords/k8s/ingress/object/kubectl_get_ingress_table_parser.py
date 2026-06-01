"""Table parser for ``kubectl get ingress`` output."""

from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlGetIngressTableParser(K8sTableParserBase):
    """
    Class for parsing the output of "kubectl get ingress" commands.

    Example raw output::

        NAME                CLASS   HOSTS               ADDRESS         PORTS    AGE
        mon-kibana          nginx   mon-kibana.svc      10.10.10.5      80, 443  3d
        mon-elasticsearch   nginx   mon-es.svc          10.10.10.5      80, 443  3d
    """

    def __init__(self, k8s_output):
        """
        Constructor
        Args:
            k8s_output: The raw String output of a kubernetes command that returns a table.
        """
        super().__init__(k8s_output)
        self.possible_headers = [
            "NAME",
            "CLASS",
            "HOSTS",
            "ADDRESS",
            "PORTS",
            "AGE",
        ]
