from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.ptp.pmc.pmc_keywords import PMCKeywords
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords


class ProxmoxPTPVerificationKeywords(BaseKeyword):
    """Keywords for Proxmox PTP VM verification operations."""

    def validate_port_data_set_with_retry(self, pmc_keywords, proxmox_config: dict, ptp_config_file: str, timeout: int = None) -> None:
        """
        Validate PORT_DATA_SET.

        Args:
            pmc_keywords: PMC keywords instance.
            proxmox_config (dict): Proxmox configuration.
            ptp_config_file (str): PTP configuration file path.
            timeout (int): Timeout in seconds for retrying validations.
        """
        get_logger().log_info("Validating PORT_DATA_SET - checking port state")
        validate_equals_with_retry(lambda: pmc_keywords.pmc_get_port_data_set(ptp_config_file).get_pmc_get_port_data_set_objects()[0].get_port_state(), proxmox_config["expected_port_state"], f"Port state should be {proxmox_config['expected_port_state']} (receiving time from master)", timeout)

    def validate_parent_data_set_with_retry(self, pmc_keywords, ptp1_expected_config, proxmox_config: dict, ptp_config_file: str, timeout: int = None) -> None:
        """
        Validate PARENT_DATA_SET.

        Args:
            pmc_keywords: PMC keywords instance.
            ptp1_expected_config: Expected PTP configuration.
            proxmox_config (dict): Proxmox configuration.
            ptp_config_file (str): PTP configuration file path.
            timeout (int): Timeout in seconds for retrying validations.
        """
        get_logger().log_info("Validating PARENT_DATA_SET - checking GM clock properties")
        expected_parent_data_set = ptp1_expected_config.get_parent_data_set_for_hostname(proxmox_config["validation_hostname"])

        def check_parent_data_set() -> bool:
            parent_data_set_obj = pmc_keywords.pmc_get_parent_data_set(ptp_config_file).get_pmc_get_parent_data_set_object()

            gm_clock_class_match = parent_data_set_obj.get_gm_clock_class() in expected_parent_data_set.get_gm_clock_class()
            gm_clock_accuracy_match = parent_data_set_obj.get_gm_clock_accuracy() == expected_parent_data_set.get_gm_clock_accuracy()
            gm_offset_match = parent_data_set_obj.get_gm_offset_scaled_log_variance() == expected_parent_data_set.get_gm_offset_scaled_log_variance()

            if not (gm_clock_class_match and gm_clock_accuracy_match and gm_offset_match):
                get_logger().log_info(f"[Proxmox VM] Parent data set mismatch - gm_clock_class: {parent_data_set_obj.get_gm_clock_class()} (expected: {expected_parent_data_set.get_gm_clock_class()}), gm_clock_accuracy: {parent_data_set_obj.get_gm_clock_accuracy()} (expected: {expected_parent_data_set.get_gm_clock_accuracy()}), gm_offset: {parent_data_set_obj.get_gm_offset_scaled_log_variance()} (expected: {expected_parent_data_set.get_gm_offset_scaled_log_variance()})")

            return gm_clock_class_match and gm_clock_accuracy_match and gm_offset_match

        validate_equals_with_retry(check_parent_data_set, True, "Parent data set values (gm.ClockClass, gm.ClockAccuracy, gm.OffsetScaledLogVariance)", timeout)

    def validate_parent_port_identity_with_retry(self, pmc_keywords, proxmox_config: dict, ptp_config_file: str, ssh_connection, timeout: int = None) -> None:
        """
        Cross-validate parent port identity with master configuration.

        Args:
            pmc_keywords: PMC keywords instance.
            proxmox_config (dict): Proxmox configuration.
            ptp_config_file (str): PTP configuration file path.
            ssh_connection: SSH connection to controller-0.
            timeout (int): Timeout in seconds for retrying validations.
        """
        get_logger().log_info("Cross-validating parent port identity with master port data set")

        master_port_response = PMCKeywords(ssh_connection).pmc_get_port_data_set(proxmox_config["master_ptp_config_path"], proxmox_config["master_ptp_uds_path"])
        master_port_objects = master_port_response.get_pmc_get_port_data_set_objects()
        if len(master_port_objects) < 1:
            raise Exception(f"Expected at least 1 port data set object, but found {len(master_port_objects)}")
        expected_master_port_identity = master_port_objects[0].get_port_identity()
        expected_port_identity = expected_master_port_identity.split("-")[0]

        validate_equals_with_retry(lambda: pmc_keywords.pmc_get_parent_data_set(ptp_config_file).get_pmc_get_parent_data_set_object().get_parent_port_identity().split("-")[0], expected_port_identity, "Parent port identity matches the master port identity", timeout)

    def validate_time_properties_data_set_with_retry(self, pmc_keywords, ptp1_expected_config, proxmox_config: dict, ptp_config_file: str, timeout: int = None) -> None:
        """
        Validate TIME_PROPERTIES_DATA_SET.

        Args:
            pmc_keywords: PMC keywords instance.
            ptp1_expected_config: Expected PTP configuration.
            proxmox_config (dict): Proxmox configuration.
            ptp_config_file (str): PTP configuration file path.
            timeout (int): Timeout in seconds for retrying validations.
        """
        get_logger().log_info("Validating TIME_PROPERTIES_DATA_SET - checking UTC offset and traceability")
        expected_time_properties = ptp1_expected_config.get_time_properties_data_set_for_hostname(proxmox_config["validation_hostname"])

        def check_time_properties_data_set() -> bool:
            time_properties_obj = pmc_keywords.pmc_get_time_properties_data_set(ptp_config_file).get_pmc_get_time_properties_data_set_object()

            current_utc_offset_match = time_properties_obj.get_current_utc_offset() == expected_time_properties.get_current_utc_offset()
            current_utc_offset_valid_match = time_properties_obj.get_current_utc_off_set_valid() == expected_time_properties.get_current_utc_offset_valid()
            time_traceable_match = time_properties_obj.get_time_traceable() == expected_time_properties.get_time_traceable()
            frequency_traceable_match = time_properties_obj.get_frequency_traceable() == expected_time_properties.get_frequency_traceable()

            if not (current_utc_offset_match and current_utc_offset_valid_match and time_traceable_match and frequency_traceable_match):
                get_logger().log_info(f"[Proxmox VM] Time properties data set mismatch - currentUtcOffset: {time_properties_obj.get_current_utc_offset()} (expected: {expected_time_properties.get_current_utc_offset()}), currentUtcOffsetValid: {time_properties_obj.get_current_utc_off_set_valid()} (expected: {expected_time_properties.get_current_utc_offset_valid()}), timeTraceable: {time_properties_obj.get_time_traceable()} (expected: {expected_time_properties.get_time_traceable()}), frequencyTraceable: {time_properties_obj.get_frequency_traceable()} (expected: {expected_time_properties.get_frequency_traceable()})")

            return current_utc_offset_match and current_utc_offset_valid_match and time_traceable_match and frequency_traceable_match

        validate_equals_with_retry(check_time_properties_data_set, True, "Time properties data set values (currentUtcOffset, currentUtcOffsetValid, timeTraceable, frequencyTraceable)", timeout)

    def validate_all_ptp_data_sets_with_retry(self, proxmox_keywords, ptp_test_scenario_reader, ptp_setup_template_path: str, operation_name: str, timeout: int = 300) -> None:
        """
        Validate all PTP data sets.

        Args:
            proxmox_keywords: Proxmox keywords instance.
            ptp_test_scenario_reader: PTP test scenario reader instance.
            ptp_setup_template_path (str): Path to PTP setup template.
            operation_name (str): Operation name from test scenario.
            timeout (int): Timeout in seconds for retrying validations (default: 300).
        """
        proxmox_config = ptp_test_scenario_reader.get_proxmox_config(operation_name)
        ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(proxmox_config["hostname"])

        operation = ptp_test_scenario_reader.get_operation(operation_name)
        verification = operation.get("verification", {})
        pmc_values = []
        for verify_step in verification:
            verify_type = verify_step.get("type")
            if verify_type == "pmc_value":
                pmc_values = verify_step.get("pmc_values", [])

        ptp_instance_selection = [[pmc_val["name"], hostname, []] for pmc_val in pmc_values for hostname in pmc_val.keys() if hostname != "name"]
        ptp_expected_setup = PTPSetupKeywords().filter_and_render_ptp_config(ptp_setup_template_path, ptp_instance_selection)
        ptp1_expected_config = ptp_expected_setup.get_pmc_values_expected_by_name(proxmox_config["ptp_instance"])

        pmc_keywords = PMCKeywords(proxmox_keywords.get_proxmox_vm_ssh_connection())
        ptp_config_file = proxmox_config["ptp_config_file"]

        self.validate_port_data_set_with_retry(pmc_keywords, proxmox_config, ptp_config_file, timeout)
        self.validate_parent_data_set_with_retry(pmc_keywords, ptp1_expected_config, proxmox_config, ptp_config_file, timeout)
        self.validate_parent_port_identity_with_retry(pmc_keywords, proxmox_config, ptp_config_file, ssh_connection, timeout)
        self.validate_time_properties_data_set_with_retry(pmc_keywords, ptp1_expected_config, proxmox_config, ptp_config_file, timeout)
