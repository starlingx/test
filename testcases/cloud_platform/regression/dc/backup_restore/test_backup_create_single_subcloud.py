"""DC Subcloud Backup Create - Single Subcloud tests.

Verifies subcloud backup creation on central and local storage for a single
subcloud, across simplex, duplex, and standard topologies and active/N-1/N-2
loads. The created backup is intentionally left in place - it is the product
of the test and is consumed by the corresponding restore tests.

Prerequisites:
    - System controller accessible (--lab_config_file)
    - At least one managed, online subcloud matching the target release/topology

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/backup_restore/test_backup_create_single_subcloud.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.subcloud_lab_is_simplex / _is_duplex / _is_standard: topology gating
    - @mark.lab_has_subcloud: requires at least one subcloud
"""

from pytest import mark

from config.lab.objects.lab_type_enum import LabTypeEnum
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback


# --- Central Backup - Simplex ---


@mark.p0
@mark.subcloud_lab_is_simplex
def test_backup_create_central_single_simplex_subcloud_n_release(request):
    """Create a central backup for a simplex subcloud running N release.

    Test Steps:
        1. Select an online simplex subcloud running N release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_create_central_single_simplex_subcloud_n_minus_1_release(request):
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
def test_backup_create_central_single_simplex_subcloud_n_minus_2_release(request):
    """Create a central backup for a simplex subcloud running N-2 release.

    Test Steps:
        1. Select an online simplex subcloud running N-2 release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-2", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_create_central_single_simplex_subcloud_n_release_with_backup_values(request):
    """Create a central backup for a simplex subcloud using backup values.

    Test Steps:
        1. Select an online simplex subcloud running N release
        2. Create a central backup passing a backup-values yaml and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name(), backup_values=True)


# --- Central Backup - Duplex ---


@mark.p0
@mark.subcloud_lab_is_duplex
def test_backup_create_central_single_duplex_subcloud_n_release(request):
    """Create a central backup for a duplex subcloud running N release.

    Test Steps:
        1. Select an online duplex subcloud running N release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_backup_create_central_single_duplex_subcloud_n_minus_1_release(request):
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
def test_backup_create_central_single_duplex_subcloud_n_minus_2_release(request):
    """Create a central backup for a duplex subcloud running N-2 release.

    Test Steps:
        1. Select an online duplex subcloud running N-2 release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-2", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


# --- Central Backup - Standard ---


@mark.p0
@mark.subcloud_lab_is_standard
def test_backup_create_central_single_standard_subcloud_n_release(request):
    """Create a central backup for a standard subcloud running N release.

    Test Steps:
        1. Select an online standard subcloud running N release
        2. Create a central backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.STANDARD)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_central_backup(result.get_name())


# --- Local Backup - Simplex ---


@mark.p0
@mark.subcloud_lab_is_simplex
def test_backup_create_local_single_simplex_subcloud_n_release(request):
    """Create a local backup for a simplex subcloud running N release.

    Test Steps:
        1. Select an online simplex subcloud running N release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


@mark.p0
@mark.subcloud_lab_is_simplex
def test_backup_create_local_single_simplex_subcloud_n_release_custom_path(request):
    """Create a local backup for a simplex subcloud to a custom path.

    Test Steps:
        1. Select an online simplex subcloud running N release
        2. Create a local backup redirected to a custom path and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name(), custom_path=True)


@mark.p0
@mark.subcloud_lab_is_simplex
def test_backup_create_local_single_simplex_subcloud_n_release_with_backup_values(request):
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
def test_backup_create_local_single_simplex_subcloud_n_minus_1_release(request):
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
def test_backup_create_local_single_simplex_subcloud_n_minus_2_release(request):
    """Create a local backup for a simplex subcloud running N-2 release.

    Test Steps:
        1. Select an online simplex subcloud running N-2 release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-2", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


# --- Local Backup - Duplex ---


@mark.p0
@mark.subcloud_lab_is_duplex
def test_backup_create_local_single_duplex_subcloud_n_release(request):
    """Create a local backup for a duplex subcloud running N release.

    Test Steps:
        1. Select an online duplex subcloud running N release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_backup_create_local_single_duplex_subcloud_n_minus_1_release(request):
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
def test_backup_create_local_single_duplex_subcloud_n_minus_2_release(request):
    """Create a local backup for a duplex subcloud running N-2 release.

    Test Steps:
        1. Select an online duplex subcloud running N-2 release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N-2", lab_type=LabTypeEnum.DUPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())


# --- Local Backup - Standard ---


@mark.p0
@mark.subcloud_lab_is_standard
def test_backup_create_local_single_standard_subcloud_n_release(request):
    """Create a local backup for a standard subcloud running N release.

    Test Steps:
        1. Select an online standard subcloud running N release
        2. Create a local backup and verify it completes
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load="N", lab_type=LabTypeEnum.STANDARD)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).create_local_backup(result.get_name())
