"""
Negative test cases for DC enrollment and restore error handling.

Validates that dcmanager produces clear, actionable error messages when users
provide invalid inputs or attempt operations in wrong states during subcloud
factory install enrollment and backup restore workflows.
"""

import os

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords

MISSING_BOOTSTRAP_FIELD_SCENARIOS = [("name", "Unable to generate subcloud region for subcloud None"), ("system_mode", "system_mode required"), ("external_oam_subnet", "external_oam_subnet required"), ("external_oam_gateway_address", "external_oam_gateway_address required"), ("external_oam_floating_address", "external_oam_floating_address required"), ("systemcontroller_gateway_address", "systemcontroller_gateway_address required"), ("management_subnet", "management_subnet required"), ("management_start_address", "management_start_address required"), ("management_end_address", "management_end_address required"), ("management_gateway_address", "management_gateway_address required")]

MISSING_INSTALL_VALUES_FIELD_SCENARIOS = [("bootstrap_interface", "Mandatory install value bootstrap_interface not present"), ("bootstrap_address", "Mandatory install value bootstrap_address not present"), ("bootstrap_address_prefix", "Mandatory install value bootstrap_address_prefix not present"), ("install_type", "Mandatory install value install_type not present"), ("bmc_username", "Mandatory install value bmc_username not present"), ("bmc_address", "Mandatory install value bmc_address not present")]

INVALID_INSTALL_VALUES_FORMAT_SCENARIOS = [
    # (description, field_to_modify, new_value, expected_error)
    ("bmc_address garbage value", "bmc_address", "INVALID", "bmc_address invalid: failed to detect a valid IP address from 'INVALID'"),
    ("bmc_address malformed IP", "bmc_address", "999.999.999.999", "bmc_address invalid: failed to detect a valid IP address from '999.999.999.999'"),
    ("bootstrap_address garbage value", "bootstrap_address", "INVALID", "bootstrap_address invalid: failed to detect a valid IP address from 'INVALID'"),
    ("bootstrap_address malformed IP", "bootstrap_address", "999.999.999.999", "bootstrap_address invalid: failed to detect a valid IP address from '999.999.999.999'"),
    ("bmc_address IPv4 with IPv6 bootstrap_address", "bmc_address", "10.10.10.1", "bmc_address and bootstrap_address must be the same IP version"),
    ("install_type out of range", "install_type", "99", "install_type invalid: 99"),
]

PARTIAL_ADMIN_NETWORK_SCENARIOS = [
    (
        "admin_subnet present but admin_start_address missing",
        "admin_subnet: fdff:abcd::0/64\nadmin_end_address: fdff:abcd::10\nadmin_gateway_address: fdff:abcd::1",
        "admin_start_address required",
    ),
    (
        "admin_subnet present but admin_end_address missing",
        "admin_subnet: fdff:abcd::0/64\nadmin_start_address: fdff:abcd::2\nadmin_gateway_address: fdff:abcd::1",
        "admin_end_address required",
    ),
    (
        "admin_subnet present but admin_gateway_address missing",
        "admin_subnet: fdff:abcd::0/64\nadmin_start_address: fdff:abcd::2\nadmin_end_address: fdff:abcd::10",
        "admin_gateway_address required",
    ),
    (
        "admin_floating_address does not match admin_start_address",
        "admin_subnet: fdff:abcd::0/64\nadmin_start_address: fdff:abcd::2\nadmin_end_address: fdff:abcd::10\nadmin_gateway_address: fdff:abcd::1\nadmin_floating_address: fdff:abcd::99",
        "admin_floating_address does not match admin_start_address",
    ),
    (
        "both admin_gateway and management_gateway specified",
        "admin_subnet: fdff:abcd::0/64\nadmin_start_address: fdff:abcd::2\nadmin_end_address: fdff:abcd::10\nadmin_gateway_address: fdff:abcd::1",
        "admin_gateway_address and management_gateway_address cannot be specified at the same time",
    ),
]

GENERIC_DCMANAGER_ERROR = "the server could not comply with the request since it is either malformed or otherwise incorrect."


