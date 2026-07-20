from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.objects.system_helm_override_output import SystemHelmOverrideOutput
from keywords.cloud_platform.system.helm.objects.system_helm_override_show_output import SystemHelmOverrideShowOutput
from keywords.files.file_keywords import FileKeywords


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

    def update_helm_override(self, yaml_file: str, app_name: str, chart_name: str, namespace: str, reuse_values: bool = False) -> SystemHelmOverrideOutput:
        """Gets the system helm-override list.

        Args:
            yaml_file (str): the yaml file with override values
            app_name (str): the app name
            chart_name (str): the chart name
            namespace (str): the namespace
            reuse_values (bool): whether to reuse existing values

        Returns:
            SystemHelmOverrideOutput: object with the list of helm overrides.
        """
        reuse_flag = "--reuse-values " if reuse_values else ""
        command = source_openrc(f"system helm-override-update {reuse_flag}--values {yaml_file} {app_name} {chart_name} {namespace}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_helm_override_output = SystemHelmOverrideOutput(output)
        return system_helm_override_output

    def update_helm_override_via_set(self, override_values: str, app_name: str, chart_name: str, namespace: str, reuse_values: bool = False, reapply: str = "") -> SystemHelmOverrideOutput:
        """
        Update the helm-override values via --set parameter

        Args:
            override_values (str): override values
            app_name (str): the app name
            chart_name (str): the chart name
            namespace (str): the namespace
            reuse_values (bool): whether to reuse existing values
            reapply (str): reapply flag, can be "--reapply" or "--reapply-all". Triggers an evaluation
                of the target application for reapply. Reapply will only occur if the application has
                pending override changes and declares the on-demand-reapply trigger in its metadata.yaml.

        Returns:
            SystemHelmOverrideOutput: object with the list of helm overrides.
        """
        reuse_flag = "--reuse-values " if reuse_values else ""
        reapply_flag = f"{reapply} " if reapply else ""
        command = source_openrc(f"system helm-override-update --set {override_values} {app_name} {chart_name} {namespace} {reuse_flag} {reapply_flag}")
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

    def helm_override_update_with_list_of_values(self, app_name: str, chart_name: str, namespace: str, reuse_values: bool, set_override: list):
        """
        Update helm chart user overrides using set of values with set and reuse values overrides

        Args:
            app_name (str): Name of the application
            chart_name (str): Name of the chart
            namespace (str): Namespace of chart overrides
            reuse_values (bool): Whether to reuse existing values
            set_override (list): List of override values to set

        """
        reuse_flag = "--reuse-values " if reuse_values else ""
        set_values = " ".join(f"--set {item}" for item in set_override)
        command = source_openrc(f"system helm-override-update {app_name} {chart_name} {namespace} {reuse_flag} {set_values}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def apply_if_changed(
        self,
        desired_overrides: str,
        app_name: str,
        chart_name: str,
        namespace: str,
        timeout: int = 3600,
        polling_sleep_time: int = 30,
        force_apply: bool = False,
    ) -> bool:
        """Apply helm overrides only if they differ from the currently applied overrides.

        Compares the desired override YAML against the current user_overrides on the
        system. If they match (semantic YAML equality), skips the expensive
        update + apply sequence. If they differ, writes the override file,
        updates the helm override, and applies the application.

        Args:
            desired_overrides (str): YAML string of desired helm overrides.
            app_name (str): Application name (e.g., "stx-openstack").
            chart_name (str): Chart name (e.g., "cinder").
            namespace (str): Namespace (e.g., "openstack").
            timeout (int): Timeout in seconds for system_application_apply. Default 3600.
            polling_sleep_time (int): Polling interval in seconds. Default 30.
            force_apply (bool): If True, always apply regardless of match. Default False.

        Returns:
            bool: True if the apply was executed, False if it was skipped.

        Raises:
            ValueError: If app_name, chart_name, or namespace is None/empty.
        """
        if not app_name:
            raise ValueError("app_name must not be None or empty")
        if not chart_name:
            raise ValueError("chart_name must not be None or empty")
        if not namespace:
            raise ValueError("namespace must not be None or empty")

        app_apply_kw = SystemApplicationApplyKeywords(self.ssh_connection)

        if force_apply:
            get_logger().log_info(f"Force-applying helm overrides for {app_name}/{chart_name} in {namespace}")
            desired_empty = desired_overrides is None or desired_overrides.strip() == ""
            if desired_empty:
                app_apply_kw.system_application_apply(app_name, timeout=timeout, polling_sleep_time=polling_sleep_time)
            else:
                self._write_and_apply(desired_overrides, app_name, chart_name, namespace, timeout, polling_sleep_time)
            return True

        # Normal path: retrieve current overrides and compare
        try:
            show_output = self.get_system_helm_override_show(app_name, chart_name, namespace)
            show_object = show_output.get_helm_override_show()
        except Exception as e:
            get_logger().log_warning(f"Failed to retrieve current overrides for {app_name}/{chart_name} " f"in {namespace}: {e} — proceeding with apply")
            self._write_and_apply(desired_overrides, app_name, chart_name, namespace, timeout, polling_sleep_time)
            return True

        if show_object.user_overrides_match(desired_overrides):
            get_logger().log_info(f"Helm override apply skipped — overrides already match for " f"{app_name}/{chart_name} in {namespace}")
            return False

        get_logger().log_info(f"Helm override apply executed for {app_name}/{chart_name} in {namespace}")
        self._write_and_apply(desired_overrides, app_name, chart_name, namespace, timeout, polling_sleep_time)
        return True

    def _write_and_apply(
        self,
        desired_overrides: str,
        app_name: str,
        chart_name: str,
        namespace: str,
        timeout: int,
        polling_sleep_time: int,
    ) -> None:
        """Write override file to temp dir, update helm override, apply, and clean up.

        Args:
            desired_overrides (str): YAML string of desired helm overrides.
            app_name (str): Application name.
            chart_name (str): Chart name.
            namespace (str): Namespace.
            timeout (int): Timeout in seconds for system_application_apply.
            polling_sleep_time (int): Polling interval in seconds.
        """
        file_kw = FileKeywords(self.ssh_connection)
        app_apply_kw = SystemApplicationApplyKeywords(self.ssh_connection)

        output = self.ssh_connection.send("mktemp -d -p /tmp")
        tmpdir = output[0].strip() if isinstance(output, list) else output.strip()
        override_file_path = f"{tmpdir}/helm_overrides.yaml"
        try:
            file_kw.create_file_with_heredoc(override_file_path, desired_overrides)
            self.update_helm_override(override_file_path, app_name, chart_name, namespace)
            app_apply_kw.system_application_apply(app_name, timeout=timeout, polling_sleep_time=polling_sleep_time)
        finally:
            self.ssh_connection.send(f"rm -rf {tmpdir}")
