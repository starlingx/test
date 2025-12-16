from typing import Any

import json5
from jinja2 import Template

from config.configuration_manager import ConfigurationManager
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords


class PTPTestScenarioReader:
    """
    Reader for PTP test scenarios from configuration files.
    """

    def __init__(self, ptp_setup_template_path: str):
        """
        Initialize the PTP test scenario reader.

        Args:
            ptp_setup_template_path (str): Path to the PTP setup template file.
        """
        self.ptp_setup_keywords = PTPSetupKeywords()
        self.ptp_setup_template_path = ptp_setup_template_path

        with open(ptp_setup_template_path, "r") as template_file:
            json5_template = template_file.read()

        ptp_config = ConfigurationManager.get_ptp_config()
        render_context = ptp_config.get_all_hosts_dictionary()

        rendered_config = Template(json5_template).render(render_context)
        self.config = json5.loads(rendered_config)
        self.config = PTPSetupKeywords._parse_embedded_json(self.config)

    def get_test_scenario(self, test_scenario_name: str) -> list:
        """
        Get test scenario steps by name.

        Args:
            test_scenario_name (str): Name of the test scenario.

        Returns:
            list: List of steps in the test scenario.
        """
        test_scenarios = self.config.get("test_scenarios", {})
        if test_scenario_name not in test_scenarios:
            raise ValueError(f"Test scenario '{test_scenario_name}' not found")
        return test_scenarios[test_scenario_name]

    def get_operation(self, operation_name: str) -> dict[str, Any]:
        """
        Get operation configuration by name.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            dict[str, Any]: Operation configuration.
        """
        test_scenarios = self.config.get("test_scenarios", {})
        for test_name, steps in test_scenarios.items():
            if isinstance(steps, list):
                for step in steps:
                    operations = step.get("operations", [])
                    for op in operations:
                        if op.get("name") == operation_name:
                            return {**op, **{k: v for k, v in step.items() if k != "operations"}}
        raise ValueError(f"Operation '{operation_name}' not found in test scenarios")

    def get_pmc_values(self, operation_name: str) -> list:
        """
        Get PMC values for an operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            list: PMC values.
        """
        operation = self.get_operation(operation_name)
        verification = operation.get("verification", {})
        return verification.get("pmc_values", [])

    def get_pmc_values_overrides(self, operation_name: str) -> list:
        """
        Get PMC values overrides for an operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            list: PMC values overrides.
        """
        operation = self.get_operation(operation_name)
        verification = operation.get("verification", {})
        return verification.get("pmc_values_overrides", [])

    def get_interface_mapping(self, operation_name: str) -> dict:
        """
        Get interface mapping for an operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            dict: Interface mapping configuration.
        """
        operation = self.get_operation(operation_name)
        return operation.get("interface_mapping", {})

    def get_interface_for_operation(self, operation_name: str) -> str:
        """
        Get interface for a specific operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            str: Interface name.
        """
        interface_mapping = self.get_interface_mapping(operation_name)
        ptp_instance = interface_mapping.get("ptp_instance")
        interface_name = interface_mapping.get("interface_name")
        hostname = interface_mapping.get("hostname")

        ptp_setup = self.ptp_setup_keywords.generate_ptp_setup_from_template(self.ptp_setup_template_path)
        interfaces = ptp_setup.get_ptp4l_setup(ptp_instance).get_ptp_interface(interface_name).get_interfaces_for_hostname(hostname)
        if not interfaces:
            raise Exception(f"No interfaces found for {hostname} in {ptp_instance}/{interface_name}")
        return interfaces[0]

    def get_alarm_config(self, operation_name: str) -> dict[str, Any]:
        """
        Get alarm configuration for an operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            dict[str, Any]: Alarm configuration.
        """
        operation = self.get_operation(operation_name)
        return operation.get("alarm_config", {})

    def get_gnss_config(self, operation_name: str) -> dict[str, Any]:
        """
        Get GNSS configuration for an operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            dict[str, Any]: GNSS configuration.
        """
        operation = self.get_operation(operation_name)
        return operation.get("gnss_config", {})

    def get_sma_config(self, operation_name: str) -> dict[str, Any]:
        """
        Get SMA configuration for an operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            dict[str, Any]: SMA configuration.
        """
        operation = self.get_operation(operation_name)
        return operation.get("sma_config", {})

    def get_interface_from_alarm_config(self, operation_name: str) -> str:
        """
        Get interface from alarm configuration.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            str: Interface name.
        """
        alarm_config = self.get_alarm_config(operation_name)
        hostname = alarm_config.get("hostname", "")
        nic = alarm_config.get("nic", "")

        ptp_config = ConfigurationManager.get_ptp_config()
        hostname_key = hostname.replace("-", "_")
        return ptp_config.get_host(hostname_key).get_nic(nic).get_base_port()

    def get_service_config(self, operation_name: str) -> dict[str, str]:
        """
        Get service configuration for an operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            dict[str, str]: Service configuration with service_name and instance_name.
        """
        operation = self.get_operation(operation_name)
        return operation.get("service_config", {})

    def get_proxmox_config(self, operation_name: str) -> dict[str, Any]:
        """
        Get Proxmox configuration for an operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            dict[str, Any]: Proxmox configuration.
        """
        operation = self.get_operation(operation_name)
        return operation.get("proxmox_config", {})

    def get_alarms(self, operation_name: str) -> list[dict[str, str]]:
        """
        Get alarms for an operation.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            list[dict[str, str]]: List of alarms.
        """
        operation = self.get_operation(operation_name)
        verification = operation.get("verification", [])
        if isinstance(verification, list):
            for verify_step in verification:
                if verify_step.get("type") == "alarm":
                    return verify_step.get("alarms", [])
        return []

    def create_alarm_objects(self, operation_name: str) -> list:
        """
        Create alarm objects from configuration.

        Args:
            operation_name (str): Name of the operation.

        Returns:
            list: List of AlarmListObject instances.
        """
        alarm_templates = self.get_alarms(operation_name)
        alarm_objects = []

        for template in alarm_templates:
            alarm_obj = AlarmListObject()
            alarm_obj.set_alarm_id(template.get("alarm_id", ""))
            alarm_obj.set_reason_text(template.get("reason_text", ""))
            alarm_obj.set_severity(template.get("severity", ""))

            entity_id = template.get("entity_id", "")
            if "{interface}" in entity_id:
                interface = self.get_interface_from_alarm_config(operation_name)
                entity_id = entity_id.replace("{interface}", interface)
            alarm_obj.set_entity_id(entity_id)

            alarm_objects.append(alarm_obj)

        return alarm_objects

    def get_base_pmc_values(self) -> list:
        """Get base PMC values from verification section.

        Returns:
            list: Base PMC values from verification.
        """
        verification = self.config.get("verification", [])
        if verification and isinstance(verification, list):
            for verify_item in verification:
                if verify_item.get("type") == "pmc_value":
                    return verify_item.get("pmc_values", [])
        return []
