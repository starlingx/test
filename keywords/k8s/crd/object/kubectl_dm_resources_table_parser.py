"""Table parser for Deployment Manager CRD resources."""

import re

from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


class KubectlDmResourcesTableParser(K8sTableParserBase):
    """Parses the table output of 'kubectl get <dm-resource> -n deployment'.

    The Deployment Manager CRDs (DataNetwork, PtpInstance, PtpInterface, System, ...) each print a
    different set of default columns, so the headers are taken from the header line itself instead of
    from a fixed list.
    """

    def __init__(self, k8s_output: list[str]):
        """Constructor.

        Args:
            k8s_output (list[str]): The raw output lines of a kubectl command that returns a table.
        """
        super().__init__(k8s_output)
        header_line = k8s_output[0] if k8s_output else ""
        self.possible_headers = re.findall(r"\S+", header_line)
