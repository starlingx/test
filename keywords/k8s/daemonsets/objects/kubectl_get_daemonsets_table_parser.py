from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlGetDaemonsetsTableParser(K8sTableParserBase):
    """
    Class for parsing the output of "kubectl get daemonsets" commands.
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
            "DESIRED",
            "CURRENT",
            "READY",
            "UP-TO-DATE",
            "AVAILABLE",
            "NODE SELECTOR",
            "AGE",
        ]
