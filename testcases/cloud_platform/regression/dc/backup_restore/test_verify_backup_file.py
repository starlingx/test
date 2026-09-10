"""DC Subcloud Backup Create tests.

Verifies subcloud backup creation on central and local storage for single
subclouds and subcloud groups, across simplex, duplex, and standard topologies
and active/N-1/N-2 loads. The created backup is intentionally left in place - it
is the product of the test and is consumed by the corresponding restore tests.

Prerequisites:
    - System controller accessible (--lab_config_file)
    - At least one managed, online subcloud matching the target release/topology
    - At least two subclouds for the group tests

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/backup_restore/test_verify_backup_file.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.subcloud_lab_is_simplex / _is_duplex / _is_standard: topology gating
    - @mark.lab_has_subcloud / @mark.lab_has_min_2_subclouds: subcloud requirements
"""

from pytest import mark

from config.lab.objects.lab_type_enum import LabTypeEnum
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback

TEST_GROUP_NAME = "TestGroup"


# --- Central Backup - Single Subcloud ---


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_central_simplex(request):
    """Create a central backup for a simplex subcloud running N release.

    Test Steps:
        1. Select an online simplex subcloud running N release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


@mark.p0
@mark.subcloud_lab_is_duplex
def test_verify_backup_central_duplex(request):
    """Create a central backup for a duplex subcloud running N release.

    Test Steps:
        1. Select an online duplex subcloud running N release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


@mark.p0
@mark.subcloud_lab_is_standard
def test_verify_backup_central_std(request):
    """Create a central backup for a standard subcloud running N release.

    Test Steps:
        1. Select an online standard subcloud running N release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.STANDARD)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_central_with_backup_values(request):
    """Create a central backup for a simplex subcloud using backup values.

    Test Steps:
        1. Select an online simplex subcloud running N release
        2. Create a central backup passing a backup-values yaml and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name(), backup_values=True)


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_on_central_n_minus_one_simplex(request):
    """Create a central backup for a simplex subcloud running N-1 release.

    Test Steps:
        1. Select an online simplex subcloud running N-1 release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-1", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_on_central_n_minus_two_simplex(request):
    """Create a central backup for a simplex subcloud running N-2 release.

    Test Steps:
        1. Select an online simplex subcloud running N-2 release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-2", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_verify_backup_on_central_n_minus_one_duplex(request):
    """Create a central backup for a duplex subcloud running N-1 release.

    Test Steps:
        1. Select an online duplex subcloud running N-1 release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-1", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_verify_backup_on_central_n_minus_two_duplex(request):
    """Create a central backup for a duplex subcloud running N-2 release.

    Test Steps:
        1. Select an online duplex subcloud running N-2 release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-2", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


# --- Local Backup - Single Subcloud ---


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_simplex(request):
    """Create a local backup for a simplex subcloud running N release.

    Test Steps:
        1. Select an online simplex subcloud running N release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_custom_path_simplex(request):
    """Create a local backup for a simplex subcloud to a custom path.

    Test Steps:
        1. Select an online simplex subcloud running N release
        2. Create a local backup redirected to a custom path and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name(), custom_path=True)


@mark.p0
@mark.subcloud_lab_is_duplex
def test_verify_backup_local_duplex(request):
    """Create a local backup for a duplex subcloud running N release.

    Test Steps:
        1. Select an online duplex subcloud running N release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


@mark.p0
@mark.subcloud_lab_is_standard
def test_verify_backup_local_std(request):
    """Create a local backup for a standard subcloud running N release.

    Test Steps:
        1. Select an online standard subcloud running N release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.STANDARD)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_with_backup_values(request):
    """Create a local backup for a simplex subcloud using backup values.

    Test Steps:
        1. Select an online simplex subcloud running N release
        2. Create a local backup passing a backup-values yaml and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name(), backup_values=True)


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_n_minus_one_simplex(request):
    """Create a local backup for a simplex subcloud running N-1 release.

    Test Steps:
        1. Select an online simplex subcloud running N-1 release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-1", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_n_minus_two_simplex(request):
    """Create a local backup for a simplex subcloud running N-2 release.

    Test Steps:
        1. Select an online simplex subcloud running N-2 release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-2", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_verify_backup_local_n_minus_one_duplex(request):
    """Create a local backup for a duplex subcloud running N-1 release.

    Test Steps:
        1. Select an online duplex subcloud running N-1 release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-1", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_verify_backup_local_n_minus_two_duplex(request):
    """Create a local backup for a duplex subcloud running N-2 release.

    Test Steps:
        1. Select an online duplex subcloud running N-2 release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-2", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


# --- Central Backup - Subcloud Group ---


@mark.p0
@mark.lab_has_min_2_subclouds
def test_verify_backup_central_simplex_group(request):
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
def test_verify_backup_central_simplex_group_n_minus_one(request):
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
def test_verify_backup_central_simplex_group_n_minus_two(request):
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


# --- Local Backup - Subcloud Group ---


@mark.p0
@mark.lab_has_min_2_subclouds
def test_verify_backup_remote_simplex_group(request):
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
def test_verify_backup_remote_simplex_group_n_minus_one(request):
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
def test_verify_backup_remote_simplex_group_n_minus_two(request):
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
