"""Regression tests for the kubernetes-power-manager application."""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords

# Alarm raised when a configuration change requires the kubernetes-power-manager app to be reapplied.
POWER_MANAGER_REAPPLY_ALARM_ID = "750.006"

# Alarm ID to exclude from the unlock health check so the unlock itself completes; the persistence of
# this alarm is validated explicitly afterwards.
CONFIG_OUT_OF_DATE_ALARM_ID = "250.001"


def upload_and_apply_app(app_name: str, ssh_connection: SSHConnection) -> None:
    """Upload and apply a platform application, validating each state transition.

    Args:
        app_name (str): Name of the platform application.
        ssh_connection (SSHConnection): Active controller SSH connection.
    """
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)

    get_logger().log_info(f"Uploading {app_name}")
    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name(app_name)
    upload_input.set_tar_file_path(f"{base_path}{app_name}*.tgz")
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)
    app_list_keywords.validate_app_status(app_name, SystemApplicationStatusEnum.UPLOADED.value)

    get_logger().log_info(f"Applying {app_name}")
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    app_list_keywords.validate_app_status(app_name, SystemApplicationStatusEnum.APPLIED.value)


def cleanup_power_manager_environment(nfd_name: str, power_manager_name: str, ssh_connection: SSHConnection) -> None:
    """Remove and delete kubernetes-power-manager and its node-feature-discovery dependency.

    Both applications are removed only if present; kubernetes-power-manager is
    removed before its node-feature-discovery dependency.

    Args:
        nfd_name (str): node-feature-discovery application name (dependency).
        power_manager_name (str): kubernetes-power-manager application name.
        ssh_connection (SSHConnection): Active controller SSH connection.
    """
    remove_keywords = SystemApplicationRemoveKeywords(ssh_connection)
    remove_keywords.cleanup_app_if_present(power_manager_name, force_removal=True, force_deletion=True, timeout_in_seconds=600)
    remove_keywords.cleanup_app_if_present(nfd_name, force_removal=True, force_deletion=True, timeout_in_seconds=600)


@mark.p1
@mark.lab_is_simplex
def test_power_manager_reapply_after_lock_unlock_simplex(request: FixtureRequest) -> None:
    """Verify kubernetes-power-manager auto-reapplies and alarm 750.006 clears after lock/unlock.

    On a simplex system, a lock/unlock cycle triggers a config change that requires
    kubernetes-power-manager to be reapplied. sysinv should reapply it automatically
    so alarm 750.006 clears on its own and the app returns to the 'applied' state.

    Test Steps:
        - Get SSH connection to the active controller
        - Cleanup the kubernetes-power-manager environment
        - Setup the environment: upload and apply node-feature-discovery (dependency)
          then kubernetes-power-manager
        - Lock the active controller
        - Unlock the active controller
        - Verify alarm 750.006 clears automatically after unlock
        - Verify kubernetes-power-manager is in the 'applied' state

    Args:
        request (FixtureRequest): pytest fixture for registering teardown.
    """
    app_config = ConfigurationManager.get_app_config()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    power_manager_name = app_config.get_power_manager_app_name()

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleanup kubernetes-power-manager environment")
    cleanup_power_manager_environment(nfd_name, power_manager_name, ssh_connection)

    def cleanup() -> None:
        get_logger().log_teardown_step("Removing and deleting kubernetes-power-manager environment")
        cleanup_power_manager_environment(nfd_name, power_manager_name, ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step(f"Upload and apply dependency {nfd_name}")
    upload_and_apply_app(nfd_name, ssh_connection)

    get_logger().log_test_case_step(f"Upload and apply {power_manager_name}")
    upload_and_apply_app(power_manager_name, ssh_connection)

    get_logger().log_test_case_step("Getting active controller hostname")
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    system_host_lock = SystemHostLockKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Locking controller {active_controller}")
    lock_success = system_host_lock.lock_host(active_controller)
    validate_equals(lock_success, True, "Controller should lock successfully")

    get_logger().log_test_case_step(f"Unlocking controller {active_controller}")
    # Exclude 750.006 from the unlock health check so the unlock completes; this alarm used to
    # persist. Its automatic clearing is asserted explicitly below.
    unlock_success = system_host_lock.unlock_host(
        active_controller,
        unlock_accepted_timeout=3000,
        exclude_alarm_ids=[POWER_MANAGER_REAPPLY_ALARM_ID, CONFIG_OUT_OF_DATE_ALARM_ID],
    )
    validate_equals(unlock_success, True, "Controller should unlock successfully")

    get_logger().log_test_case_step(f"Verifying alarm {POWER_MANAGER_REAPPLY_ALARM_ID} clears automatically after unlock")
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    validate_equals_with_retry(
        function_to_execute=lambda: alarm_list_keywords.is_alarm_present(POWER_MANAGER_REAPPLY_ALARM_ID),
        expected_value=False,
        validation_description=f"Alarm {POWER_MANAGER_REAPPLY_ALARM_ID} (kubernetes-power-manager reapply required) should clear automatically",
        timeout=900,
        polling_sleep_time=30,
    )

    get_logger().log_test_case_step(f"Verifying {power_manager_name} is in applied state after auto-reapply")
    SystemApplicationListKeywords(ssh_connection).validate_app_status(power_manager_name, SystemApplicationStatusEnum.APPLIED.value, timeout=600, polling_sleep_time=30)
