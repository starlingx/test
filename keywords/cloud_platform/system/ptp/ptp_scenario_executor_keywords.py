import re
import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.ptp.objects.operation_type_object import OperationType
from keywords.cloud_platform.system.ptp.objects.status_constants_object import StatusConstants
from keywords.cloud_platform.system.ptp.objects.verification_type_object import VerificationType
from keywords.cloud_platform.system.ptp.ptp_verify_config_keywords import PTPVerifyConfigKeywords
from keywords.linux.ip.ip_keywords import IPKeywords
from keywords.linux.systemctl.systemctl_keywords import SystemCTLKeywords
from keywords.ptp.gnss_keywords import GnssKeywords
from keywords.ptp.phc_ctl_keywords import PhcCtlKeywords
from keywords.ptp.proxmox_ptp_setup_keywords import ProxmoxPTPSetupKeywords
from keywords.ptp.proxmox_ptp_verification_keywords import ProxmoxPTPVerificationKeywords
from keywords.ptp.ptp4l.ptp_service_status_validator import PTPServiceStatusValidator
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords
from keywords.ptp.setup.ptp_test_scenario_reader import PTPTestScenarioReader
from keywords.ptp.sma_keywords import SmaKeywords


class PTPScenarioExecutorKeywords(BaseKeyword):
    """Unified executor for PTP test scenarios."""

    def __init__(self, ssh_connection, resource_path: str):
        """Initialize PTP scenario executor.

        Args:
            ssh_connection: SSH connection to the system.
            resource_path (str): Path to PTP resource configuration file.
        """
        self.ssh_connection = ssh_connection
        self.resource_path = resource_path
        self.ptp_test_scenario_reader = PTPTestScenarioReader(resource_path)
        self.ptp_setup_keywords = PTPSetupKeywords()
        self.gnss_keywords = GnssKeywords()
        self.sma_keywords = SmaKeywords(ssh_connection)
        self.systemctl_keywords = SystemCTLKeywords(ssh_connection)
        self.alarm_keywords = AlarmListKeywords(ssh_connection)
        self.default_timeout = 120
        self.last_operation = None
        self.status = StatusConstants()

    def execute_test_scenario(self, test_scenario_data, request=None) -> None:
        """Execute complete test scenario with operations and verifications.

        Args:
            test_scenario_data (list): Optional list of test scenario step dictionaries.
            request: Pytest request fixture for finalizers (optional).
        """
        steps = test_scenario_data
        for step in steps:
            get_logger().log_info(f"Executing {step.get('description')}")
            operations = step.get("operations", [])
            verification = step.get("verification", [])

            self.execute_operations(operations, request)
            self.execute_verification(verification)

    def execute_operations(self, operations: list, request=None) -> None:
        """Execute operations based on type.

        Args:
            operations (list): List of operation dictionaries.
            request: Pytest request fixture for finalizers (optional).
        """
        for operation in operations:
            operation_type = operation.get("type")
            operation_name = operation.get("name")
            status = operation.get("status")

            get_logger().log_info(f"{operation.get('description')}")
            get_logger().log_info(f"Executing operation: {operation_name} (type: {operation_type}, status: {status})")

            self.last_operation = operation

            if operation_type == OperationType.interface:
                self._execute_interface_operation(operation)
            elif operation_type == OperationType.gnss:
                self._execute_gnss_operation(operation)
            elif operation_type == OperationType.sma:
                self._execute_sma_operation(operation)
            elif operation_type == OperationType.service:
                self._execute_service_operation(operation)
            elif operation_type == OperationType.phc_ctl:
                self._execute_phc_ctl_operation(operation)
            elif operation_type == OperationType.phc_ctl_loop:
                self._execute_phc_ctl_loop_operation(operation)
            elif operation_type == OperationType.proxmox:
                self._execute_proxmox_operation(operation, request)
            else:
                get_logger().log_info(f"Invalid operation has been selected {operation}")

    def execute_verification(self, verification: list) -> None:
        """Execute verification steps based on type.

        Args:
            verification (list): List of verification dictionaries.
        """
        for verify_step in verification:
            verify_type = verify_step.get("type")
            if verify_type == VerificationType.alarm:
                self._verify_alarms(verify_step)
            elif verify_type == VerificationType.pmc_value:
                self._verify_pmc(verify_step)
            elif verify_type == VerificationType.service_status:
                self._verify_service_status(verify_step)
            else:
                get_logger().log_info(f"Invalid type has been selected {verify_type}")

    def _execute_interface_operation(self, operation: dict) -> None:
        """Execute interface operation.

        Args:
            operation (dict): Operation configuration dictionary.
        """
        status = operation.get("status")
        interface_name = self.ptp_test_scenario_reader.get_interface_for_operation(operation["name"])
        ip_keywords = IPKeywords(self.ssh_connection)

        if status == self.status.get_interface_down():
            get_logger().log_info(f"Interface down {interface_name}.")
            ip_keywords.set_ip_port_state(interface_name, self.status.get_interface_down())
        else:
            get_logger().log_info(f"Interface up {interface_name}.")
            ip_keywords.set_ip_port_state(interface_name, "up")

    def _execute_gnss_operation(self, operation: dict) -> None:
        """Execute GNSS operation.

        Args:
            operation (dict): Operation configuration dictionary.
        """
        status = operation.get("status")
        gnss_config = self.ptp_test_scenario_reader.get_gnss_config(operation["name"])

        if status == self.status.get_gnss_sma_disable():
            get_logger().log_info(f"Turning off GNSS for {gnss_config['hostname']} {gnss_config['nic']}.")
            self.gnss_keywords.gnss_power_off(gnss_config["hostname"], gnss_config["nic"])
        # enable
        else:
            get_logger().log_info(f"Turning GNSS back on for {gnss_config['hostname']} {gnss_config['nic']}.")
            self.gnss_keywords.gnss_power_on(gnss_config["hostname"], gnss_config["nic"])

    def _execute_sma_operation(self, operation: dict) -> None:
        """Execute SMA operation.

        Args:
            operation (dict): Operation configuration dictionary.
        """
        status = operation.get("status")
        sma_config = self.ptp_test_scenario_reader.get_sma_config(operation["name"])

        if status == self.status.get_gnss_sma_disable():
            get_logger().log_info(f"Disabled SMA1 for {sma_config['hostname']} {sma_config['nic']}.")
            self.sma_keywords.disable_sma(sma_config["hostname"], sma_config["nic"])
        # enable
        else:
            get_logger().log_info(f"Enabled SMA1 for {sma_config['hostname']} {sma_config['nic']}.")
            self.sma_keywords.enable_sma(sma_config["hostname"], sma_config["nic"])

    def _execute_service_operation(self, operation: dict) -> None:
        """Execute service operation.

        Args:
            operation (dict): Operation configuration dictionary.
        """
        status = operation.get("status")
        service_config = self.ptp_test_scenario_reader.get_service_config(operation["name"])
        if status == self.status.get_service_stop():
            get_logger().log_info(f"Stopping {service_config['service_name']}@{service_config['instance_name']}.service...")
            self.systemctl_keywords.systemctl_stop(service_config["service_name"], service_config["instance_name"])
            time.sleep(10)
        elif status == self.status.get_service_start():
            get_logger().log_info(f"Starting {service_config['service_name']}@{service_config['instance_name']}.service...")
            self.systemctl_keywords.systemctl_start(service_config["service_name"], service_config["instance_name"])
        elif status == self.status.get_service_restart():
            get_logger().log_info(f"Restarting {service_config['service_name']}@{service_config['instance_name']}.service...")
            self.systemctl_keywords.systemctl_restart(service_config["service_name"], service_config["instance_name"])
        else:
            get_logger().log_info(f"Invalid status has been selected {status}")

    def _resolve_interface_placeholder(self, entity_id: str) -> str:
        """Resolve interface placeholders in entity_id.

        Args:
            entity_id (str): Entity ID with potential {interface} placeholder.

        Returns:
            str: Entity ID with interface placeholder replaced by actual interface name.
        """
        if "{interface}" not in entity_id:
            return entity_id

        match = re.search(r"host=([^.]+)", entity_id)
        if not match:
            return entity_id

        hostname = match.group(1).replace("-", "_")
        ptp_config = ConfigurationManager.get_ptp_config()
        host = ptp_config.get_host(hostname)
        nic = host.get_nic("nic1")
        interface = nic.get_base_port()
        return entity_id.replace("{interface}", interface)

    def _verify_alarms(self, verify_step: dict) -> None:
        """Verify alarms.

        Args:
            verify_step (dict): Verification step configuration.
        """
        alarm_dicts = verify_step.get("alarms", [])
        if not alarm_dicts:
            get_logger().log_info("No alarms to verify.")
            return

        alarm_objects = []
        for alarm_dict in alarm_dicts:
            alarm_obj = AlarmListObject()
            alarm_obj.set_alarm_id(alarm_dict.get("alarm_id", ""))
            alarm_obj.set_reason_text(alarm_dict.get("reason_text", ""))
            entity_id = self._resolve_interface_placeholder(alarm_dict.get("entity_id", ""))
            alarm_obj.set_entity_id(entity_id)
            alarm_objects.append(alarm_obj)

        timeout = verify_step.get("timeout", self.default_timeout)
        self.alarm_keywords.set_timeout_in_seconds(timeout)

        state = alarm_dicts[0].get("state", "set")
        if state == self.status.get_alarm_set():
            get_logger().log_info("Waiting for alarms to appear.")
            self.alarm_keywords.wait_for_alarms_to_appear(alarm_objects)
        else:
            get_logger().log_info("Waiting for alarms to clear.")
            self.alarm_keywords.wait_for_alarms_cleared(alarm_objects)

    def _verify_pmc(self, verify_step: dict) -> None:
        """Verify PMC values.

        If pmc_values_overrides is present or empty list: Merge with base pmc_values from verification and verify all
        If pmc_values is present: Verify only those specific values

        Args:
            verify_step (dict): Verification step configuration.
        """
        pmc_values = verify_step.get("pmc_values", [])
        pmc_values_overrides = verify_step.get("pmc_values_overrides")
        timeout = verify_step.get("timeout")

        if not pmc_values and pmc_values_overrides is None:
            get_logger().log_info("No PMC values to verify.")
            return

        get_logger().log_info("Verifying PMC data.")

        if pmc_values_overrides is not None:
            base_pmc = {item["name"]: item for item in self.ptp_test_scenario_reader.get_base_pmc_values()}
            override_pmc = {item["name"]: item for item in pmc_values_overrides}
            base_pmc.update(override_pmc)
            combined_pmc = base_pmc
            ptp_setup = self.ptp_setup_keywords.filter_and_render_ptp_config(self.resource_path, [[item["name"], hostname, []] for item in combined_pmc.values() for hostname in item.keys() if hostname != "name"], configuration_verification_overrides={"ptp4l": list(combined_pmc.values())})
        else:
            combined_pmc = {item["name"]: item for item in pmc_values}
            ptp_setup = self.ptp_setup_keywords.filter_and_render_ptp_config(self.resource_path, [[item["name"], hostname, []] for item in combined_pmc.values() for hostname in item.keys() if hostname != "name"], configuration_verification_overrides={"ptp4l": list(combined_pmc.values())})
        ptp_verify_config_keywords = PTPVerifyConfigKeywords(self.ssh_connection, ptp_setup)
        check_domain = not (self.last_operation and self.last_operation.get("type") == OperationType.service and self.last_operation.get("status") == self.status.get_service_stop())
        ptp_verify_config_keywords.verify_ptp_pmc_values_with_retry(check_domain=check_domain, timeout=timeout)

    def _verify_service_status(self, verify_step: dict) -> None:
        """Verify PTP service status.

        Args:
            verify_step (dict): Verification step with service_status list or flat structure.
        """
        service_status_list = verify_step.get("service_status", [])
        timeout = verify_step.get("timeout", 30)

        for service_status in service_status_list:
            service_name = service_status.get("service_name")
            instance_name = service_status.get("instance_name")
            expected_status = service_status.get("expected_status", "active (running)")

            get_logger().log_info(f"Verifying service status for {service_name}@{instance_name}.service")
            ptp_service_status_validator = PTPServiceStatusValidator(self.ssh_connection)
            ptp_service_status_validator.verify_service_status_and_recent_event(service_name, instance_name, timeout, expected_status)

    def _execute_phc_ctl_operation(self, operation: dict) -> None:
        """Execute PHC control operation.

        Args:
            operation (dict): Operation configuration dictionary.
        """
        interface_name = self.ptp_test_scenario_reader.get_interface_for_operation(operation["name"])
        interface_mapping = operation.get("interface_mapping", {})
        hostname = interface_mapping.get("hostname")
        status = operation.get("status")

        get_logger().log_info(f"Executing phc_ctl operation on {hostname} {interface_name}...")
        phc_ctl_keywords = PhcCtlKeywords(LabConnectionKeywords().get_ssh_for_hostname(hostname))

        if status == self.status.get_phc_ctl_adj():
            phc_ctl_keywords.phc_ctl_adj(interface_name, "0.0001")
        elif status == self.status.get_phc_ctl_set():
            phc_ctl_keywords.phc_ctl_set(interface_name)
        else:
            get_logger().log_info(f"Invalid status has been selected {status}")

    def _execute_phc_ctl_loop_operation(self, operation: dict) -> None:
        """Execute PHC control loop operation that waits for alarms.

        Args:
            operation (dict): Operation configuration dictionary.
        """
        interface_name = self.ptp_test_scenario_reader.get_interface_for_operation(operation["name"])
        alarm_objects = self.ptp_test_scenario_reader.create_alarm_objects(operation["name"])
        interface_mapping = operation.get("interface_mapping", {})
        hostname = interface_mapping.get("hostname")

        get_logger().log_info(f"Starting phc_ctl loop on {hostname} {interface_name} and waiting for alarms...")
        phc_ctl_keywords = PhcCtlKeywords(LabConnectionKeywords().get_ssh_for_hostname(hostname))
        phc_ctl_keywords.wait_for_phc_ctl_adjustment_alarm(interface_name, alarm_objects)

    def _execute_proxmox_operation(self, operation: dict, request=None) -> None:
        """Execute Proxmox PTP VM verification.

        Args:
            operation (dict): Operation configuration.
            request: Pytest request fixture for finalizers (optional).
        """
        proxmox_setup_keywords = ProxmoxPTPSetupKeywords()
        proxmox_keywords = proxmox_setup_keywords.setup_proxmox_environment(self.ptp_test_scenario_reader, self.resource_path, operation["name"])

        if request:

            def cleanup_ptp_service():
                get_logger().log_info("Test cleanup: Stopping PTP service")
                proxmox_keywords.stop_ptp_service()

            request.addfinalizer(cleanup_ptp_service)

        proxmox_verification_keywords = ProxmoxPTPVerificationKeywords()
        proxmox_verification_keywords.validate_all_ptp_data_sets_with_retry(proxmox_keywords, self.ptp_test_scenario_reader, self.resource_path, operation["name"])
