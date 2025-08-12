from typing import Dict, List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.kubernetes.object.kubernetes_version_list_object import KubernetesVersionListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class KubernetesVersionListOutput:
    """
    Represents the output of 'system kube-version-list' command as a list of KubernetesVersionListObject objects.
    """

    def __init__(self, system_kubernetes_version_list_output: list[str]) -> None:
        """
        Constructor

        Args:
            system_kubernetes_version_list_output (list[str]): output of 'system kube-version-list' command

        """
        self.k8s_version_list: [KubernetesVersionListObject] = []
        system_table_parser = SystemTableParser(system_kubernetes_version_list_output)
        self.output_values = system_table_parser.get_output_values_list()

        for value in self.output_values:
            if self.is_valid_output(value):
                self.k8s_version_list.append(
                    KubernetesVersionListObject(
                        value["version"],
                        value["target"],
                        value["state"],
                    )
                )
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_kubernetes_version(self) -> list:
        """
        Returns the list of kubernetes version objects
        """
        k8s_versions = [k8s["version"] for k8s in self.output_values]
        return k8s_versions

    def get_version_by_state(self, state: str) -> List[str]:
        """
        Gets the kubernetes version by state.

        Args:
            state (str): the version desired state.

        Returns:
            List[str]: The kubernetes version list.
        """
        k8s_versions = [entry["version"] for entry in self.output_values if entry["state"] == state]
        if not k8s_versions:
            raise KeywordException(f"No version with state {state} was found.")
        return k8s_versions

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """
        Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_keys = ["version", "target", "state"]
        for key in required_keys:
            if key not in value:
                get_logger().log_error(f"{key} is not in the output value: {value}")
                return False
        return True