def _create_temp_files_with_missing_keys(system_controller_ssh: SSHConnection, source_file: str, temp_dir: str, scenarios: list) -> dict:
    """Copy a YAML file to temp dir and remove one required key per copy.

    All operations happen on the SC via SSH. Original files are never modified.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the system controller.
        source_file (str): Remote path to the original YAML file.
        temp_dir (str): Remote path to the temp directory on the SC.
        scenarios (list): List of (field_name, expected_error) tuples.

    Returns:
        dict: dict mapping field_name to the remote path of the modified file.
    """
    base_name = os.path.basename(source_file)
    FileKeywords(system_controller_ssh).create_directory(temp_dir)

    file_map = {}
    for field, _ in scenarios:
        modified_file = f"{temp_dir}/no_{field}_{base_name}"
        FileKeywords(system_controller_ssh).copy_file(source_file, modified_file)
        FileKeywords(system_controller_ssh).remove_line_matching(modified_file, f"^{field}:")
        file_map[field] = modified_file

    return file_map


def _delete_subcloud_if_created(system_controller_ssh: SSHConnection, subcloud_name: str) -> None:
    """Delete a subcloud if it was unexpectedly created during a negative test.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud to delete.
    """
    DcManagerSubcloudDeleteKeywords(system_controller_ssh).dcmanager_subcloud_delete(subcloud_name)


def _validate_scenarios(system_controller_ssh: SSHConnection, subcloud_name: str, scenarios: list, file_map: dict, install_values: str, bootstrap_values: str = None, deploy_config_file: str = "", use_file_as_bootstrap: bool = True) -> list:
    """Run enroll command for each scenario and collect failures.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Subcloud name.
        scenarios (list): List of (field_name, expected_error) tuples.
        file_map (dict): Dict mapping field_name to modified file path.
        install_values (str): Remote path to install-values file (used when testing bootstrap scenarios).
        bootstrap_values (str): Remote path to bootstrap-values file (used when testing install scenarios).
        deploy_config_file (str): Remote path to deploy-config file.
        use_file_as_bootstrap (bool): If True, file_map entries are bootstrap files.
            If False, file_map entries are install-values files.

    Returns:
        list: list of failure description strings. Empty if all passed.
    """
    failures = []

    for field, expected_error in scenarios:
        get_logger().log_info(f"Testing missing field: {field}")
        modified_file = file_map[field]

        if use_file_as_bootstrap:
            output, rc = DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll_with_error(subcloud_name, modified_file, install_values, deploy_config_file)
        else:
            output, rc = DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll_with_error(subcloud_name, bootstrap_values, modified_file, deploy_config_file)

        if rc == 0:
            get_logger().log_info(f"UNEXPECTED: enrollment accepted with missing '{field}'. Deleting subcloud.")
            _delete_subcloud_if_created(system_controller_ssh, subcloud_name)
            failures.append(f"  {field}: command was accepted (rc=0) when it should have been rejected")
            continue

        generic_error = GENERIC_DCMANAGER_ERROR
        has_generic_error = generic_error in output.lower()
        has_specific_error = expected_error.lower() in output.lower()

        if not has_generic_error:
            failures.append(f"  {field}: missing generic error message in output: {output.strip()}")
        elif not has_specific_error:
            failures.append(f"  {field}: expected detail containing '{expected_error}' but got: {output.strip()}")
        else:
            get_logger().log_info(f"PASS: {field} - correctly rejected with expected error")

    return failures


def _create_temp_files_with_replaced_values(system_controller_ssh: SSHConnection, source_file: str, temp_dir: str, scenarios: list) -> dict:
    """Copy a YAML file to temp dir and replace field values per scenario.

    All operations happen on the SC via SSH. Original files are never modified.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the system controller.
        source_file (str): Remote path to the original YAML file.
        temp_dir (str): Remote path to the temp directory on the SC.
        scenarios (list): List of (description, field, new_value, expected_error) tuples.

    Returns:
        dict: dict mapping description to the remote path of the modified file.
    """
    base_name = os.path.basename(source_file)
    FileKeywords(system_controller_ssh).create_directory(temp_dir)

    file_map = {}
    for description, field, new_value, _ in scenarios:
        safe_desc = description.replace(" ", "_").replace("/", "_")
        modified_file = f"{temp_dir}/{safe_desc}_{base_name}"
        FileKeywords(system_controller_ssh).copy_file(source_file, modified_file)
        FileKeywords(system_controller_ssh).replace_line_matching(modified_file, f"^{field}:.*", f"{field}: {new_value}")
        file_map[description] = modified_file

    return file_map


