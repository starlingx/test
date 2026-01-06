from typing import List

from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlGetGlobalNetworkPolicyTableParser(K8sTableParserBase):
    """
    Class for parsing the output of "kubectl get globalnetworkpolicies.crd.projectcalico.org" commands.
    """

    def __init__(self, k8s_output: List[str]):
        """Constructor.

        Args:
            k8s_output (List[str]): The raw String output of a kubernetes command that returns a table.
        """
        super().__init__(k8s_output)
        self.possible_headers = [
            "NAME",
            "AGE",
        ]
