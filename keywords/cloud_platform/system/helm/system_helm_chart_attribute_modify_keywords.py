from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.helm.objects.system_helm_chart_attribute_modify_output import SystemHelmChartAttributeModifyOutput


class SystemHelmChartAttributeModifyKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system helm-chart-attribute-modify' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection object.

        """
        self.ssh_connection = ssh_connection

    def helm_chart_attribute_modify_enabled(self, enabled_value: str, app_name: str, chart_name: str, namespace: str) -> SystemHelmChartAttributeModifyOutput:
        """
        Modify helm chart attribute.

        Args:
            enabled_value (str): enabled_value to be modified
            app_name (str): Name of the application
            chart_name (str): Name of the chart
            namespace (str): Namespace of chart overrides

        """
        command = source_openrc(f"system helm-chart-attribute-modify --enabled {enabled_value} {app_name} {chart_name} {namespace}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_helm_chart_attribute_modify_output = SystemHelmChartAttributeModifyOutput(output)
        return system_helm_chart_attribute_modify_output
