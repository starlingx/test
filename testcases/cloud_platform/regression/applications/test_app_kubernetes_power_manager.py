"""Regression tests for the kubernetes-power-manager application."""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_not_equals
from keywords.cloud_platform.applications.power_manager.power_manager_keywords import PowerManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords

# Alarm raised when a configuration change requires the kubernetes-power-manager app to be reapplied.
POWER_MANAGER_REAPPLY_ALARM_ID = PowerManagerKeywords.REAPPLY_ALARM_ID

# Alarm ID to exclude from the unlock health check so the unlock itself completes; the persistence of
# this alarm is validated explicitly afterwards.
CONFIG_OUT_OF_DATE_ALARM_ID = "250.001"

# Label required on the hosts for the kubernetes-power-manager application
POWER_MANAGEMENT_LABEL = PowerManagerKeywords.MANAGEMENT_LABEL


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


@mark.p1
@mark.lab_has_cstate_support
def test_install_uninstall_power_manager(request: FixtureRequest) -> None:
    """Install and uninstall kubernetes-power-manager with its node-feature-discovery dependency.

    The power-management=enabled label is assigned to and removed from the controller and
    worker hosts, and the CStates custom resources are verified to follow the label.

    Test Steps:
        - Cleanup the kubernetes-power-manager environment
        - Step 1: Upload and apply node-feature-discovery (dependency)
        - Step 2: Upload and apply kubernetes-power-manager
        - Step 3: Verify the kubernetes-power-manager pods are running
        - Step 4: Verify no CStates custom resource exists for any controller or worker host before the power-management=enabled label is assigned
        - Step 5: Assign the power-management=enabled label to all controller and worker hosts
        - Step 6: Verify kubernetes-power-manager auto-reapplies: alarm 750.006 is raised, then clears, and the app returns to 'applied'
        - Step 7: Verify the kubernetes-power-manager pods are running after auto-reapply
        - Step 8: Verify a CStates custom resource is created for each controller and worker host
        - Step 9: Remove the power-management label from all hosts
        - Step 10: Verify kubernetes-power-manager auto-reapplies after label removal: alarm 750.006 is raised, then clears, and the app returns to 'applied'
        - Step 11: Verify the CStates custom resource is removed for each controller and worker host
        - Step 12: Remove and delete kubernetes-power-manager
        - Step 13: Verify no pods remain in the intel-power namespace after deletion
        - Step 14: Remove and delete node-feature-discovery

    Args:
        request (FixtureRequest): pytest fixture for registering teardown.
    """
    # Setup app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    power_manager_name = app_config.get_power_manager_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    power_manager_keywords = PowerManagerKeywords(ssh_connection)

    # Host names do not change during the test, so query 'system host-list' once and reuse the result.
    host_names = [host.get_host_name() for host in SystemHostListKeywords(ssh_connection).get_system_host_list().get_controllers_and_computes()]

    # Cleanup: ensure that NFD and Power Manager application is not present before starting
    get_logger().log_test_case_step("Cleanup kubernetes-power-manager environment")
    power_manager_keywords.cleanup_environment(nfd_name, power_manager_name)

    def cleanup() -> None:
        get_logger().log_teardown_step("Removing and deleting kubernetes-power-manager environment")
        power_manager_keywords.cleanup_environment(nfd_name, power_manager_name)

    request.addfinalizer(cleanup)

    # Step 1: Upload and apply Node Feature Discovery (dependency) first
    get_logger().log_test_case_step(f"Upload and apply dependency {nfd_name}")

    # Setup the upload input object for NFD
    nfd_upload_input = SystemApplicationUploadInput()
    nfd_upload_input.set_app_name(nfd_name)
    nfd_upload_input.set_tar_file_path(f"{base_path}{nfd_name}*.tgz")

    # Upload the NFD app file and verify it
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(nfd_upload_input)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    nfd_app_status = system_applications.get_application(nfd_name).get_status()
    validate_equals(nfd_app_status, SystemApplicationStatusEnum.UPLOADED.value, f"{nfd_name} upload status validation")

    # Apply the NFD app to the active controller and verify it was applied
    nfd_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(nfd_name)
    nfd_app_object = nfd_apply_output.get_system_application_object()
    validate_not_equals(nfd_app_object, None, "NFD application object should not be None")
    validate_equals(nfd_app_object.get_name(), nfd_name, "NFD application name validation")
    validate_equals(nfd_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "NFD application status validation")

    # Step 2: Upload and apply Power Manager
    get_logger().log_test_case_step(f"Upload and apply {power_manager_name}")

    # Setup the upload input object for Power Manager
    power_manager_upload_input = SystemApplicationUploadInput()
    power_manager_upload_input.set_app_name(power_manager_name)
    power_manager_upload_input.set_tar_file_path(f"{base_path}{power_manager_name}*.tgz")

    # Upload the Power Manager app file and verify it
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(power_manager_upload_input)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    power_manager_app_status = system_applications.get_application(power_manager_name).get_status()
    validate_equals(power_manager_app_status, SystemApplicationStatusEnum.UPLOADED.value, f"{power_manager_name} upload status validation")

    # Apply the Power Manager app to the active controller
    power_manager_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(power_manager_name)

    # Verify the Power Manager app was applied
    power_manager_app_object = power_manager_apply_output.get_system_application_object()
    validate_not_equals(power_manager_app_object, None, "Power Manager application object should not be None")
    validate_equals(power_manager_app_object.get_name(), power_manager_name, "Power Manager application name validation")
    validate_equals(power_manager_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Power Manager application status validation")

    # Step 3: Verify the Power Manager pods are up and running
    get_logger().log_test_case_step(f"Verifying {power_manager_name} pods are running")
    power_manager_keywords.wait_for_pods_running()
    validate_equals(power_manager_keywords.is_namespace_empty(), False, f"Resources should be present in namespace {PowerManagerKeywords.NAMESPACE} while Power Manager is applied")

    # Step 4: Verify no CStates custom resources exist before the power-management label is assigned
    get_logger().log_test_case_step(f"Verifying no {PowerManagerKeywords.CSTATES_KIND} custom resources exist before the {POWER_MANAGEMENT_LABEL} label is assigned")
    for host_name in host_names:
        cstate_present = power_manager_keywords.is_cstate_present(host_name)
        validate_equals(cstate_present, False, f"No {PowerManagerKeywords.CSTATES_KIND} custom resource should exist for host {host_name} before the {POWER_MANAGEMENT_LABEL} label is assigned")

    # Step 5: Assign the power-management=enabled label to all nodes
    get_logger().log_test_case_step(f"Assigning {POWER_MANAGEMENT_LABEL} label to hosts: {host_names}")
    power_manager_keywords.assign_management_label_to_hosts(host_names)

    # Step 6: Verify power manager auto-reapplies after labels are assigned
    get_logger().log_test_case_step(f"Verifying {power_manager_name} auto-reapplies after labels are assigned")
    power_manager_keywords.wait_for_auto_reapply(power_manager_name)

    # Step 7: Verify the Power Manager pods are up and running after auto-reapply
    get_logger().log_test_case_step(f"Verifying {power_manager_name} pods are running after auto-reapply")
    power_manager_keywords.wait_for_pods_running()
    validate_equals(power_manager_keywords.is_namespace_empty(), False, f"Resources should be present in namespace {PowerManagerKeywords.NAMESPACE} while Power Manager is applied")

    # Step 8: Verify a CStates custom resource is created for each host after the power-management label is assigned
    get_logger().log_test_case_step(f"Verifying a {PowerManagerKeywords.CSTATES_KIND} custom resource exists for each host after the {POWER_MANAGEMENT_LABEL} label is assigned")
    for host_name in host_names:
        validate_equals_with_retry(
            function_to_execute=lambda host_name=host_name: power_manager_keywords.is_cstate_present(host_name),
            expected_value=True,
            validation_description=f"A {PowerManagerKeywords.CSTATES_KIND} custom resource should exist for host {host_name} after the {POWER_MANAGEMENT_LABEL} label is assigned",
            timeout=300,
            polling_sleep_time=15,
        )

    # Step 9: Remove the power-management=enabled label from all nodes
    get_logger().log_test_case_step(f"Removing {PowerManagerKeywords.MANAGEMENT_LABEL_KEY} label from all hosts")
    power_manager_keywords.remove_management_label_from_all_hosts()

    # Step 10: Verify power manager auto-reapplies after labels are removed
    get_logger().log_test_case_step(f"Verifying {power_manager_name} auto-reapplies after labels are removed")
    power_manager_keywords.wait_for_auto_reapply(power_manager_name)

    # Step 11: Verify the CStates custom resources are removed for each host after the power-management label is removed
    get_logger().log_test_case_step(f"Verifying no {PowerManagerKeywords.CSTATES_KIND} custom resources exist for any host after the {POWER_MANAGEMENT_LABEL} label is removed")
    for host_name in host_names:
        validate_equals_with_retry(
            function_to_execute=lambda host_name=host_name: power_manager_keywords.is_cstate_present(host_name),
            expected_value=False,
            validation_description=f"No {PowerManagerKeywords.CSTATES_KIND} custom resource should exist for host {host_name} after the {POWER_MANAGEMENT_LABEL} label is removed",
            timeout=300,
            polling_sleep_time=15,
        )

    # Step 12: Remove and delete the Power Manager application
    get_logger().log_test_case_step(f"Removing and deleting {power_manager_name}")

    # Remove the Power Manager application
    power_manager_remove_input = SystemApplicationRemoveInput()
    power_manager_remove_input.set_app_name(power_manager_name)
    power_manager_remove_input.set_force_removal(False)
    power_manager_remove_input.set_timeout_in_seconds(90)

    # system_application_remove already waits for the 'uploaded' status and raises on timeout.
    SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(power_manager_remove_input)

    # Delete the Power Manager application
    power_manager_delete_input = SystemApplicationDeleteInput()
    power_manager_delete_input.set_app_name(power_manager_name)
    power_manager_delete_input.set_force_deletion(False)
    power_manager_delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(power_manager_delete_input)
    validate_equals(power_manager_delete_msg, f"Application {power_manager_name} deleted.\n", "Power Manager deletion message validation")

    # Step 13: Verify no pods remain in the power manager namespace after deletion.
    # CStates removal is already verified in Step 11, while the CStates CRD still exists; the delete removes the CRD itself.
    get_logger().log_test_case_step(f"Verifying no pods remain in namespace {PowerManagerKeywords.NAMESPACE} after {power_manager_name} deletion")
    power_manager_keywords.wait_for_pods_deleted()

    # Step 14: Remove and delete the Node Feature Discovery application
    get_logger().log_test_case_step(f"Removing and deleting {nfd_name}")

    # Remove the NFD application
    nfd_remove_input = SystemApplicationRemoveInput()
    nfd_remove_input.set_app_name(nfd_name)
    nfd_remove_input.set_force_removal(False)
    nfd_remove_input.set_timeout_in_seconds(90)

    # system_application_remove already waits for the 'uploaded' status and raises on timeout.
    SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(nfd_remove_input)

    # Delete the NFD application
    nfd_delete_input = SystemApplicationDeleteInput()
    nfd_delete_input.set_app_name(nfd_name)
    nfd_delete_input.set_force_deletion(False)
    nfd_delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(nfd_delete_input)
    validate_equals(nfd_delete_msg, f"Application {nfd_name} deleted.\n", "NFD deletion message validation")


@mark.p1
@mark.lab_is_simplex
@mark.lab_has_cstate_support
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
    power_manager_keywords = PowerManagerKeywords(ssh_connection)

    get_logger().log_test_case_step("Cleanup kubernetes-power-manager environment")
    power_manager_keywords.cleanup_environment(nfd_name, power_manager_name)

    def cleanup() -> None:
        get_logger().log_teardown_step("Removing and deleting kubernetes-power-manager environment")
        power_manager_keywords.cleanup_environment(nfd_name, power_manager_name)

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

    get_logger().log_test_case_step(f"Verifying {power_manager_name} auto-reapplies after unlock")
    power_manager_keywords.wait_for_auto_reapply(power_manager_name)
