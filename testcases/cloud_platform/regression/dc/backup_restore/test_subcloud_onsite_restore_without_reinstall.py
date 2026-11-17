"""Onsite restore without reinstall test cases.

Validates that a factory-installed simplex subcloud is restored in place (no OS
reinstall) by building an onsite-restore seed ISO, staging it on the SC HTTPS
tree, and mounting it via RVMC. Covers both the remote (central backup) and local
backup variants.

Prerequisites:
    - System controller accessible (--lab_config_file).
    - The target subcloud is factory-installed (e.g. after a factory install or a
      factory restore) and present in dcmanager; its deploy_status is not checked.
    - Subcloud factory_ip and factory_credentials are configured (the subcloud is
      reachable only on its factory IP/credentials at factory baseline).
    - Remote variant: a central backup exists on the System Controller at
      /opt/dc-vault/backups/<subcloud>/<sw_version>/.
    - Local variant: the local backup archive produced by the dashboard backup test
      with custom_path=True is present in the subcloud home directory
      (/home/<user>/<subcloud>_platform_backup_*.tgz); it survives the factory
      restore which wipes /opt/platform-backup/backups.
"""

from pytest import FixtureRequest, fail, mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.dcmanager_onsite_restore_keywords import DcManagerOnsiteRestoreKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords
from keywords.cloud_platform.kpi.dc_kpi_recorder_keywords import DcKpiRecorderKeywords
from keywords.cloud_platform.kpi.dcmanager_log_kpi_keywords import ANSIBLE_PLAYBOOK_LOG_TEMPLATE, ONSITE_RESTORE_PHASES, ONSITE_RESTORE_SESSION_MARKER, DcManagerLogKpiKeywords
from keywords.cloud_platform.nocloud.seed_iso_builder_keywords import SeedIsoBuilderKeywords
from keywords.cloud_platform.nocloud.seed_iso_staging_keywords import SeedIsoStagingKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager
from keywords.files.file_keywords import FileKeywords

# Platform local backup directory the onsite restore reads for local_only=true
# (/opt/platform-backup/backups/<sw_version>/).
PLATFORM_BACKUP_DIR_TEMPLATE = "/opt/platform-backup/backups/{sw_version}"
# Timeout (seconds) for dcmanager subcloud manage/unmanage operations. Matches the
# value used by the DC backup-restore tests' manage step.
MANAGE_TIMEOUT = 60


def _get_subcloud_software_version(system_controller_ssh: SSHConnection, subcloud_name: str) -> str:
    """Return the software version reported by dcmanager for the subcloud.

    Args:
        system_controller_ssh (SSHConnection): SSH to the active System Controller.
        subcloud_name (str): Name of the target subcloud.

    Returns:
        str: The subcloud software version.
    """
    return DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()


def _run_onsite_restore_prechecks(system_controller_ssh: SSHConnection, subcloud_name: str, local_only: bool) -> None:
    """Run the shared preconditions for onsite restore without reinstall.

    Prechecks are validated from the System Controller via dcmanager (no subcloud
    SSH). Checks follow the subcloud lifecycle order:
      1. Subcloud exists in dcmanager.
      2. Subcloud is unmanaged (unmanage it if currently managed).
      3. Local variant: stage the preserved local backup for the seed to read.

    Args:
        system_controller_ssh (SSHConnection): SSH to the active System Controller.
        subcloud_name (str): Name of the target subcloud.
        local_only (bool): Whether the restore uses the subcloud's local backup.
    """
    dcm_list_kw = DcManagerSubcloudListKeywords(system_controller_ssh)

    # 1. Subcloud must be known to dcmanager.
    get_logger().log_setup_step(f"Verify {subcloud_name} exists in dcmanager")
    if not dcm_list_kw.get_dcmanager_subcloud_list().is_subcloud_in_output(subcloud_name):
        fail(f"{subcloud_name} is not present in the dcmanager subcloud list; cannot run onsite restore.")

    subcloud_show = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object()

    # 2. Subcloud must be unmanaged before the restore.
    get_logger().log_setup_step(f"Ensure {subcloud_name} is unmanaged before restore")
    if subcloud_show.get_management() == "managed":
        get_logger().log_info(f"{subcloud_name} is managed; unmanaging before restore")
        DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, MANAGE_TIMEOUT)

    # 3. Local variant only: stage the preserved local backup for the seed to read.
    #    The remote variant restores from the System Controller's central backup,
    #    which is a prerequisite of the test plan; no extra precheck is done here.
    if local_only:
        _restore_preserved_local_backup(subcloud_name, subcloud_show.get_software_version())


