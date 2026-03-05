from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sysctl.sysctl_keywords import SysctlKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords

SYSCTL_PARAMS = [("kernel.hung_task_timeout_secs", "90"), ("vm.swappiness", "80"), ("vm.dirty_ratio", "16"), ("kernel.domainname", "LAB1")]


@mark.p0
def test_add_parameter() -> None:
    """Add sysctl parameters to system configuration.

    This function adds sysctl parameters to the system and validates they're applied.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    service_keywords = SystemServiceParameterKeywords(ssh_connection)
    sysctl_keywords = SysctlKeywords(ssh_connection)

    # Get sysctl parameters once
    param_list = service_keywords.list_service_parameters(section="sysctl").get_parameters()
    param_names = [param.name for param in param_list]
    param_dict = dict(zip(param_names, param_list))

    for param_name, param_value in SYSCTL_PARAMS:
        get_logger().log_info(f"Adding sysctl parameter {param_name}={param_value}")

        param_found = param_dict.get(param_name)
        if param_found:
            get_logger().log_info(f"Parameter exists, modifying to {param_value}")
            service_keywords.modify_service_parameter("platform", "sysctl", param_name, param_value)
        else:
            get_logger().log_info("Adding new parameter")
            service_keywords.add_service_parameter("platform", param_name, param_value, "sysctl")

    # Verify all parameters are applied
    for param_name, param_value in SYSCTL_PARAMS:
        get_logger().log_info(f"Waiting for parameter {param_name} to be applied...")
        validate_equals_with_retry(
            # Get parsed sysctl value
            function_to_execute=lambda p=param_name: sysctl_keywords.get_sysctl_value(p),
            expected_value=param_value,
            validation_description=f"Parameter {param_name} applied",
            timeout=60,
            polling_sleep_time=5,
        )
        get_logger().log_info(f"✓ Parameter {param_name}={param_value} successfully applied")


@mark.p0
def test_verify_persistence() -> None:
    """Verify sysctl parameters persistence after restore.

    This function verifies that the sysctl parameters persisted after backup and restore.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    service_keywords = SystemServiceParameterKeywords(ssh_connection)
    sysctl_keywords = SysctlKeywords(ssh_connection)

    get_logger().log_info("Verifying sysctl parameters persistence after restore")

    # Get sysctl parameters once
    param_list = service_keywords.list_service_parameters(section="sysctl").get_parameters()
    param_names = [param.name for param in param_list]
    param_dict = dict(zip(param_names, param_list))

    for param_name, param_value in SYSCTL_PARAMS:
        # Verify live sysctl parameter value matches expected
        actual_value = sysctl_keywords.get_sysctl_value(param_name)
        validate_equals(actual_value, param_value, f"Parameter {param_name} persisted in sysctl")

        # Verify parameter exists and has correct value in database
        param_found = param_dict.get(param_name)
        validate_equals(param_found is not None, True, f"Parameter {param_name} exists in database")
        validate_equals(param_found.value, param_value, f"Parameter {param_name} value in database")

        get_logger().log_info(f"Parameter {param_name}={param_value} persisted after restore")