@mark.p2
@mark.lab_has_subcloud
def test_enroll_rejects_missing_required_bootstrap_values(request: FixtureRequest):
    """Verify dcmanager rejects enrollment when bootstrap-values is missing required fields.

    Iterates through all required bootstrap-values fields, removes each one
    individually, and validates that dcmanager rejects the enrollment with an
    appropriate error message.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.
        - Subcloud is NOT currently registered in dcmanager.

    Test Steps:
        1. Create a temp directory under the subcloud config folder on the SC.
        2. For each required field, create a copy of bootstrap-values with
           that field removed.
        3. Run dcmanager subcloud add --enroll with each modified file.
        4. Validate each command is rejected with an appropriate error.

    Expected Results:
        - All commands return non-zero exit code.
        - Each error output contains the generic dcmanager error message.
        - Each error output contains a detail message identifying the missing field.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
    deploy_config_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()

    subcloud_dir = os.path.dirname(bootstrap_values)
    temp_dir = f"{subcloud_dir}/temp"

    def teardown():
        get_logger().log_teardown_step(f"Remove temp directory {temp_dir}")
        FileKeywords(system_controller_ssh).delete_directory(temp_dir)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Creating modified bootstrap-values files with missing fields")
    file_map = _create_temp_files_with_missing_keys(system_controller_ssh, bootstrap_values, temp_dir, MISSING_BOOTSTRAP_FIELD_SCENARIOS)

    get_logger().log_test_case_step("Running enrollment with each modified file")
    failures = _validate_scenarios(
        system_controller_ssh,
        subcloud_name,
        MISSING_BOOTSTRAP_FIELD_SCENARIOS,
        file_map,
        install_values,
        deploy_config_file=deploy_config_file,
        use_file_as_bootstrap=True,
    )

    validate_equals(len(failures), 0, f"All scenarios should pass. Failed {len(failures)} scenario(s):\n" + "\n".join(failures))


@mark.p2
@mark.lab_has_subcloud
def test_enroll_rejects_missing_required_install_values(request: FixtureRequest):
    """Verify dcmanager rejects enrollment when install-values is missing required fields.

    Iterates through all required install-values fields, removes each one
    individually, and validates that dcmanager rejects the enrollment with an
    appropriate error message.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.
        - Subcloud is NOT currently registered in dcmanager.

    Test Steps:
        1. Create a temp directory under the subcloud config folder on the SC.
        2. For each required field, create a copy of install-values with
           that field removed.
        3. Run dcmanager subcloud add --enroll with the original bootstrap-values
           and each modified install-values file.
        4. Validate each command is rejected with an appropriate error.

    Expected Results:
        - All commands return non-zero exit code.
        - Each error output contains the generic dcmanager error message.
        - Each error output contains a detail message identifying the missing field.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
    deploy_config_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()

    subcloud_dir = os.path.dirname(install_values)
    temp_dir = f"{subcloud_dir}/temp"

    def teardown():
        get_logger().log_teardown_step(f"Remove temp directory {temp_dir}")
        FileKeywords(system_controller_ssh).delete_directory(temp_dir)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Creating modified install-values files with missing fields")
    file_map = _create_temp_files_with_missing_keys(system_controller_ssh, install_values, temp_dir, MISSING_INSTALL_VALUES_FIELD_SCENARIOS)

    get_logger().log_test_case_step("Running enrollment with each modified file")
    failures = _validate_scenarios(
        system_controller_ssh,
        subcloud_name,
        MISSING_INSTALL_VALUES_FIELD_SCENARIOS,
        file_map,
        install_values,
        bootstrap_values=bootstrap_values,
        deploy_config_file=deploy_config_file,
        use_file_as_bootstrap=False,
    )

    validate_equals(len(failures), 0, f"All scenarios should pass. Failed {len(failures)} scenario(s):\n" + "\n".join(failures))


