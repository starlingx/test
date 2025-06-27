from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_list_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.ptp.pmc.pmc_keywords import PMCKeywords
from keywords.ptp.proxmox_keywords import ProxmoxKeywords
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords


@mark.p2
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_proxmox_ptp_vm_verification(request):
    """
    Test PTP VM verification with automatic service recovery.

    This test verifies PTP (Precision Time Protocol) functionality in a Proxmox VM environment
    by checking service status, retrieving PTP data sets, and validating against expected values.

    Test Steps:
        - Connect to PTP VM and setup test environment
        - Verify PTP service is running (auto-start if needed)
        - Validate PORT_DATA_SET - Check port state is SLAVE
        - Validate PARENT_DATA_SET - Verify GM clock properties
        - Validate TIME_PROPERTIES_DATA_SET - Check UTC offset and traceability
        - Cross-validate parent port identity with master configuration

    Expected Results:
        - PTP service runs successfully with auto-recovery capability
        - Port operates in SLAVE state as expected
        - Parent data set matches expected GM clock configuration
        - Time properties align with system UTC settings
        - Parent port identity correctly maps to master port

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_configuration_expectation_compute.json5.
    """

    def cleanup_ptp_service():
        """Cleanup function to stop PTP service after test completion"""
        get_logger().log_info("Test cleanup: Stopping PTP service")
        proxmox_keywords.stop_ptp_service()

    request.addfinalizer(cleanup_ptp_service)

    lab_connect_keywords = LabConnectionKeywords()
    controller_0_ssh_connection = lab_connect_keywords.get_ssh_for_hostname("controller-0")

    # Get Proxmox VM configuration for PTP testing
    ptp_config = ConfigurationManager.get_ptp_config()
    proxmox_vm_config = ptp_config.get_host("controller_0").get_nic("nic1").get_proxmox_ptp_vm_config()
    proxmox_keywords = ProxmoxKeywords(proxmox_vm_config)

    # PTP configuration file path in the VM
    ptp_config_file = "/etc/ptp4l.conf"

    # Load expected PTP configuration from template
    ptp_setup_keywords = PTPSetupKeywords()
    expected_config_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")

    # Define PTP instances and interfaces for both controllers
    ptp_instance_selection = [("ptp1", "controller-0", ["ptp1if1", "ptp1if2"]), ("ptp1", "controller-1", ["ptp1if1", "ptp1if2"])]
    ptp_expected_setup = ptp_setup_keywords.filter_and_render_ptp_config(expected_config_template_path, ptp_instance_selection)

    # Get expected configuration for ptp1 instance
    ptp1_expected_config = ptp_expected_setup.get_ptp4l_expected_by_name("ptp1")

    get_logger().log_info("Starting PTP VM verification with auto-recovery capability")

    # Verify PTP service is running, auto-start if needed
    get_logger().log_info("Verifying PTP service status and enabling auto-recovery")
    proxmox_keywords.verify_ptp_service_with_auto_recovery()

    # Initialize PMC (PTP Management Client) for data retrieval
    proxmox_vm_ssh_connection = proxmox_keywords.get_proxmox_vm_ssh_connection()
    pmc_keywords = PMCKeywords(proxmox_vm_ssh_connection)

    get_logger().log_info("Validating PORT_DATA_SET - checking port state")
    # Retrieve current port data set from PTP service
    port_data_set_response = pmc_keywords.pmc_get_port_data_set(ptp_config_file)
    observed_port_data_sets = port_data_set_response.get_pmc_get_port_data_set_objects()

    # Ensure we have at least one port data set object
    if len(observed_port_data_sets) < 1:
        raise Exception(f"Expected at least 1 port data set object, but found {len(observed_port_data_sets)}")

    # Use the first port data set for validation
    current_port_data_set = observed_port_data_sets[0]

    # Validate port is operating in SLAVE state (receiving time from master)
    validate_equals(current_port_data_set.get_port_state(), "SLAVE", "Port state should be SLAVE (receiving time from master)")

    get_logger().log_info("Validating PARENT_DATA_SET - checking GM clock properties")
    # Retrieve parent data set (information about the master clock)
    parent_data_set_response = pmc_keywords.pmc_get_parent_data_set(ptp_config_file)
    current_parent_data_set = parent_data_set_response.get_pmc_get_parent_data_set_object()

    # Get expected parent data set configuration for controller-1
    expected_parent_data_set = ptp1_expected_config.get_parent_data_set_for_hostname("controller-1")

    validate_list_contains(current_parent_data_set.get_gm_clock_class(), expected_parent_data_set.get_gm_clock_class(), "gm.ClockClass value within GET PARENT_DATA_SET")
    validate_equals(current_parent_data_set.get_gm_clock_accuracy(), expected_parent_data_set.get_gm_clock_accuracy(), "gm.ClockAccuracy value within GET PARENT_DATA_SET")
    validate_equals(current_parent_data_set.get_gm_offset_scaled_log_variance(), expected_parent_data_set.get_gm_offset_scaled_log_variance(), "gm.OffsetScaledLogVariance value within GET PARENT_DATA_SET")

    get_logger().log_info("Cross-validating parent port identity with master port data set")

    # Get master port data set from PTP configuration
    master_port_response = PMCKeywords(controller_0_ssh_connection).pmc_get_port_data_set("/etc/linuxptp/ptpinstance/ptp4l-ptp1.conf", "/var/run/ptp4l-ptp1")
    master_port_objects = master_port_response.get_pmc_get_port_data_set_objects()

    if len(master_port_objects) < 1:
        raise Exception(f"Expected at least 1 port data set object, but found {len(master_port_objects)}")
    # Extract master port identity (use first available port)
    expected_master_port_identity = master_port_objects[0].get_port_identity()

    # Compare parent port identity with master port identity (clock ID portion)
    current_parent_port_identity = current_parent_data_set.get_parent_port_identity()
    expected_port_identity = expected_master_port_identity.split("-")[0]
    current_port_identity = current_parent_port_identity.split("-")[0]
    validate_equals(current_port_identity, expected_port_identity, "Parent port identity matches the master port identity")

    get_logger().log_info("Validating TIME_PROPERTIES_DATA_SET - checking UTC offset and traceability")

    # Retrieve time properties data set (UTC and traceability information)
    time_properties_response = pmc_keywords.pmc_get_time_properties_data_set(ptp_config_file)
    current_time_properties = time_properties_response.get_pmc_get_time_properties_data_set_object()

    # Extract current time properties
    current_utc_offset = current_time_properties.get_current_utc_offset()
    current_utc_offset_valid = current_time_properties.get_current_utc_off_set_valid()
    current_time_traceable = current_time_properties.get_time_traceable()
    current_frequency_traceable = current_time_properties.get_frequency_traceable()

    # Get expected time properties configuration
    expected_time_properties = ptp1_expected_config.get_time_properties_data_set_for_hostname("controller-1")
    expected_utc_offset = expected_time_properties.get_current_utc_offset()
    expected_utc_offset_valid = expected_time_properties.get_current_utc_offset_valid()
    expected_time_traceable = expected_time_properties.get_time_traceable()
    expected_frequency_traceable = expected_time_properties.get_frequency_traceable()

    # Validate all time properties
    validate_equals(current_utc_offset, expected_utc_offset, "currentUtcOffset value within GET TIME_PROPERTIES_DATA_SET")
    validate_equals(current_utc_offset_valid, expected_utc_offset_valid, "currentUtcOffsetValid value within GET TIME_PROPERTIES_DATA_SET")
    validate_equals(current_time_traceable, expected_time_traceable, "timeTraceable value within GET TIME_PROPERTIES_DATA_SET")
    validate_equals(current_frequency_traceable, expected_frequency_traceable, "frequencyTraceable value within GET TIME_PROPERTIES_DATA_SET")
    get_logger().log_info("TIME_PROPERTIES_DATA_SET validation completed - all time properties verified")