def _restore_preserved_local_backup(subcloud_name: str, software_version: str) -> None:
    """Copy the custom-path local backup into the platform backup directory.

    The dashboard backup test creates the local backup with custom_path=True, which
    writes it to the subcloud home directory
    (/home/<user>/<subcloud_name>_platform_backup_*.tgz) rather than the default
    /opt/platform-backup/backups that the factory restore wipes. The onsite-restore
    seed reads the local backup from /opt/platform-backup/backups/<sw_version>/, so
    this helper copies the custom-path archive into that directory on the subcloud.

    Args:
        subcloud_name (str): Name of the target subcloud.
        software_version (str): Subcloud software version (platform backup subdir).

    Raises:
        Failed: Via pytest.fail if no custom-path backup archive is found.
    """
    subcloud_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    home_user = subcloud_config.get_admin_credentials().get_user_name()
    home_dir = f"/home/{home_user}/"
    platform_backup_dir = PLATFORM_BACKUP_DIR_TEMPLATE.format(sw_version=software_version)

    get_logger().log_setup_step(f"Copy custom-path local backup for {subcloud_name} from {home_dir} into {platform_backup_dir}")

    # The subcloud is at factory-restore baseline here (pre-trigger), so it is
    # reachable only on its factory IP/credentials, not the post-enroll admin ones.
    subcloud_ssh = LabConnectionKeywords().get_subcloud_factory_ssh(subcloud_name)
    subcloud_file_keywords = FileKeywords(subcloud_ssh)

    backup_archives = [name for name in subcloud_file_keywords.get_files_in_dir(home_dir) if name.startswith(f"{subcloud_name}_platform_backup_") and name.endswith(".tgz")]
    if not backup_archives:
        fail(f"No custom-path local backup ({home_dir}{subcloud_name}_platform_backup_*.tgz) found on {subcloud_name}; cannot run local onsite restore.")

    subcloud_file_keywords.create_directory_with_sudo(platform_backup_dir)
    subcloud_file_keywords.copy_file(f"{home_dir}{backup_archives[0]}", f"{platform_backup_dir}/", sudo=True)


def _record_onsite_restore_kpis(system_controller_ssh: SSHConnection, subcloud_name: str, variant: str) -> None:
    """Mine per-phase onsite-restore durations from the SC and subcloud logs and record them.

    The system controller drives the restore (restore_subcloud_backup.yml), so the
    phase markers are the task headers in the subcloud's ansible playbook log on the
    SC; the final alarm_clear phase stops on the subcloud's fm-manager.log. Mining is
    anchored at the last restore playbook start rather than a pre-restore line
    snapshot, because logrotate can rename the log mid-restore. Phases whose markers
    are not found are skipped, and nothing is recorded when the run has no KPI
    session or database.

    Args:
        system_controller_ssh (SSHConnection): SSH to the system controller.
        subcloud_name (str): Subcloud that was restored.
        variant (str): Restore variant tag for the KPIs ("remote" or "local").
    """
    system_controller_version = CloudPlatformVersionManager.get_sw_version().get_name()
    subcloud_version = _get_subcloud_software_version(system_controller_ssh, subcloud_name)

    ansible_log = ANSIBLE_PLAYBOOK_LOG_TEMPLATE.format(subcloud_name=subcloud_name)
    log_kpi = DcManagerLogKpiKeywords(system_controller_ssh, extra_logs={"ansible": ansible_log})
    since_line = log_kpi.anchor_since_last_session("ansible", ONSITE_RESTORE_SESSION_MARKER)

    # alarm_clear stops on the subcloud's own fm-manager.log. get_subcloud_ssh()
    # does not raise on a failed connect, so probe it; without a reachable
    # subcloud the miner skips alarm_clear and the SC phases still record.
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    if not subcloud_ssh.is_reachable():
        get_logger().log_info(f"{subcloud_name} is not reachable over SSH; skipping alarm_clear")
        subcloud_ssh = None
    durations = log_kpi.mine_phase_durations(subcloud_name, ONSITE_RESTORE_PHASES, since_line=since_line, subcloud_ssh=subcloud_ssh)
    DcKpiRecorderKeywords().record_phase_durations(
        durations,
        kpi_category="Backup_Restore",
        kpi_group="onsite_restore",
        name_prefix="onsite-restore",
        subcloud_version=subcloud_version,
        system_controller_version=system_controller_version,
        extra_details={"variant": variant, "reinstall": False},
    )


