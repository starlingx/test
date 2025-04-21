from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SystemHelmKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system helm' commands.
    """
    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection


    def helm_override_update(self, app_name: str, chart_name: str, namespace: str, values: str):
        """
        Update helm chart user overrides.

        Args:
            app_name (str): Name of the application
            chart_name (str): Name of the chart
            namespace (str): Namespace of chart overrides
            values (str): YAML file containing helm chart override values

        """

        command = source_openrc(f"system helm-override-update {app_name} {chart_name} {namespace} --values {values}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)