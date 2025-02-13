from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlGetSecretsTableParser(K8sTableParserBase):
    """
    Class for parsing the output of "kubectl get secret" commands.
    """

    def __init__(self, k8s_output):
        """_
        Constructor
        Args:
            k8s_output (_type_): _description_
        """
        super().__init__(k8s_output)
        self.possible_headers = [
            "NAME",
            "TYPE",
            "DATA",
            "AGE",
        ]