def _register_teardown(request: FixtureRequest, system_controller_ssh: SSHConnection, subcloud_name: str, software_version: str) -> None:
    """Register post-test cleanup for the onsite restore flow.

    Two independent finalizers are registered so a failure in one still lets the
    other run (pytest runs each registered finalizer regardless of earlier
    failures). They run in reverse registration order (LIFO):
      1. remove the SC seed build working directory,
      2. unstage the HTTPS-served seed ISO.

    The subcloud is intentionally left unmanaged: managing a restored subcloud is
    covered by its own test case, not this one.

    Unstaging is done only at teardown (after the test body has returned or raised,
    so the subcloud is no longer fetching the seed over HTTPS); unstaging
    mid-restore would break an in-progress restore.

    Args:
        request (FixtureRequest): The pytest request fixture.
        system_controller_ssh (SSHConnection): SSH to the active System Controller.
        subcloud_name (str): Name of the target subcloud.
        software_version (str): Subcloud software version (locates the staged ISO).
    """

    def unstage_seed_iso() -> None:
        """Unstage the seed ISO from the SC HTTPS tree."""
        get_logger().log_teardown_step(f"Unstage seed ISO for {subcloud_name}")
        SeedIsoStagingKeywords(system_controller_ssh).unstage_seed_iso(subcloud_name, software_version)

    def remove_seed_work_dir() -> None:
        """Remove the SC seed build working directory."""
        get_logger().log_teardown_step(f"Remove onsite-restore seed working dir for {subcloud_name}")
        SeedIsoBuilderKeywords(system_controller_ssh).cleanup(subcloud_name)

    # Registered in reverse of the intended run order (finalizers run LIFO). Each is
    # independent: a failure in one does not prevent the other from running.
    request.addfinalizer(unstage_seed_iso)
    request.addfinalizer(remove_seed_work_dir)


def _run_onsite_restore(request: FixtureRequest, local_only: bool) -> None:
    """Execute the onsite restore without reinstall flow and post-restore checks.

    Args:
        request (FixtureRequest): The pytest request fixture.
        local_only (bool): True for the local-backup variant; False for remote/central.
    """
    # Select the simplex subcloud from config and the system controller that owns
    # it. Using the picker's fallback (rather than always the active SC) lets this
    # run in rehome-capable labs where the subcloud may live on the secondary SC.
    # No availability/backup_status filter is applied: the factory-installed target
    # is offline in dcmanager when this runs, so filtering on ONLINE would exclude it.
    system_controller_ssh, pick_result = SubcloudPickerKeywords.pick_with_fallback(present_in_config=True, lab_type=LabTypeEnum.SIMPLEX)
    subcloud_name = pick_result.get_name()

    _run_onsite_restore_prechecks(system_controller_ssh, subcloud_name, local_only)

    software_version = _get_subcloud_software_version(system_controller_ssh, subcloud_name)
    _register_teardown(request, system_controller_ssh, subcloud_name, software_version)

    # Build seed -> stage to HTTPS -> mount via RVMC -> monitor -> validate online/health.
    get_logger().log_test_case_step(f"Run onsite restore without reinstall on {subcloud_name} (local_only={local_only}) and validate it")
    DcManagerOnsiteRestoreKeywords(system_controller_ssh).onsite_restore_without_reinstall(subcloud_name, local_only)

    # The subcloud is intentionally NOT managed here: managing a restored subcloud is
    # covered by its own test case.
    get_logger().log_test_case_step(f"Record onsite restore KPIs for {subcloud_name}")
    _record_onsite_restore_kpis(system_controller_ssh, subcloud_name, variant="local" if local_only else "remote")


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_onsite_restore_without_reinstall_remote(request: FixtureRequest) -> None:
    """Onsite restore without reinstall from the central (remote) backup.

    Test Steps:
        - Ensure the subcloud exists in dcmanager and is unmanaged.
        - Build the onsite-restore seed ISO (local_only=false).
        - Stage the seed ISO on the SC HTTPS tree.
        - Mount the seed ISO via RVMC (boot override and power-off excluded).
        - Monitor the restore to deploy_status=complete and availability=online.
        - Validate cluster health.
        - Record per-phase restore KPIs.

    Teardown:
        - Remove the seed working dir and unstage the seed ISO (subcloud left
          unmanaged; managing is covered by a separate test case).
    """
    _run_onsite_restore(request, local_only=False)


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_onsite_restore_without_reinstall_local(request: FixtureRequest) -> None:
    """Onsite restore without reinstall from the subcloud's local backup.

    Test Steps:
        - Ensure the subcloud exists in dcmanager and is unmanaged.
        - Copy the preserved local backup into the subcloud platform backup dir.
        - Build the onsite-restore seed ISO (local_only=true).
        - Stage the seed ISO on the SC HTTPS tree.
        - Mount the seed ISO via RVMC (boot override and power-off excluded).
        - Monitor the restore to deploy_status=complete and availability=online.
        - Validate cluster health.
        - Record per-phase restore KPIs.

    Teardown:
        - Remove the seed working dir and unstage the seed ISO (subcloud left
          unmanaged; managing is covered by a separate test case).
    """
    _run_onsite_restore(request, local_only=True)
