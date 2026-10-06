"""DC Subcloud Backup Delete tests.

Verifies deletion of pre-existing subcloud backups from central and local
storage, for the active (N), N-1 and N-2 releases, driven from controller-0 and
controller-1, and for subcloud groups. These tests delete only - the backup must
already exist (produced by the corresponding backup-create tests). The subcloud
is selected with the picker by backup mode and release so a subcloud that
actually has the backup on disk is chosen.

Prerequisites:
    - System controller accessible (--lab_config_file)
    - A backup of the target mode/release must already exist (produced by the
      corresponding backup-create tests)
    - At least one managed, online subcloud with the required backup

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/backup_restore/test_delete_subcloud_backup.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.lab_has_subcloud: requires at least one subcloud
    - @mark.lab_has_min_2_subclouds: group tests require at least two subclouds
"""

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from pytest import FixtureRequest, mark

GROUP_NAME = "Test"


# --- Post-Delete Helpers ---


def validate_backup_status_unknown(system_controller_ssh: object, subcloud_name: str) -> None:
    """Validate a subcloud's backup status is 'unknown' after its backup is deleted.

    Args:
        system_controller_ssh (object): SSH connection to the active system controller.
        subcloud_name (str): Subcloud whose backup status is checked.
    """
    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' backup status is 'unknown'")
    backup_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_backup_status()
    validate_equals(backup_status, "unknown", "Subcloud backup status after deletion")


# --- Central Delete - Single Subcloud ---


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_central(request: FixtureRequest):
    """Delete a subcloud's central backup running N release.

    Preconditions:
        - A central backup for release N already exists for a subcloud

    Test Steps:
        1. Select an online subcloud with a central backup available for release N
        2. Delete the central backup and verify it is removed
        3. Validate the subcloud backup status is 'unknown'
    """
    backup_release = "N"
    system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        backup_mode="central",
        backup_release=backup_release,
    )
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_central_backup(result.get_name(), backup_release)
    validate_backup_status_unknown(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_central_n_minus_one(request: FixtureRequest):
    """Delete a subcloud's central backup running N-1 release.

    Preconditions:
        - A central backup for release N-1 already exists for a subcloud

    Test Steps:
        1. Select an online subcloud with a central backup available for release N-1
        2. Delete the central backup and verify it is removed
        3. Validate the subcloud backup status is 'unknown'
    """
    backup_release = "N-1"
    system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        backup_mode="central",
        backup_release=backup_release,
    )
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_central_backup(result.get_name(), backup_release)
    validate_backup_status_unknown(system_controller_ssh, result.get_name())


# --- Local Delete - Single Subcloud ---


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_local(request: FixtureRequest):
    """Delete a subcloud's local backup running N release.

    Preconditions:
        - A local backup for release N already exists for a subcloud

    Test Steps:
        1. Select an online subcloud with a local backup available for release N
        2. Delete the local backup and verify it is removed
        3. Validate the subcloud backup status is 'unknown'
    """
    backup_release = "N"
    system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        backup_mode="local",
        backup_release=backup_release,
    )
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_local_backup(result.get_name(), backup_release)
    validate_backup_status_unknown(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_local_n_minus_one(request: FixtureRequest):
    """Delete a subcloud's local backup running N-1 release.

    Preconditions:
        - A local backup for release N-1 already exists for a subcloud

    Test Steps:
        1. Select an online subcloud with a local backup available for release N-1
        2. Delete the local backup and verify it is removed
        3. Validate the subcloud backup status is 'unknown'
    """
    backup_release = "N-1"
    system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        backup_mode="local",
        backup_release=backup_release,
    )
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_local_backup(result.get_name(), backup_release)
    validate_backup_status_unknown(system_controller_ssh, result.get_name())


