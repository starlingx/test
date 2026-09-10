"""DC Subcloud Backup Restore tests.

Verifies restore of a subcloud backup from central and local storage for single
subclouds and subcloud groups, across simplex and duplex topologies and
active/N-1/N-2 loads. Covers install and no-install restores, restore-values
overrides, auto-restore, factory-restore, and restores executed from the standby
system controller. Duplex members are powered off automatically by the restore
keyword before an install-based restore.

Prerequisites:
    - System controller accessible (--lab_config_file)
    - A backup must already exist for the target subcloud (produced by the
      corresponding backup-create tests)
    - At least one managed, online subcloud matching the target release/topology
    - At least two subclouds for the group tests

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/backup_restore/test_backup_restore.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.subcloud_lab_is_simplex / _is_duplex: topology gating
    - @mark.lab_has_subcloud / @mark.lab_has_min_2_subclouds: subcloud requirements
"""

from pytest import mark

from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords

TEST_GROUP_NAME = "TestGroup"


# --- Post-Restore Helpers ---


def manage_and_validate_health(system_controller_ssh: SSHConnection, subcloud_name: str) -> None:
    """Manage a restored subcloud and validate its cluster health.

    A restore leaves the subcloud unmanaged. Manage it, then validate the
    subcloud cluster is healthy, mirroring the subcloud deploy flow.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the active system controller.
        subcloud_name (str): Subcloud that was restored.
    """
    get_logger().log_test_case_step(f"Manage subcloud '{subcloud_name}'")
    DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_manage(subcloud_name, timeout=60)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


# --- Central Restore - Simplex ---


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_release(request):
    """Restore a simplex subcloud from its central backup running N release.

    Test Steps:
        1. Select an online simplex subcloud with a central backup available
        2. Restore the subcloud from its central backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_local_single_simplex_subcloud_n_release(request):
    """Restore a simplex subcloud from its local backup running N release.

    Test Steps:
        1. Select an online simplex subcloud with a local backup available
        2. Restore the subcloud from its local backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_minus_1_release(request):
    """Restore a simplex subcloud from its central backup running N-1 release.

    Test Steps:
        1. Select an online simplex subcloud with a central backup available
        2. Restore the subcloud from its central backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_minus_2_release(request):
    """Restore a simplex subcloud from its central backup running N-2 release.

    Test Steps:
        1. Select an online simplex subcloud with a central backup available
        2. Restore the subcloud from its central backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_local_single_simplex_subcloud_n_minus_1_release(request):
    """Restore a simplex subcloud from its local backup running N-1 release.

    Test Steps:
        1. Select an online simplex subcloud with a local backup available
        2. Restore the subcloud from its local backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_local_single_simplex_subcloud_n_minus_2_release(request):
    """Restore a simplex subcloud from its local backup running N-2 release.

    Test Steps:
        1. Select an online simplex subcloud with a local backup available
        2. Restore the subcloud from its local backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


# --- Central/Local Restore With Restore Values - Simplex ---


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_release_with_restore_values(request):
    """Restore a simplex subcloud from its central backup using restore values.

    Test Steps:
        1. Select an online simplex subcloud with a central backup available
        2. Create a restore-values yaml on the system controller
        3. Restore the subcloud from its central backup passing the restore-values yaml and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    FileKeywords(system_controller_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release, override_values="restore_values.yaml")
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_local_single_simplex_subcloud_n_release_with_restore_values(request):
    """Restore a simplex subcloud from its local backup using restore values.

    Test Steps:
        1. Select an online simplex subcloud with a local backup available
        2. Create a restore-values yaml on the system controller
        3. Restore the subcloud from its local backup passing the restore-values yaml and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    FileKeywords(system_controller_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release, override_values="restore_values.yaml")
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_minus_1_release_with_restore_values(request):
    """Restore a simplex subcloud from its central backup running N-1 release using restore values.

    Test Steps:
        1. Select an online simplex subcloud with a central backup available
        2. Create a restore-values yaml on the system controller
        3. Restore the subcloud from its central backup passing the restore-values yaml and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    FileKeywords(system_controller_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release, override_values="restore_values.yaml")
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_minus_2_release_with_restore_values(request):
    """Restore a simplex subcloud from its central backup running N-2 release using restore values.

    Test Steps:
        1. Select an online simplex subcloud with a central backup available
        2. Create a restore-values yaml on the system controller
        3. Restore the subcloud from its central backup passing the restore-values yaml and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    FileKeywords(system_controller_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release, override_values="restore_values.yaml")
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_local_single_simplex_subcloud_n_minus_1_release_with_restore_values(request):
    """Restore a simplex subcloud from its local backup running N-1 release using restore values.

    Test Steps:
        1. Select an online simplex subcloud with a local backup available
        2. Create a restore-values yaml on the system controller
        3. Restore the subcloud from its local backup passing the restore-values yaml and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    FileKeywords(system_controller_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release, override_values="restore_values.yaml")
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_local_single_simplex_subcloud_n_minus_2_release_with_restore_values(request):
    """Restore a simplex subcloud from its local backup running N-2 release using restore values.

    Test Steps:
        1. Select an online simplex subcloud with a local backup available
        2. Create a restore-values yaml on the system controller
        3. Restore the subcloud from its local backup passing the restore-values yaml and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    FileKeywords(system_controller_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release, override_values="restore_values.yaml")
    manage_and_validate_health(system_controller_ssh, result.get_name())


