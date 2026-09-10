"""DC Subcloud Backup Restore - Group Subcloud tests.

Verifies restore of a subcloud group from central and local backups. Each test
builds a temporary subcloud group from picker-selected members, restores the
group, verifies all members complete, and tears the group down.

Prerequisites:
    - System controller accessible (--lab_config_file)
    - Backups must already exist for the group members (produced by the
      corresponding backup-create tests)
    - At least two managed, online subclouds

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/backup_restore/test_backup_restore_group_subcloud.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.lab_has_min_2_subclouds: requires at least two subclouds
"""

from pytest import mark

from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass

TEST_GROUP_NAME = "TestGroup"


# --- Group Restore ---


@mark.p2
@mark.lab_has_min_2_subclouds
def test_restore_group_central_backup(request):
    """Restore a subcloud group from central backups running N release.

    Test Steps:
        1. Select online subclouds running N release and assign them to a group
        2. Restore the group from central backups and verify all members complete

    Teardown:
        - Reset members to Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N", TEST_GROUP_NAME)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_group_central_backup(TEST_GROUP_NAME, members, backup_release)


@mark.p2
@mark.lab_has_min_2_subclouds
def test_restore_group_local_backup(request):
    """Restore a subcloud group from local backups running N release.

    Test Steps:
        1. Select online subclouds running N release and assign them to a group
        2. Restore the group from local backups and verify all members complete

    Teardown:
        - Reset members to Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N", TEST_GROUP_NAME)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_group_local_backup(TEST_GROUP_NAME, members, backup_release)
