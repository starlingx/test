from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.raw_metrics.object.kubectl_get_raw_metrics_output import KubectlGetRawMetricsOutput


class KubectlGetRawMetricsKeywords(BaseKeyword):
    """
    Keyword class for get raw metrics
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection(SSHConnection): SSH connection object
        """
        self.ssh_connection = ssh_connection

    def get_raw_metrics_with_grep(self, grep: str) -> list:
        """
        Retrieve raw Kubernetes metrics filtered by a grep pattern.

        Executes a kubectl command to fetch raw metrics from the Kubernetes API server,
        applying a grep filter to reduce the output size. The filtered metrics are then
        parsed and returned as a list.

        Args:
            grep (str): The pattern to filter the metrics output using grep.

        Returns:
            list: A list of filtered raw metrics lines matching the grep pattern.
        """
        command = export_k8s_config(f"kubectl get --raw /metrics |  grep {grep}")
        output = self.ssh_connection.send(command)
        raw_metrics_output = KubectlGetRawMetricsOutput(output)

        return raw_metrics_output

    def is_deprecated_api_found(self, expected_deprecated_output_group: str | list) -> bool:
        """
        Checks if any of the specified deprecated API groups are present in the Kubernetes API server metrics.

        Args:
            expected_deprecated_output_group (str | list): API group(s) to search for in the metrics.

        Returns:
            bool: True if any of the specified API groups are found, False otherwise.
        """
        output = self.get_raw_metrics_with_grep("apiserver_requested_deprecated_apis{")
        raw_metrics_obj_list = output.get_raw_metrics()
        for elem in raw_metrics_obj_list:
            if elem.get_labels().get("group") in expected_deprecated_output_group:
                found = True
                break
        else:
            found = False
        return found
