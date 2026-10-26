from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.linux.log.log_grep_keywords import LogGrepKeywords

APP_CHART_BASE_PATH = "/usr/local/share/applications/helm/"
SYSINV_LOG_PATH = "/var/log/sysinv.log"
RPC_TIMEOUT_ERROR_PATTERN = r"Timeout while waiting on RPC response.*perform_app_delete"
APPS = ["snmp", "metrics-server", "portieris", "istio", "security-profiles-operator"]

# Timeout constants for application lifecycle operations
APP_OPERATION_TIMEOUT_SECONDS = 600
POLLING_SLEEP_TIME_SECONDS = 5


def check_for_app_delete_timeout_errors(ssh_connection: SSHConnection) -> str:
    """Check sysinv.log for RPC timeout errors during app delete operations.

    Searches for timeout errors related to perform_app_delete RPC calls.

    Args:
        ssh_connection (SSHConnection): SSH connection to the target host.

    Returns:
        str: Error messages found, or empty string if no errors.
    """
    log_grep_keywords = LogGrepKeywords(ssh_connection)
    errors = log_grep_keywords.grep_log_for_errors(SYSINV_LOG_PATH, RPC_TIMEOUT_ERROR_PATTERN, secondary_pattern=None, tail=10)

    if errors:
        get_logger().log_error(f"Found RPC timeout errors in sysinv.log:\n{errors}")

    return errors


def cleanup_test_applications(ssh_connection: SSHConnection, apps_to_test: list[str]) -> None:
    """Remove and delete all test applications.

    Args:
        ssh_connection (SSHConnection): SSH connection to the target host.
        apps_to_test (list[str]): List of application names.
    """
    remove_kw = SystemApplicationRemoveKeywords(ssh_connection)

    for app_name in apps_to_test:
        remove_kw.cleanup_app_if_present(app_name, force_removal=True, force_deletion=True, timeout_in_seconds=APP_OPERATION_TIMEOUT_SECONDS)
        get_logger().log_info(f"{app_name} cleaned up")


@mark.p2
def test_application_delete_timeout_with_multiple_apps(request: FixtureRequest):
    """Verify system application-delete does not time out with multiple apps.

    Test Steps:
        - Upload available applications
        - Verify all applications are uploaded
        - Apply all applications
        - Verify all applications are applied
        - Remove all applications
        - Delete all applications one by one
        - Verify all applications are deleted
        - Verify no RPC timeout errors in sysinv.log during deletions
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    upload_kw = SystemApplicationUploadKeywords(ssh_connection)
    apply_kw = SystemApplicationApplyKeywords(ssh_connection)
    app_list_kw = SystemApplicationListKeywords(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Cleaning up all test applications")
        cleanup_test_applications(ssh_connection, APPS)

    request.addfinalizer(cleanup)

    # Cleanup any previous instances
    get_logger().log_setup_step("Ensure test applications are not already present")
    cleanup_test_applications(ssh_connection, APPS)

    # Upload all applications
    get_logger().log_test_case_step("Uploading test applications")
    for app_name in APPS:
        get_logger().log_info(f"Uploading {app_name}")
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(app_name)
        upload_input.set_tar_file_path(f"{APP_CHART_BASE_PATH}{app_name}*.tgz")
        upload_kw.system_application_upload(upload_input, timeout=APP_OPERATION_TIMEOUT_SECONDS, polling_sleep_time=POLLING_SLEEP_TIME_SECONDS)

    # Verify all uploaded
    get_logger().log_test_case_step("Verifying all applications are uploaded")
    for app_name in APPS:
        app_list_kw.validate_app_status(app_name, "uploaded", timeout=APP_OPERATION_TIMEOUT_SECONDS, polling_sleep_time=POLLING_SLEEP_TIME_SECONDS)
        get_logger().log_info(f"{app_name} is uploaded")

    # Apply all applications
    get_logger().log_test_case_step("Applying test applications")
    for app_name in APPS:
        get_logger().log_info(f"Applying {app_name}")
        apply_kw.system_application_apply(app_name, timeout=APP_OPERATION_TIMEOUT_SECONDS, polling_sleep_time=POLLING_SLEEP_TIME_SECONDS)

    # Verify all applied
    get_logger().log_test_case_step("Verifying all applications are applied")
    for app_name in APPS:
        app_list_kw.validate_app_status(app_name, "applied", timeout=APP_OPERATION_TIMEOUT_SECONDS, polling_sleep_time=POLLING_SLEEP_TIME_SECONDS)
        get_logger().log_info(f"{app_name} is applied")

    # Remove all applications
    get_logger().log_test_case_step("Removing all test applications")
    remove_kw = SystemApplicationRemoveKeywords(ssh_connection)
    for app_name in APPS:
        get_logger().log_info(f"Removing {app_name}")
        remove_input = SystemApplicationRemoveInput()
        remove_input.set_app_name(app_name)
        remove_input.set_timeout_in_seconds(APP_OPERATION_TIMEOUT_SECONDS)
        remove_kw.system_application_remove(remove_input)

    # Delete all applications
    get_logger().log_test_case_step("Deleting all test applications")
    delete_kw = SystemApplicationDeleteKeywords(ssh_connection)
    for app_name in APPS:
        get_logger().log_info(f"Deleting {app_name}")
        delete_input = SystemApplicationDeleteInput()
        delete_input.set_app_name(app_name)
        delete_kw.get_system_application_delete(delete_input)

    # Verify all deleted
    get_logger().log_test_case_step("Verifying all applications are deleted")
    system_applications = app_list_kw.get_system_application_list()
    for app_name in APPS:
        app_present = system_applications.is_in_application_list(app_name)
        validate_not_equals(app_present, True, f"{app_name} should not be in application list after deletion")
        get_logger().log_info(f"{app_name} is deleted")

    # Check sysinv.log for RPC timeout errors
    get_logger().log_test_case_step("Verifying no RPC timeout errors occurred during app deletion")
    errors = check_for_app_delete_timeout_errors(ssh_connection)
    validate_equals(errors, "", "RPC timeout errors should not occur during app deletion")

    get_logger().log_info("All applications deleted successfully without timeout errors")
