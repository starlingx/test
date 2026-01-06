from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.helm.objects.system_helm_override_output import SystemHelmOverrideOutput
from keywords.cloud_platform.system.helm.objects.system_helm_override_show_output import SystemHelmOverrideShowOutput


class SystemHelmOverrideKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system helm-override' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the KubectlGetPodsKeywords class.

        Args:
            ssh_connection (SSHConnection): An SSH connection object to the target system.
        """
        self.ssh_connection = ssh_connection

    def update_helm_override(self, yaml_file: str, app_name: str, chart_name: str, namespace: str) -> SystemHelmOverrideOutput:
        """
        Gets the system helm-override list

        Args:
            yaml_file (str): the yaml file with override values
            app_name (str): the app name
            chart_name (str): the chart name
            namespace (str): the namespace

        Returns:
            SystemHelmOverrideOutput: object with the list of helm overrides.
        """
        command = source_openrc(f"system helm-override-update --values {yaml_file} {app_name} {chart_name} {namespace}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_helm_override_output = SystemHelmOverrideOutput(output)
        return system_helm_override_output

    def update_helm_override_via_set(self, override_values: str, app_name: str, chart_name: str, namespace: str) -> SystemHelmOverrideOutput:
        """
        Update the helm-override values via --set parameter

        Args:
            override_values (str): override values
            app_name (str): the app name
            chart_name (str): the chart name
            namespace (str): the namespace

        Returns:
            SystemHelmOverrideOutput: object with the list of helm overrides.
        """
        command = source_openrc(f"system helm-override-update --set {override_values} {app_name} {chart_name} {namespace}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_helm_override_output = SystemHelmOverrideOutput(output)
        return system_helm_override_output

    def get_system_helm_override_show(self, app_name: str, chart_name: str, namespace: str) -> SystemHelmOverrideShowOutput:
        """
        Gets the system helm-override show

        Args:
            app_name (str): the app name
            chart_name (str): the chart name
            namespace (str): the namespace

        Returns:
            SystemHelmOverrideShowOutput: The parsed helm override show object.
        """
        command = source_openrc(f"system helm-override-show {app_name} {chart_name} {namespace}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_helm_override_show_output = SystemHelmOverrideShowOutput(output)
        return system_helm_override_show_output

    def verify_helm_user_override(self, label: str, app_name: str, chart_name: str, namespace: str):
        """
        Verifies the user override

        Args:
            label (str): the label
            app_name (str): the app name
            chart_name (str): the chart name
            namespace (str): the namespace
        """
        user_override = self.get_system_helm_override_show(app_name, chart_name, namespace).get_helm_override_show().get_user_overrides()

        validate_str_contains(user_override, label, "User Override")

    def get_system_helm_override_list(self, app_name: str) -> SystemHelmOverrideOutput:
        """
        Gets the system helm-override show

        Args:
            app_name (str): the app name

        Returns:
            SystemHelmOverrideOutput: The parsed helm override list object.
        """
        command = source_openrc(f"system helm-override-list {app_name} ")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_helm_override_show_output = SystemHelmOverrideOutput(output)
        return system_helm_override_show_output

    def delete_system_helm_override(self, app_name: str, chart_name: str, namespace: str) -> None:
        """
        Gets the system helm-override show

        Args:
            app_name (str): the app name
            chart_name (str): the chart name
            namespace (str): the namespace
        """
        self.ssh_connection.send(source_openrc(f"system helm-override-delete {app_name} {chart_name} {namespace}"))
        self.validate_success_return_code(self.ssh_connection)
