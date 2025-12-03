from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.k8s.node.object.kubectl_nodes_object import KubectlNodesObject
from keywords.k8s.node.object.kubectl_nodes_table_parser import KubectlNodesTableParser


class KubectlNodesOutput:
    """
    Class for 'kubectl get nodes' output.
    """

    def __init__(self, kubectl_nodes_output: str):
        """
        Constructor

        Args:
            kubectl_nodes_output(str): Raw string output from running a "kubectl get nodes" command.

        """
        self.kubectl_nodes: list[KubectlNodesObject] = []
        k8s_table_parser = KubectlNodesTableParser(kubectl_nodes_output)
        output_values = k8s_table_parser.get_output_values_list()
        for value in output_values:
            if self.is_valid_output(value):
                kubectl_nodes_object = KubectlNodesObject()
                kubectl_nodes_object.set_name(value["NAME"])
                kubectl_nodes_object.set_status(value["STATUS"])
                kubectl_nodes_object.set_age(value["AGE"])
                kubectl_nodes_object.set_version(value["VERSION"])
                self.kubectl_nodes.append(kubectl_nodes_object)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_nodes(self) -> list[KubectlNodesObject]:
        """
        Returns the list of kubectl nodes objects.

        Returns:
            list[KubectlNodesObject]: List of KubectlNodesObject
        """
        return self.kubectl_nodes

    def get_node(self, node_name: str) -> KubectlNodesObject:
        """
        Returns the node with the given name

        Args:
            node_name (str): the name of the node

        Returns:
            KubectlNodesObject: kubectl node object
        """
        nodes = list(filter(lambda node: node.get_name() == node_name, self.kubectl_nodes))
        if len(nodes) == 0:
            raise KeywordException(f"No Node with name {node_name} was found.")

        return nodes[0]

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """
        Checks to ensure the output has the correct keys.

        Args:
            value (dict): The value to check.

        Returns:
            bool: True if valid, False otherwise.
        """
        valid = True
        if "NAME" not in value:
            get_logger().log_error(f"NAME is not in the output value: {value}")
            valid = False
        if "STATUS" not in value:
            get_logger().log_error(f"STATUS is not in the output value: {value}")
            valid = False
        if "ROLES" not in value:
            get_logger().log_error(f"ROLES is not in the output value: {value}")
            valid = False
        if "AGE" not in value:
            get_logger().log_error(f"AGE is not in the output value: {value}")
            valid = False
        if "VERSION" not in value:
            get_logger().log_error(f"VERSION is not in the output value: {value}")
            valid = False

        return valid
