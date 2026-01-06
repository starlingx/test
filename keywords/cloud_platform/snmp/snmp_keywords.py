import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.fm_client_cli_keywords import FaultManagementClientCLIKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.object.fm_client_cli_object import FaultManagementClientCLIObject
from keywords.cloud_platform.snmp.objects.snmp_output import SNMPOutput
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class SNMPKeywords(BaseKeyword):
    """Keywords for SNMP operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize SNMP keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.alarm_keywords = AlarmListKeywords(ssh_connection)
        self.fm_client_keywords = FaultManagementClientCLIKeywords(ssh_connection)
        self.config = ConfigurationManager.get_snmp_config()
        self.file_keywords = FileKeywords(ssh_connection)
        self.kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
        self.system_app_list = SystemApplicationListKeywords(ssh_connection)
        self.system_app_upload = SystemApplicationUploadKeywords(ssh_connection)
        self.system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        self.system_app_remove = SystemApplicationRemoveKeywords(ssh_connection)
        self.system_app_delete = SystemApplicationDeleteKeywords(ssh_connection)
        self.helm_override = SystemHelmOverrideKeywords(ssh_connection)
        self.kubectl_exec = KubectlExecInPodsKeywords(ssh_connection)

    def generate_test_alarm(self) -> None:
        """Generate a test alarm for SNMP testing."""
        alarm_obj = FaultManagementClientCLIObject()
        alarm_obj.set_alarm_id(self.config.get_trap_alarm_id())
        alarm_obj.set_entity_type_id(self.config.test_entity_type_id)
        alarm_obj.set_entity_id(self.config.test_entity_id)
        alarm_obj.set_severity(self.config.test_severity)
        alarm_obj.set_reason_text(self.config.test_reason_text)
        alarm_obj.set_alarm_type(self.config.test_alarm_type)

        self.fm_client_keywords.raise_alarm(alarm_obj)
        self.validate_success_return_code(self.ssh_connection)

    def remove_test_alarm(self) -> bool:
        """Remove the test alarm.

        Returns:
            bool: True if alarm removed successfully, False otherwise.
        """
        alarm_obj = FaultManagementClientCLIObject()
        alarm_obj.set_alarm_id(self.config.get_trap_alarm_id())
        alarm_obj.set_entity_id(self.config.test_entity_id)
        alarm_obj.set_entity_type_id(self.config.test_entity_type_id)

        self.fm_client_keywords.delete_alarm(alarm_obj)
        return self.ssh_connection.get_return_code() == 0

    def execute_snmp_command(self, command: str, oid: str, ip: str, port: int = 161, version: str = "v2c") -> SNMPOutput:
        """Execute SNMP command on the lab.

        Args:
            command (str): SNMP command type (get, walk, etc.).
            oid (str): SNMP OID to query.
            ip (str): Target IP address.
            port (int): SNMP port number.
            version (str): SNMP version (v2c or v3).

        Returns:
            SNMPOutput: SNMP command output.
        """
        lab_config = ConfigurationManager.get_lab_config()
        formatted_ip = f"[{ip}]" if lab_config.is_ipv6() else ip
        target = f"{formatted_ip}:{port}"

        if version == "v3":
            cmd = f"snmp{command} -v3 -a MD5 -A {self.config.snmp_v3_auth_password} -x DES -X {self.config.snmp_v3_priv_password} -l authPriv -u {self.config.snmp_v3_username} {target} {oid}"
        else:
            cmd = f"snmp{command} -v2c -c {self.config.snmp_v2c_community} {target} {oid}"

        output = self.ssh_connection.send(cmd)
        return_code = self.ssh_connection.get_return_code()

        return SNMPOutput(output, return_code)

    def snmp_get(self, oid: str, ip: str, port: int = 161, version: str = "v2c") -> SNMPOutput:
        """Execute SNMP get command."""
        return self.execute_snmp_command("get", oid, ip, port, version)

    def snmp_getnext(self, oid: str, ip: str, port: int = 161, version: str = "v2c") -> SNMPOutput:
        """Execute SNMP getnext command."""
        return self.execute_snmp_command("getnext", oid, ip, port, version)

    def snmp_bulkget(self, oid: str, ip: str, port: int = 161, version: str = "v2c") -> SNMPOutput:
        """Execute SNMP bulkget command."""
        return self.execute_snmp_command("bulkget", oid, ip, port, version)

    def snmp_walk(self, oid: str, ip: str, port: int = 161, version: str = "v2c") -> SNMPOutput:
        """Execute SNMP walk command."""
        return self.execute_snmp_command("walk", oid, ip, port, version)

    def get_next_alarm_oid(self) -> str:
        """Get next alarm OID based on active alarms.

        Returns:
            str: Next alarm OID to query.
        """
        active_alarms = self.alarm_keywords.alarm_list()
        index_previous = len(active_alarms) - 1

        if len(active_alarms) > 1:
            return f"{self.config.active_alarm_oid}.{index_previous}"
        else:
            return self.config.active_alarm_oid

    def get_active_alarm_count(self) -> int:
        """Get count of active alarms.

        Returns:
            int: Number of active alarms.
        """
        active_alarms = self.alarm_keywords.alarm_list()
        return len(active_alarms)

    def upload_snmp_config_files(self) -> None:
        """Upload SNMP config files to controller."""
        lab_config = ConfigurationManager.get_lab_config()
        config_file = self.config.config_file_ipv6 if lab_config.is_ipv6() else self.config.config_file_ipv4

        config_path = get_stx_resource_path(f"resources/cloud_platform/snmp/{config_file}")
        port_config_path = get_stx_resource_path(f"resources/cloud_platform/snmp/{self.config.port_config_file}")

        self.file_keywords.upload_file(config_path, f"/tmp/{config_file}")
        self.file_keywords.upload_file(port_config_path, f"/tmp/{self.config.port_config_file}")

    def upload_and_apply_snmp_app(self) -> None:
        """Upload and apply SNMP application using existing keywords."""
        app_name = self.config.get_snmp_app_name()

        if not self.system_app_list.is_app_present(app_name):
            upload_input = SystemApplicationUploadInput()
            upload_input.set_app_name(app_name)
            upload_input.set_tar_file_path(self.config.snmp_package_path)
            self.system_app_upload.system_application_upload(upload_input)

        app_list = self.system_app_list.get_system_application_list()
        if self.system_app_list.is_app_present(app_name):
            snmp_app = app_list.get_application(app_name)
            if snmp_app.get_status() not in ["applied", "applying"]:
                self.system_app_apply.system_application_apply(app_name)

    def wait_for_pods_ready(self, timeout: int = 300) -> bool:
        """Wait for SNMP pods to be ready using existing kubectl keywords.

        Args:
            timeout (int): Maximum time to wait in seconds.

        Returns:
            bool: True if pods are ready, False if timeout.
        """
        timeout_time = time.time() + timeout
        while time.time() < timeout_time:
            pods = self.kubectl_pods.get_pods(namespace="kube-system")
            snmp_pods = [pod for pod in pods.get_pods() if "snmp" in pod.get_name()]
            if snmp_pods and all(self.is_pod_ready(pod) for pod in snmp_pods):
                return True
            time.sleep(5)
        return False

    def is_pod_ready(self, pod: object) -> bool:
        """Check if a Kubernetes pod is ready.

        Args:
            pod (object): Pod object that provides get_status() and get_ready() methods.

        Returns:
            bool: True if the pod is ready, False otherwise.
        """
        if pod.get_status() != "Running":
            return False
        ready_status = pod.get_ready()
        if not ready_status or "/" not in ready_status:
            return False
        ready_parts = ready_status.split("/")
        return len(ready_parts) == 2 and ready_parts[0] == ready_parts[1]

    def install_and_configure_snmp_complete(self) -> bool:
        """Complete SNMP installation and configuration.

        Returns:
            bool: True if installation successful, False otherwise.
        """
        self.upload_snmp_config_files()
        self.upload_and_apply_snmp_app()
        self.generate_test_alarm()
        return self.wait_for_pods_ready()

    def apply_snmp_helm_overrides(self) -> bool:
        """Apply SNMP helm overrides and reapply application.

        Returns:
            bool: True if successful, False otherwise.
        """
        lab_config = ConfigurationManager.get_lab_config()
        config_file = self.config.config_file_ipv6 if lab_config.is_ipv6() else self.config.config_file_ipv4

        # Use direct command to avoid parsing issues
        cmd = f"system helm-override-update --values /tmp/{config_file} snmp snmp kube-system"
        self.ssh_connection.send(source_openrc(cmd))
        if self.ssh_connection.get_return_code() != 0:
            return False

        # Reapply SNMP application
        self.system_app_apply.system_application_apply(self.config.get_snmp_app_name())
        return True

    def apply_port_helm_overrides(self) -> bool:
        """Apply port helm overrides for nginx and reapply.

        Returns:
            bool: True if successful, False otherwise.
        """
        # Use direct command to avoid parsing issues
        cmd = f"system helm-override-update --values /tmp/{self.config.port_config_file} nginx-ingress-controller ks-ingress-nginx kube-system"
        self.ssh_connection.send(source_openrc(cmd))
        if self.ssh_connection.get_return_code() != 0:
            return False

        # Reapply nginx-ingress-controller
        self.system_app_apply.system_application_apply("nginx-ingress-controller")
        return True

    def restore_port_helm_overrides(self) -> None:
        """Restore default port helm overrides for nginx."""
        # Use direct command for reset-values as it's not in the existing class
        cmd = "system helm-override-update --reset-values nginx-ingress-controller ks-ingress-nginx kube-system"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        # Reapply nginx-ingress-controller
        self.system_app_apply.system_application_apply("nginx-ingress-controller")

    def install_and_configure_snmp(self) -> None:
        """Install and configure SNMP application."""
        self.upload_snmp_config_files()
        self.upload_and_apply_snmp_app()

        # Apply helm overrides - continue even if they fail
        snmp_override_success = self.apply_snmp_helm_overrides()
        port_override_success = self.apply_port_helm_overrides()

        if not snmp_override_success:
            get_logger().log_info("SNMP helm override failed, continuing with default config")
        if not port_override_success:
            get_logger().log_info("Port helm override failed, continuing with default config")

    def remove_and_cleanup_snmp(self) -> None:
        """Remove and cleanup SNMP application."""
        # Restore port helm overrides first
        self.restore_port_helm_overrides()

        app_name = self.config.get_snmp_app_name()
        if self.system_app_list.is_app_present(app_name):
            remove_input = SystemApplicationRemoveInput()
            remove_input.set_app_name(app_name)
            self.system_app_remove.system_application_remove(remove_input)

            delete_input = SystemApplicationDeleteInput()
            delete_input.set_app_name(app_name)
            self.system_app_delete.get_system_application_delete(delete_input)

    def get_running_snmp_pod_name(self) -> str:
        """Get name of running SNMP pod.

        Returns:
            str: Name of running SNMP pod, empty string if none found.
        """
        pods = self.kubectl_pods.get_pods(namespace="kube-system")
        snmp_pods = [pod for pod in pods.get_pods() if "snmp" in pod.get_name() and pod.get_status() == "Running"]
        return snmp_pods[0].get_name() if snmp_pods else ""

    def get_snmp_config_object(self, pod_name: str) -> SNMPOutput:
        """Get SNMP configuration from pod.

        Args:
            pod_name (str): Name of the SNMP pod.

        Returns:
            SNMPOutput: SNMP configuration output.
        """
        exec_output = self.kubectl_exec.run_pod_exec_cmd(pod_name, "cat /etc/snmp/snmpd.conf", "-n kube-system")
        return SNMPOutput(exec_output, 0)

    def check_config_patterns_present(self, config_content: str) -> bool:
        """Check if required configuration patterns are present.

        Args:
            config_content (str): Configuration content to check.

        Returns:
            bool: True if all patterns present, False otherwise.
        """
        required_patterns = self.config.required_config_patterns
        return all(pattern in config_content for pattern in required_patterns)

    def wait_for_alarm_in_snmp(self, oid: str, ip: str, timeout: int = 60, version: str = "v3") -> bool:
        """Wait for alarm to appear in SNMP output.

        Args:
            oid (str): SNMP OID to query.
            ip (str): Target IP address.
            timeout (int): Maximum time to wait in seconds.
            version (str): SNMP version (v2c or v3).

        Returns:
            bool: True if alarm found, False if timeout.
        """
        timeout_time = time.time() + timeout
        while time.time() < timeout_time:
            snmp_output = self.snmp_get(oid, ip, version=version)
            snmp_result = snmp_output.get_snmp_object()

            if snmp_result and snmp_result.contains_alarm_id(self.config.get_trap_alarm_id()):
                get_logger().log_info(f"Alarm found in SNMP output: {snmp_result.get_content()}")
                return True

            time.sleep(2)
        return False
