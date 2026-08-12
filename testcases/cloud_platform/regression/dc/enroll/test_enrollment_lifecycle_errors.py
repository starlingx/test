"""
Lifecycle-ordered error handling tests for subcloud enrollment and restore.

Validates that dcmanager rejects invalid operations at each stage of the
subcloud lifecycle: transitory enrollment state, managed/complete state.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_not_equals, validate_str_contains
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

GENERIC_DCMANAGER_ERROR = "the server could not comply with the request since it is either malformed or otherwise incorrect."
DEPLOY_ENROLL_WRONG_STATE_ERROR = "Subcloud deploy status must be either: create-complete, enroll-failed, pre-enroll-failed, pre-init-enroll-failed, init-enroll-failed, factory-restore-complete"
RESTORE_INVALID_STATE_ERROR = "must be unmanaged and in a valid deploy state for the subcloud-backup restore operation."


# =============================================================================
# Stage 1: Enrollment with transitory state test
# =============================================================================


@mark.p2
@mark.lab_has_subcloud
def test_enroll_subcloud_and_reject_restore_during_transitory_state(request: FixtureRequest):
    """Enroll subcloud and verify restore is rejected during transitory state.

    Deletes the subcloud from dcmanager if it exists, starts enrollment via
    'subcloud add --enroll', polls for transitory state, attempts a backup
    restore (expects rejection), then waits for enrollment to complete and
    subcloud to come online.

    Preconditions:
        - Target subcloud is factory-restored (hardware ready).
        - Subcloud may or may not exist in dcmanager (test handles deletion).
        - Deployment assets available on the system controller.

    Test Steps:
        1. Delete subcloud from dcmanager if it exists.
        2. Run dcmanager subcloud add --enroll.
        3. Poll until subcloud reaches transitory 'enrolling' state.
        4. Run dcmanager subcloud-backup restore.
        5. Validate rejection with error about invalid deploy state.
        6. Wait for enrollment to reach 'complete' status.
        7. Wait for subcloud to come online.
        8. Manage the subcloud.

    Expected Results:
        - Restore command returns non-zero exit code during enrollment.
        - Error about subcloud being in invalid deploy state for restore.
        - Enrollment completes and subcloud comes online and is managed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name = lab_config.get_subcloud_names()[0]
    subcloud_obj = lab_config.get_subcloud(subcloud_name)
    subcloud_password = subcloud_obj.get_admin_credentials().get_password()

    # Delete subcloud from dcmanager if it exists
    dcm_list_kw = DcManagerSubcloudListKeywords(system_controller_ssh)
    sc_list = dcm_list_kw.get_dcmanager_subcloud_list()
    if sc_list.is_subcloud_in_output(subcloud_name):
        get_logger().log_test_case_step(f"Deleting {subcloud_name} from dcmanager")
        subcloud_status = sc_list.get_subcloud_by_name(subcloud_name)
        if subcloud_status.get_management() == "managed":
            DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 60)
        DcManagerSubcloudDeleteKeywords(system_controller_ssh).dcmanager_subcloud_delete(subcloud_name)

    # Start enrollment
    get_logger().log_test_case_step(f"Starting enrollment for {subcloud_name} via subcloud add --enroll")
    sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
    DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll(
        subcloud_name=subcloud_name,
        bootstrap_values=sc_assets.get_bootstrap_file(),
        install_values=sc_assets.get_install_file(),
        deploy_config_file=sc_assets.get_deployment_config_file(),
    )

    # Poll for transitory state
    get_logger().log_test_case_step("Polling for transitory 'enrolling' state")
    DcManagerSubcloudShowKeywords(system_controller_ssh).wait_for_state(
        subcloud_name, "deploy_status", "enrolling", timeout=300, check_interval=5
    )

    # Attempt restore during enrollment — expect rejection
    get_logger().log_test_case_step("Running backup restore while subcloud is enrolling")
    output, rc = DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_subcloud_backup_with_error(
        sysadmin_password=subcloud_password,
        subcloud=subcloud_name,
    )

    get_logger().log_info(f"Return code: {rc}, Output: {output}")

    # Capture validation result but don't fail yet — must complete enrollment first
    transitory_test_passed = rc != 0 and RESTORE_INVALID_STATE_ERROR.lower() in output.lower()
    if not transitory_test_passed:
        get_logger().log_info(f"Transitory state test result: rc={rc}, expected error not found in output")

    # Wait for enrollment to complete
    get_logger().log_test_case_step("Waiting for enrollment to reach 'complete' status")
    dcm_list_kw.validate_subcloud_status(subcloud_name, "complete")

    # Wait for subcloud to come online
    get_logger().log_test_case_step(f"Waiting for {subcloud_name} to come online")

    def get_availability():
        sc_list_out = dcm_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
        return sc_list_out.get_availability()

    validate_equals_with_retry(get_availability, "online", "Validate subcloud is online after enrollment.", timeout=900, polling_sleep_time=30)

    # Manage the subcloud
    get_logger().log_test_case_step(f"Managing subcloud {subcloud_name}")
    DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_manage(subcloud_name, 120)

    # Now assert the transitory state test result
    validate_not_equals(rc, 0, f"Command should be rejected. Got rc={rc}. Output: {output}")
    validate_str_contains(
        output.lower(), RESTORE_INVALID_STATE_ERROR.lower(),
        "Error about subcloud being in invalid deploy state for restore",
    )