@mark.p2
@mark.lab_has_subcloud
def test_enroll_rejects_invalid_install_values_formats(request: FixtureRequest):
    """Verify dcmanager rejects enrollment when install-values has invalid field formats.

    Iterates through scenarios with invalid IP addresses, IP version mismatches,
    and out-of-range values in install-values, validating that dcmanager rejects
    each with an appropriate error message.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.
        - Subcloud is NOT currently registered in dcmanager.

    Test Steps:
        1. Create a temp directory under the subcloud config folder on the SC.
        2. For each scenario, create a copy of install-values with the target
           field replaced with an invalid value.
        3. Run dcmanager subcloud add --enroll with the original bootstrap-values
           and each modified install-values file.
        4. Validate each command is rejected with an appropriate error.

    Expected Results:
        - All commands return non-zero exit code.
        - Each error output contains the generic dcmanager error message.
        - Each error output contains the specific error detail for the invalid value.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
    deploy_config_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()

    subcloud_dir = os.path.dirname(install_values)
    temp_dir = f"{subcloud_dir}/temp"

    def teardown():
        get_logger().log_teardown_step(f"Remove temp directory {temp_dir}")
        FileKeywords(system_controller_ssh).delete_directory(temp_dir)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Creating modified install-values files with invalid formats")
    file_map = _create_temp_files_with_replaced_values(system_controller_ssh, install_values, temp_dir, INVALID_INSTALL_VALUES_FORMAT_SCENARIOS)

    failures = []

    for description, _, _, expected_error in INVALID_INSTALL_VALUES_FORMAT_SCENARIOS:
        get_logger().log_info(f"Testing: {description}")
        modified_file = file_map[description]

        output, rc = DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll_with_error(subcloud_name, bootstrap_values, modified_file, deploy_config_file)

        if rc == 0:
            get_logger().log_info(f"UNEXPECTED: enrollment accepted for '{description}'. Deleting subcloud.")
            _delete_subcloud_if_created(system_controller_ssh, subcloud_name)
            failures.append(f"  {description}: command was accepted (rc=0) when it should have been rejected")
            continue

        has_generic_error = GENERIC_DCMANAGER_ERROR in output.lower()
        has_specific_error = expected_error.lower() in output.lower()

        if not has_generic_error:
            failures.append(f"  {description}: missing generic error message in output: {output.strip()}")
        elif not has_specific_error:
            failures.append(f"  {description}: expected detail containing '{expected_error}' but got: {output.strip()}")
        else:
            get_logger().log_info(f"PASS: {description} - correctly rejected with expected error")

    validate_equals(len(failures), 0, f"All scenarios should pass. Failed {len(failures)} scenario(s):\n" + "\n".join(failures))


@mark.p2
@mark.lab_has_subcloud
def test_enroll_rejects_partial_admin_network_config(request: FixtureRequest):
    """Verify dcmanager rejects enrollment when bootstrap-values has incomplete admin network.

    Tests scenarios where some admin network fields are present but others are
    missing, and where admin_floating_address does not match admin_start_address.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.
        - Subcloud is NOT currently registered in dcmanager.

    Test Steps:
        1. Create a temp directory under the subcloud config folder on the SC.
        2. For each scenario, create a copy of bootstrap-values and append
           a partial admin network configuration.
        3. Run dcmanager subcloud add --enroll with each modified file.
        4. Validate each command is rejected with an appropriate error.

    Expected Results:
        - All commands return non-zero exit code.
        - Each error output contains the generic dcmanager error message.
        - Each error output contains the specific error about the missing or
          conflicting admin network field.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
    deploy_config_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()

    subcloud_dir = os.path.dirname(bootstrap_values)
    temp_dir = f"{subcloud_dir}/temp"
    base_name = os.path.basename(bootstrap_values)

    def teardown():
        get_logger().log_teardown_step(f"Remove temp directory {temp_dir}")
        FileKeywords(system_controller_ssh).delete_directory(temp_dir)

    request.addfinalizer(teardown)

    FileKeywords(system_controller_ssh).create_directory(temp_dir)

    file_map = {}
    for description, admin_lines, _ in PARTIAL_ADMIN_NETWORK_SCENARIOS:
        safe_desc = description.replace(" ", "_").replace("/", "_")
        modified_file = f"{temp_dir}/{safe_desc}_{base_name}"
        FileKeywords(system_controller_ssh).copy_file(bootstrap_values, modified_file)

        if "both admin_gateway and management_gateway" in description:
            file_kw = FileKeywords(system_controller_ssh)
            file_kw.append_to_file(modified_file, admin_lines)
        else:
            file_kw = FileKeywords(system_controller_ssh)
            file_kw.remove_line_matching(modified_file, "^management_gateway_address:")
            file_kw.append_to_file(modified_file, admin_lines)
        file_map[description] = modified_file

    get_logger().log_test_case_step("Running enrollment with partial admin network configurations")
    failures = []

    for description, _, expected_error in PARTIAL_ADMIN_NETWORK_SCENARIOS:
        get_logger().log_info(f"Testing: {description}")
        modified_file = file_map[description]

        output, rc = DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll_with_error(subcloud_name, modified_file, install_values, deploy_config_file)

        if rc == 0:
            get_logger().log_info(f"UNEXPECTED: enrollment accepted for '{description}'. Deleting subcloud.")
            _delete_subcloud_if_created(system_controller_ssh, subcloud_name)
            failures.append(f"  {description}: command was accepted (rc=0) when it should have been rejected")
            continue

        has_generic_error = GENERIC_DCMANAGER_ERROR in output.lower()
        has_specific_error = expected_error.lower() in output.lower()

        if not has_generic_error:
            failures.append(f"  {description}: missing generic error message in output: {output.strip()}")
        elif not has_specific_error:
            failures.append(f"  {description}: expected detail containing '{expected_error}' but got: {output.strip()}")
        else:
            get_logger().log_info(f"PASS: {description} - correctly rejected with expected error")

    validate_equals(len(failures), 0, f"All scenarios should pass. Failed {len(failures)} scenario(s):\n" + "\n".join(failures))


