from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than, validate_greater_than_or_equal, validate_less_than_or_equal, validate_not_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.linux.occtop.occtop_keywords import OcctopKeywords


@mark.p0
def test_occtop_execution_on_active_controller():
    """Test that occtop executes successfully on the active controller and produces valid output.

    Test Steps:
        - Connect to the active controller via SSH
        - Run occtop with a period of 1 second
        - Validate the header contains a non-empty hostname matching the active controller
        - Validate the CPU count in the header is greater than zero
        - Validate at least one sample is present with per-CPU occupancy values
        - Validate the number of per-CPU values matches the CPU count from the header
        - Validate all per-CPU occupancy values are between 0.0 and 100.0 inclusive

    """
    # Connect to the active controller
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()
    active_controller_hostname = active_controller.get_host_name()
    get_logger().log_info(f"Connected to active controller: {active_controller_hostname}")

    # Run occtop with period=1
    occtop_output = OcctopKeywords(ssh_connection).run_occtop(period=1)
    validate_not_none(occtop_output, "occtop command should produce valid output")

    # Validate header hostname matches active controller
    hostname = occtop_output.get_hostname()
    validate_not_none(hostname, "occtop header should contain a hostname")
    validate_equals(hostname, active_controller_hostname, "occtop hostname should match active controller hostname")
    get_logger().log_info(f"Header hostname: {hostname}")

    # Validate CPU count is greater than zero
    cpu_count = occtop_output.get_cpu_count()
    validate_greater_than(cpu_count, 0, "CPU count should be greater than zero")
    get_logger().log_info(f"CPU count: {cpu_count}")

    # Validate at least one sample is present
    samples = occtop_output.get_samples()
    sample_count = occtop_output.get_sample_count()
    validate_greater_than(sample_count, 0, "occtop should collect at least one sample")
    get_logger().log_info(f"Number of samples collected: {sample_count}")

    # Validate per-CPU occupancy values
    for i, sample in enumerate(samples):
        per_cpu_values = sample['per_cpu']
        validate_not_none(per_cpu_values, f"Sample {i} should have per-CPU occupancy values")

        # Validate the number of per-CPU values matches the header CPU count
        validate_equals(len(per_cpu_values), cpu_count, f"Sample {i} per-CPU value count should match header CPU count")

        # Validate all values are between 0.0 and 100.0 inclusive
        for cpu_index, value in enumerate(per_cpu_values):
            validate_greater_than_or_equal(value, 0.0, f"Sample {i}, CPU {cpu_index}: occupancy value should be >= 0.0")
            validate_less_than_or_equal(value, 100.0, f"Sample {i}, CPU {cpu_index}: occupancy value should be <= 100.0")

    get_logger().log_info("All occtop output validations passed successfully")