# --- Central Restore No Install - Simplex ---


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_release_no_install(request):
    """Restore a simplex subcloud from its central backup without reinstall.

    Test Steps:
        1. Select an online simplex subcloud with a central backup available
        2. Restore the subcloud from its central backup without reinstall and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release, with_install=False)
    manage_and_validate_health(system_controller_ssh, result.get_name())


# --- Auto/Factory Restore - Simplex ---


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_auto_restore_central_single_simplex_subcloud_n_release(request):
    """Auto-restore a simplex subcloud from its central backup running N release.

    Test Steps:
        1. Select an online simplex subcloud with a central backup available
        2. Auto-restore the subcloud from its central backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).auto_restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_auto_restore_local_single_simplex_subcloud_n_release(request):
    """Auto-restore a simplex subcloud from its local backup running N release.

    Test Steps:
        1. Select an online simplex subcloud with a local backup available
        2. Auto-restore the subcloud from its local backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).auto_restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_factory_restore_local_single_simplex_subcloud_n_release(request):
    """Factory-restore a simplex subcloud from its factory backup running N release.

    Test Steps:
        1. Select an online simplex subcloud with a local backup available
        2. Factory-restore the subcloud from its factory backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    DcManagerSubcloudBackupKeywords(system_controller_ssh).factory_restore_backup(result.get_name())
    manage_and_validate_health(system_controller_ssh, result.get_name())


# --- Central Restore - Duplex ---


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_backup_restore_central_single_duplex_subcloud_n_release(request):
    """Restore a duplex subcloud from its central backup running N release.

    Test Steps:
        1. Select an online duplex subcloud with a central backup available
        2. Restore the subcloud from its central backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.DUPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_backup_restore_central_single_duplex_subcloud_n_minus_1_release(request):
    """Restore a duplex subcloud from its central backup running N-1 release.

    Test Steps:
        1. Select an online duplex subcloud with a central backup available
        2. Restore the subcloud from its central backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.DUPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_backup_restore_central_single_duplex_subcloud_n_minus_2_release(request):
    """Restore a duplex subcloud from its central backup running N-2 release.

    Test Steps:
        1. Select an online duplex subcloud with a central backup available
        2. Restore the subcloud from its central backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.DUPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


# --- Local Restore - Duplex ---


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_backup_restore_local_single_duplex_subcloud_n_release(request):
    """Restore a duplex subcloud from its local backup running N release.

    Test Steps:
        1. Select an online duplex subcloud with a local backup available
        2. Restore the subcloud from its local backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.DUPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_backup_restore_local_single_duplex_subcloud_n_minus_1_release(request):
    """Restore a duplex subcloud from its local backup running N-1 release.

    Test Steps:
        1. Select an online duplex subcloud with a local backup available
        2. Restore the subcloud from its local backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.DUPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_backup_restore_local_single_duplex_subcloud_n_minus_2_release(request):
    """Restore a duplex subcloud from its local backup running N-2 release.

    Test Steps:
        1. Select an online duplex subcloud with a local backup available
        2. Restore the subcloud from its local backup and verify it completes
        3. Manage the restored subcloud
        4. Validate the subcloud cluster is healthy
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.DUPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


# --- Restore From System Controller 1 - Simplex ---


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_release_from_system_controller_1(request):
    """Restore a simplex subcloud from its central backup driven from controller-1.

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online simplex subcloud with a central backup available
        3. Restore the subcloud from its central backup and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_local_single_simplex_subcloud_n_release_from_system_controller_1(request):
    """Restore a simplex subcloud from its local backup driven from controller-1.

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online simplex subcloud with a local backup available
        3. Restore the subcloud from its local backup and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_sw_version())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_minus_1_release_from_system_controller_1(request):
    """Restore a simplex subcloud from its central backup running N-1 release driven from controller-1.

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online simplex subcloud with a central backup available
        3. Restore the subcloud from its central backup and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_central_single_simplex_subcloud_n_minus_2_release_from_system_controller_1(request):
    """Restore a simplex subcloud from its central backup running N-2 release driven from controller-1.

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online simplex subcloud with a central backup available
        3. Restore the subcloud from its central backup and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-central", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_central_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_local_single_simplex_subcloud_n_minus_1_release_from_system_controller_1(request):
    """Restore a simplex subcloud from its local backup running N-1 release driven from controller-1.

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online simplex subcloud with a local backup available
        3. Restore the subcloud from its local backup and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_backup_restore_local_single_simplex_subcloud_n_minus_2_release_from_system_controller_1(request):
    """Restore a simplex subcloud from its local backup running N-2 release driven from controller-1.

    Test Steps:
        1. Swact the central cloud to make controller-1 the active system controller
        2. Select an online simplex subcloud with a local backup available
        3. Restore the subcloud from its local backup and verify it completes
        4. Manage the restored subcloud
        5. Validate the subcloud cluster is healthy

    Teardown:
        - Swact the central cloud back to controller-0
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-0"))
    SystemHostSwactKeywords(central_ssh).ensure_controller_is_active("controller-1")

    system_controller_ssh, result = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, backup_status="complete-local", lab_type=LabTypeEnum.SIMPLEX)
    backup_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_local_backup(result.get_name(), backup_release)
    manage_and_validate_health(system_controller_ssh, result.get_name())


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