@mark.p2
@mark.lab_has_subcloud
def test_enroll_rejects_software_version_mismatch(request: FixtureRequest):
    """Verify dcmanager rejects enrollment when software_version in install-values mismatches.

    Tests the scenario where the software_version field in install-values
    does not match the active software version on the system controller.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.
        - Subcloud is NOT currently registered in dcmanager.

    Test Steps:
        1. Create a temp directory under the subcloud config folder on the SC.
        2. Create a copy of install-values with software_version set to a
           non-existent version (99.99).
        3. Run dcmanager subcloud add --enroll with the modified install-values.
        4. Validate command is rejected with error about version mismatch.

    Expected Results:
        - Command returns non-zero exit code.
        - Error output contains the generic dcmanager error message.
        - Error output contains detail about software_version mismatch with
          guidance to correct or remove the parameter.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
    deploy_config_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()

    subcloud_dir = os.path.dirname(install_values)
    temp_dir = f"{subcloud_dir}/temp"
    base_name = os.path.basename(install_values)
    modified_install = f"{temp_dir}/bad_sw_version_{base_name}"

    def teardown():
        get_logger().log_teardown_step(f"Remove temp directory {temp_dir}")
        FileKeywords(system_controller_ssh).delete_directory(temp_dir)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Creating install-values with mismatched software_version")
    file_keywords = FileKeywords(system_controller_ssh)
    file_keywords.create_directory(temp_dir)
    file_keywords.copy_file(install_values, modified_install)
    FileKeywords(system_controller_ssh).replace_line_matching(modified_install, "^software_version:.*", "software_version: 99.99")

    get_logger().log_test_case_step("Running enrollment with mismatched software_version")
    output, rc = DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll_with_error(subcloud_name, bootstrap_values, modified_install, deploy_config_file)

    get_logger().log_info(f"Return code: {rc}")
    get_logger().log_info(f"Output: {output}")

    if rc == 0:
        _delete_subcloud_if_created(system_controller_ssh, subcloud_name)

    expected_error = "The software_version value 99.99 in the install values yaml file " "does not match with the specified/current software version of"

    validate_not_equals(rc, 0, f"Command should be rejected (non-zero rc). Got rc={rc}. Output: {output}")
    validate_str_contains(output.lower(), GENERIC_DCMANAGER_ERROR, "Generic dcmanager error message present in output")
    validate_str_contains(output.lower(), expected_error.lower(), "Specific error detail present in output")
