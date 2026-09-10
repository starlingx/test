"""DC Subcloud Backup Create - Group Subcloud tests.

Verifies subcloud group backup creation on central and local storage across
active/N-1/N-2 loads. Each test builds a temporary subcloud group from the
picker-selected members, creates the group backup, and tears the group down.

Prerequisites:
    - System controller accessible (--lab_config_file)
    - At least two managed, online subclouds matching the target release

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/backup_restore/test_backup_create_group_subcloud.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.lab_has_min_2_subclouds: requires at least two subclouds
"""

from pytest import mark

from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords

TEST_GROUP_NAME = "TestGroup"


@mark.p0
@mark.lab_has_min_2_subclouds
def test_backup_create_central_subcloud_group_n_release(request):
    """Create a central backup for a subcloud group running N release.

    Test Steps:
        1. Select online subclouds running N release and assign them to a group
        2. Create a central group backup and verify all members complete

    Teardown:
        - Reset members to Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N", TEST_GROUP_NAME)
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_group_central_backup(TEST_GROUP_NAME, members)


@mark.p0
@mark.lab_has_min_2_subclouds
def test_backup_create_central_subcloud_group_n_minus_1_release(request):
    """Create a central backup for a subcloud group running N-1 release.

    Test Steps:
        1. Select online subclouds running N-1 release and assign them to a group
        2. Create a central group backup and verify all members complete

    Teardown:
        - Reset members to Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N-1", TEST_GROUP_NAME)
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_group_central_backup(TEST_GROUP_NAME, members)


@mark.p0
@mark.lab_has_min_2_subclouds
def test_backup_create_central_subcloud_group_n_minus_2_release(request):
    """Create a central backup for a subcloud group running N-2 release.

    Test Steps:
        1. Select online subclouds running N-2 release and assign them to a group
        2. Create a central group backup and verify all members complete

    Teardown:
        - Reset members to Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N-2", TEST_GROUP_NAME)
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_group_central_backup(TEST_GROUP_NAME, members)


@mark.p0
@mark.lab_has_min_2_subclouds
def test_backup_create_local_subcloud_group_n_release(request):
    """Create a local backup for a subcloud group running N release.

    Test Steps:
        1. Select online subclouds running N release and assign them to a group
        2. Create a local group backup and verify all members complete

    Teardown:
        - Reset members to Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N", TEST_GROUP_NAME)
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_group_local_backup(TEST_GROUP_NAME, members)


@mark.p0
@mark.lab_has_min_2_subclouds
def test_backup_create_local_subcloud_group_n_minus_1_release(request):
    """Create a local backup for a subcloud group running N-1 release.

    Test Steps:
        1. Select online subclouds running N-1 release and assign them to a group
        2. Create a local group backup and verify all members complete

    Teardown:
        - Reset members to Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N-1", TEST_GROUP_NAME)
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_group_local_backup(TEST_GROUP_NAME, members)


@mark.p0
@mark.lab_has_min_2_subclouds
def test_backup_create_local_subcloud_group_n_minus_2_release(request):
    """Create a local backup for a subcloud group running N-2 release.

    Test Steps:
        1. Select online subclouds running N-2 release and assign them to a group
        2. Create a local group backup and verify all members complete

    Teardown:
        - Reset members to Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build_from_load("N-2", TEST_GROUP_NAME)
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_group_local_backup(TEST_GROUP_NAME, members)