# --- Central/Local Delete From Controller-1 - Single Subcloud ---


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_central_controller1(request: FixtureRequest):
    """Delete a subcloud's central backup (N-1 release) driven from controller-1.

    Preconditions:
        - A central backup for release N-1 already exists for a subcloud

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online subcloud with a central backup available for release N-1
        3. Delete the central backup and verify it is removed
        4. Validate the subcloud backup status is 'unknown'

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    backup_release = "N-1"
    system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        backup_mode="central",
        backup_release=backup_release,
    )
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_central_backup(result.get_name(), backup_release)
    validate_backup_status_unknown(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_local_controller1(request: FixtureRequest):
    """Delete a subcloud's local backup (N release) driven from controller-1.

    Preconditions:
        - A local backup for release N already exists for a subcloud

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online subcloud with a local backup available for release N
        3. Delete the local backup and verify it is removed
        4. Validate the subcloud backup status is 'unknown'

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    backup_release = "N"
    system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        backup_mode="local",
        backup_release=backup_release,
    )
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_local_backup(result.get_name(), backup_release)
    validate_backup_status_unknown(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
def test_controller_1_delete_backup_central_n_minus_one(request: FixtureRequest):
    """Delete a subcloud's central backup (N-1 release) with controller-1 active.

    Preconditions:
        - A central backup for release N-1 already exists for a subcloud

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online subcloud with a central backup available for release N-1
        3. Delete the central backup and verify it is removed
        4. Validate the subcloud backup status is 'unknown'

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    backup_release = "N-1"
    system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        backup_mode="central",
        backup_release=backup_release,
    )
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_central_backup(result.get_name(), backup_release)
    validate_backup_status_unknown(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
def test_controller_1_delete_backup_local_n_minus_one(request: FixtureRequest):
    """Delete a subcloud's local backup (N-1 release) with controller-1 active.

    Preconditions:
        - A local backup for release N-1 already exists for a subcloud

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online subcloud with a local backup available for release N-1
        3. Delete the local backup and verify it is removed
        4. Validate the subcloud backup status is 'unknown'

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    backup_release = "N-1"
    system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        backup_mode="local",
        backup_release=backup_release,
    )
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_local_backup(result.get_name(), backup_release)
    validate_backup_status_unknown(system_controller_ssh, result.get_name())


# --- Group Delete ---


@mark.p2
@mark.lab_has_min_2_subclouds
def test_delete_backup_group_on_central(request: FixtureRequest):
    """Delete a subcloud group's central backup for the active release.

    Builds a group from the online subclouds running the active release (via the
    subcloud picker), then deletes the group's central backup. Per-group backup
    existence is not pre-filtered; the backup is expected to exist from the
    corresponding group backup-create test.

    Preconditions:
        - A central group backup for release N already exists

    Setup:
        - Build a subcloud group from online subclouds running release N

    Test Steps:
        1. Delete the group's central backup and verify it is removed

    Teardown:
        - Reset the group members to the Default group and delete the group
    """
    backup_release = "N"

    get_logger().log_setup_step(f"Build subcloud group '{GROUP_NAME}' from online subclouds running release N")
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N", GROUP_NAME)
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(GROUP_NAME, members))

    get_logger().log_test_case_step(f"Delete central backup for subcloud group '{GROUP_NAME}'")
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_group_central_backup(GROUP_NAME, members, backup_release)


@mark.p2
@mark.lab_has_min_2_subclouds
def test_delete_backup_group_on_local(request: FixtureRequest):
    """Delete a subcloud group's local backup for the active release.

    Builds a group from the online subclouds running the active release (via the
    subcloud picker), then deletes the group's local backup. Per-group backup
    existence is not pre-filtered; the backup is expected to exist from the
    corresponding group backup-create test.

    Preconditions:
        - A local group backup for release N already exists

    Setup:
        - Build a subcloud group from online subclouds running release N

    Test Steps:
        1. Delete the group's local backup and verify it is removed

    Teardown:
        - Reset the group members to the Default group and delete the group
    """
    backup_release = "N"

    get_logger().log_setup_step(f"Build subcloud group '{GROUP_NAME}' from online subclouds running release N")
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N", GROUP_NAME)
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(GROUP_NAME, members))

    get_logger().log_test_case_step(f"Delete local backup for subcloud group '{GROUP_NAME}'")
    DcManagerSubcloudBackupKeywords(system_controller_ssh).delete_group_local_backup(GROUP_NAME, members, backup_release)