# =============================================================================
# Stage 2: managed/complete
# =============================================================================


@mark.p2
@mark.lab_has_subcloud
def test_deploy_enroll_rejects_complete_subcloud(request: FixtureRequest):
    """Verify deploy enroll is rejected on a managed/complete subcloud.

    Preconditions:
        - Target subcloud is managed with deploy status 'complete'.
        - Subcloud must have been enrolled and brought online prior to this test.

    Test Steps:
        1. Verify subcloud is managed and complete.
        2. Run dcmanager subcloud deploy enroll with valid parameters.
        3. Validate rejection due to invalid deploy status.

    Expected Results:
        - Non-zero exit code.
        - Error about deploy status not being valid for enrollment.
        - No subcloud state change.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name = lab_config.get_subcloud_names()[0]
    subcloud_obj = lab_config.get_subcloud(subcloud_name)

    get_logger().log_test_case_step(f"Verifying {subcloud_name} is managed and complete")
    sc_list = DcManagerSubcloudListKeywords(system_controller_ssh).get_dcmanager_subcloud_list()
    subcloud_status = sc_list.get_subcloud_by_name(subcloud_name)
    validate_equals(subcloud_status.get_management(), "managed", "Precondition: subcloud must be managed")
    validate_equals(subcloud_status.get_deploy_status(), "complete", "Precondition: deploy status must be complete")

    sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
    sysadmin_password = subcloud_obj.get_admin_credentials().get_password()
    bmc_password = subcloud_obj.get_bm_password() or sysadmin_password

    get_logger().log_test_case_step("Running deploy enroll on managed/complete subcloud")
    output, rc = DCManagerSubcloudDeployKeywords(system_controller_ssh).dcmanager_subcloud_deploy_enroll_with_error(
        subcloud_name,
        bootstrap_values=sc_assets.get_bootstrap_file(),
        install_values=sc_assets.get_install_file(),
        sysadmin_password=sysadmin_password,
        bmc_password=bmc_password,
        bootstrap_address=subcloud_obj.get_first_controller().get_ip(),
    )

    validate_not_equals(rc, 0, f"Command should be rejected. Got rc={rc}. Output: {output}")
    validate_str_contains(output.lower(), GENERIC_DCMANAGER_ERROR, "Generic dcmanager error present")
    validate_str_contains(output.lower(), DEPLOY_ENROLL_WRONG_STATE_ERROR.lower(), "Error about invalid deploy status")


@mark.p2
@mark.lab_has_subcloud
def test_restore_rejects_managed_subcloud(request: FixtureRequest):
    """Verify backup restore is rejected on a managed subcloud.

    Preconditions:
        - Target subcloud is managed.
        - Subcloud must have been enrolled and brought online prior to this test.

    Test Steps:
        1. Verify subcloud is managed.
        2. Run dcmanager subcloud-backup restore.
        3. Validate rejection with error about management state.

    Expected Results:
        - Non-zero exit code.
        - Error about subcloud must be unmanaged.
        - No subcloud state change.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name = lab_config.get_subcloud_names()[0]
    subcloud_obj = lab_config.get_subcloud(subcloud_name)
    subcloud_password = subcloud_obj.get_admin_credentials().get_password()

    get_logger().log_test_case_step(f"Verifying {subcloud_name} is managed")
    sc_list = DcManagerSubcloudListKeywords(system_controller_ssh).get_dcmanager_subcloud_list()
    subcloud_status = sc_list.get_subcloud_by_name(subcloud_name)
    validate_equals(subcloud_status.get_management(), "managed", "Precondition: subcloud must be managed")

    get_logger().log_test_case_step("Running backup restore on managed subcloud")
    output, rc = DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_subcloud_backup_with_error(
        sysadmin_password=subcloud_password,
        subcloud=subcloud_name,
    )

    validate_not_equals(rc, 0, f"Command should be rejected. Got rc={rc}. Output: {output}")
    validate_str_contains(output.lower(), RESTORE_INVALID_STATE_ERROR.lower(), "Error about subcloud must be unmanaged")
