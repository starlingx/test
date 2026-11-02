import os
from typing import Callable, List

from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords import DcManagerSubcloudStateWatcherKeywords
from keywords.cloud_platform.dcmanager.enroll_config import EnrollConfig
from keywords.cloud_platform.dcmanager.subcloud_enroll_config_keywords import SubcloudEnrollConfigKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.kpi.dc_kpi_recorder_keywords import DcKpiRecorderKeywords
from keywords.cloud_platform.kpi.dcmanager_log_kpi_keywords import DCMANAGER_ENROLL_PHASES, DcManagerLogKpiKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager
from keywords.files.file_keywords import FileKeywords

# Deploy statuses that mean the enroll failed; the state watcher fail-fasts on
# any of these instead of waiting out the full timeout.
ENROLL_FAILED_STATES = [
    "bootstrap-failed",
    "install-failed",
    "create-failed",
    "config-failed",
    "pre-enroll-failed",
    "enroll-failed",
    "pre-init-enroll-failed",
    "init-enroll-failed",
    "rehome-failed",
]

FACTORY_INSTALL_COMPLETE_MARKER = "/var/lib/factory-install/complete"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _default_enroll_config(subcloud_name: str) -> EnrollConfig:
    """Read a subcloud's default (N) enroll config paths from deployment assets.

    Args:
        subcloud_name (str): Subcloud name.

    Returns:
        EnrollConfig: The subcloud's default bootstrap/install/deploy paths.
    """
    assets = ConfigurationManager.get_deployment_assets_config().get_subcloud_deployment_assets(subcloud_name)
    return EnrollConfig(
        bootstrap_values=assets.get_bootstrap_file(),
        install_values=assets.get_install_file(),
        deploy_config_file=assets.get_deployment_config_file(),
    )


def _wait_for_enroll_online(system_controller_ssh: SSHConnection, subcloud_name: str) -> None:
    """Wait for the enroll to complete, then for the subcloud to come online.

    Uses the on-change watcher so the output is a clean timeline (one line per
    state transition) rather than a status printed every poll. Each stage
    fail-fasts on a failed state.

    Args:
        system_controller_ssh (SSHConnection): SSH to the system controller.
        subcloud_name (str): Subcloud being enrolled.
    """
    watcher = DcManagerSubcloudStateWatcherKeywords(system_controller_ssh)
    watcher.watch_single_subcloud_log_on_change(subcloud_name, field_to_watch="deploy_status", complete_state="complete", failed_states=ENROLL_FAILED_STATES, timeout=4800)
    watcher.watch_single_subcloud_log_on_change(subcloud_name, field_to_watch="availability", complete_state="online", failed_states=["offline"], timeout=900)


def _record_enroll_kpis(system_controller_ssh: SSHConnection, subcloud_name: str, since_line: dict, jcnr: bool, release_delta: str) -> None:
    """Mine per-phase enroll durations from the SC logs and record them.

    Best-effort: a parse/record failure is logged and never fails the test. The
    enrolled subcloud's load and the system controller's load are both captured
    (they differ for an N-1 enroll), and the variant is tagged.

    Args:
        system_controller_ssh (SSHConnection): SSH to the system controller.
        subcloud_name (str): Subcloud that was enrolled.
        since_line (dict): Pre-enroll log line offsets (so only this run is mined).
        jcnr (bool): Whether this was a JCNR enroll (KPI tag).
        release_delta (str): Release delta relative to the SC ("N", "N-1", "N-2").
    """
    system_controller_version = CloudPlatformVersionManager.get_sw_version().get_name()
    subcloud_version = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    durations = DcManagerLogKpiKeywords(system_controller_ssh).mine_phase_durations(subcloud_name, DCMANAGER_ENROLL_PHASES, since_line=since_line)
    DcKpiRecorderKeywords().record_phase_durations(
        durations,
        kpi_category="Enrollment",
        kpi_group="dcmanager_enroll",
        name_prefix="dcmanager-enroll",
        subcloud_version=subcloud_version,
        system_controller_version=system_controller_version,
        extra_details={"jcnr": jcnr, "variant": "remote", "release_delta": release_delta},
    )


def _make_delete_file_finalizer(ssh_connection: SSHConnection, file_path: str) -> Callable[[], None]:
    """Build a finalizer that deletes a remote file, binding the path per call.

    Used inside a loop so each iteration's file is captured in its own closure
    rather than by late-binding a shared loop variable.

    Args:
        ssh_connection (SSHConnection): SSH connection to the host holding the file.
        file_path (str): Absolute path of the file to delete at teardown.

    Returns:
        Callable[[], None]: A no-arg finalizer suitable for request.addfinalizer.
    """

    def _finalizer() -> None:
        get_logger().log_info(f"Removing file: {file_path}")
        FileKeywords(ssh_connection).delete_file(file_path)

    return _finalizer


def _configured_subcloud_names() -> List[str]:
    """Return every subcloud declared in the loaded lab config.

    Tests loop over this set rather than taking index 0, so a lab config that
    declares more than one subcloud enrolls every one of them instead of
    silently operating on only the lowest-numbered.

    Returns:
        List[str]: Subcloud names in config order.
    """
    return ConfigurationManager.get_lab_config().get_subcloud_names()


def _enroll_and_record_kpis(subcloud_name: str, enroll_config: EnrollConfig, jcnr: bool = False, cloud_init_config: str = None, release: str = None, release_delta: str = "N") -> None:
    """Enroll one SX subcloud and record its per-phase enrollment KPIs.

    Shared by the standard, N-1/N-2 and JCNR/vCSR enroll tests. They differ only
    in the resolved config paths and the extra enroll args (JCNR adds
    --cloud-init-config; N-1/N-2 adds --release); the flow, phases and recorder
    are identical. Factory-readiness is a precondition checked by
    test_verify_subcloud_factory_ready, sequenced before these tests.

    Args:
        subcloud_name (str): Subcloud to enroll.
        enroll_config (EnrollConfig): Resolved bootstrap/install/deploy paths.
        jcnr (bool): True for a JCNR/vCSR enroll (KPI tag). Defaults to False.
        cloud_init_config (str): Path to the cloud-init-config tarball for JCNR.
        release (str): N-1/N-2 release (e.g. "26.03"), passed as --release.
        release_delta (str): Release delta tag for KPIs ("N", "N-1", "N-2").
            Defaults to "N".
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Snapshot SC log positions before enroll so only this run's lines are mined.
    kpi_log_kw = DcManagerLogKpiKeywords(system_controller_ssh)
    since_line = {
        "dcmanager": kpi_log_kw.snapshot_log_line_count("dcmanager"),
        "state": kpi_log_kw.snapshot_log_line_count("state"),
    }

    get_logger().log_test_case_step(f"Enrolling {subcloud_name}")
    DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll(
        subcloud_name=subcloud_name,
        bootstrap_values=enroll_config.bootstrap_values,
        install_values=enroll_config.install_values,
        deploy_config_file=enroll_config.deploy_config_file,
        cloud_init_config=cloud_init_config,
        release=release,
    )

    _wait_for_enroll_online(system_controller_ssh, subcloud_name)
    _record_enroll_kpis(system_controller_ssh, subcloud_name, since_line, jcnr, release_delta)

    get_logger().log_test_case_step(f"Post-enroll health check on {subcloud_name}")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

    get_logger().log_test_case_step(f"Managing {subcloud_name}")
    DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)


def create_fake_bootstrap_values(bootstrap_values: str, ssh_connection: SSHConnection) -> str:
    """Copy bootstrap-values and mangle the docker_registries block to force a failure.

    Used by the retry test to provoke an enroll-failed state.

    Args:
        bootstrap_values (str): Path to the original bootstrap-values file.
        ssh_connection (SSHConnection): SSH connection to the system controller.

    Returns:
        str: Path to the fake bootstrap-values file on the remote host.
    """
    dir_name = os.path.dirname(bootstrap_values)
    base_name = os.path.basename(bootstrap_values)
    fake_bootstrap_values = os.path.join(dir_name, f"fake_{base_name}")

    file_keywords = FileKeywords(ssh_connection)
    local_temp_file = f"/tmp/{base_name}"
    file_keywords.download_file(bootstrap_values, local_temp_file)

    modified_lines = []
    skip_registry_block = False
    with open(local_temp_file, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("docker_registries:"):
                skip_registry_block = True
                modified_lines.append("docker_registries:\n")
                modified_lines.append("  k8s.gcr.io:\n")
                modified_lines.append("    url: registry.central:9001/k8s.gcr.io\n")
                modified_lines.append("    username: someuser\n")
                continue
            if skip_registry_block:
                if line.startswith(" ") or line.startswith("\t"):
                    continue
                skip_registry_block = False
            modified_lines.append(line)

    with open(local_temp_file, "w") as f:
        f.writelines(modified_lines)

    file_keywords.upload_file(local_temp_file, fake_bootstrap_values)
    os.remove(local_temp_file)
    return fake_bootstrap_values


def run_enroll_operations(system_controller_ssh: SSHConnection, subcloud_name: str, bootstrap_values: str, install_values: str, deployment_config_file: str, phased: bool = False) -> None:
    """Run a subcloud enroll via dcmanager (used by the retry / factory-restore tests).

    Args:
        system_controller_ssh (SSHConnection): SSH to the system controller.
        subcloud_name (str): Subcloud to enroll.
        bootstrap_values (str): Path to the bootstrap-values file.
        install_values (str): Path to the install-values file.
        deployment_config_file (str): Path to the deploy-config file.
        phased (bool): Run the phased enroll+config flow instead of the single add.
    """
    if phased:
        deploy_kw = DCManagerSubcloudDeployKeywords(system_controller_ssh)
        get_logger().log_test_case_step(f"Enrolling {subcloud_name}")
        deploy_kw.dcmanager_subcloud_enroll(subcloud_name)
        get_logger().log_test_case_step(f"Configuring {subcloud_name}")
        deploy_kw.dcmanager_subcloud_deploy_config(subcloud_name)
        return

    missing = [name for name, value in {"bootstrap_values": bootstrap_values, "install_values": install_values, "deployment_config_file": deployment_config_file}.items() if value is None]
    if missing:
        fail(f"The following required parameters are None: {', '.join(missing)}")
    DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll(
        subcloud_name=subcloud_name,
        bootstrap_values=bootstrap_values,
        install_values=install_values,
        deploy_config_file=deployment_config_file,
    )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
@mark.p2
@mark.lab_has_subcloud
def test_enroll_one_sx_subcloud():
    """Execute a standard (N) subcloud enroll and record enrollment KPIs.

    Enrolls every subcloud declared in the lab config. Assumes the subclouds are
    factory-ready (see test_verify_subcloud_factory_ready).
    """
    for subcloud_name in _configured_subcloud_names():
        _enroll_and_record_kpis(subcloud_name, _default_enroll_config(subcloud_name))


@mark.p2
@mark.lab_has_subcloud
def test_enroll_n_minus_1_sx_subcloud():
    """Execute an N-1 subcloud enroll (subcloud one major release behind the SC).

    Same flow as the standard enroll, but passes --release for the N-1 load and
    reads the release-specific configs in place; the default configs are left
    unchanged. KPIs are tagged release_delta=N-1.

    Enrolls every subcloud declared in the lab config. Assumes the subclouds are
    factory-ready and that the N-1 configs are staged on the system controller.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    n_minus_1_release = CloudPlatformVersionManager.resolve_release_token("N-1")

    for subcloud_name in _configured_subcloud_names():
        default_config = _default_enroll_config(subcloud_name)
        enroll_config = SubcloudEnrollConfigKeywords(system_controller_ssh).resolve_for_release(default_config, n_minus_1_release)
        _enroll_and_record_kpis(subcloud_name, enroll_config, release=n_minus_1_release, release_delta="N-1")


@mark.p2
@mark.lab_has_subcloud
def test_enroll_n_minus_2_sx_subcloud():
    """Execute an N-2 subcloud enroll (subcloud two major releases behind the SC).

    Same as the N-1 case but two majors back: passes --release for the N-2 load
    and reads the release-specific configs in place. KPIs are tagged
    release_delta=N-2.

    Enrolls every subcloud declared in the lab config. Assumes the subclouds are
    factory-ready and that the N-2 configs are staged on the system controller.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    n_minus_2_release = CloudPlatformVersionManager.resolve_release_token("N-2")

    for subcloud_name in _configured_subcloud_names():
        default_config = _default_enroll_config(subcloud_name)
        enroll_config = SubcloudEnrollConfigKeywords(system_controller_ssh).resolve_for_release(default_config, n_minus_2_release)
        _enroll_and_record_kpis(subcloud_name, enroll_config, release=n_minus_2_release, release_delta="N-2")


@mark.p2
@mark.lab_has_subcloud
def test_enroll_jcnr_sx_subcloud(request):
    """Execute a JCNR/vCSR subcloud enroll and record enrollment KPIs.

    Same flow as the standard enroll, but passes the extra --cloud-init-config
    tarball (JCNR configlet, secret and apply script) and tags the KPIs jcnr=true.
    A JCNR subcloud has a different network identity than its standard counterpart,
    so it is described by its own lab config; the JCNR addresses and config files
    come from that config's deployment assets.

    Enrolls every subcloud declared in the lab config. Assumes the subclouds are
    factory-ready (see test_verify_subcloud_factory_ready).
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_add_keywords = DcManagerSubcloudAddKeywords(system_controller_ssh)
    # The build dir holds the secret with the encoded sysadmin password; remove it
    # after the test regardless of outcome (one build dir, reused per subcloud).
    request.addfinalizer(subcloud_add_keywords.cleanup_jcnr_cloud_init_config)

    for subcloud_name in _configured_subcloud_names():
        assets = ConfigurationManager.get_deployment_assets_config().get_subcloud_deployment_assets(subcloud_name)
        cloud_init_config_dir = assets.get_cloud_init_config_dir()
        configlet_file = assets.get_cloud_init_configlet_file()
        if not cloud_init_config_dir or not configlet_file:
            fail(f"JCNR cloud-init-config not configured for {subcloud_name} (need cloud_init_config_dir and cloud_init_configlet_file in the JCNR lab's deployment_assets).")

        enroll_config = EnrollConfig(
            bootstrap_values=assets.get_bootstrap_file(),
            install_values=assets.get_install_file(),
            deploy_config_file=assets.get_deployment_config_file(),
        )

        # Assemble the cloud-init-config tarball: overlay this subcloud's configlet
        # on the generic bundle and inject the base64 sysadmin password.
        get_logger().log_test_case_step(f"Assembling JCNR cloud-init-config for {subcloud_name}")
        sysadmin_password = lab_config.get_subcloud(subcloud_name).get_admin_credentials().get_password()
        cloud_init_config = subcloud_add_keywords.build_jcnr_cloud_init_config(cloud_init_config_dir, configlet_file, sysadmin_password)

        _enroll_and_record_kpis(subcloud_name, enroll_config, jcnr=True, cloud_init_config=cloud_init_config)


@mark.p2
@mark.lab_has_subcloud
def test_retry_enroll_one_sx_subcloud(request):
    """Enroll with a bad bootstrap file, confirm it fails, then enroll successfully.

    Runs for every subcloud declared in the lab config.

    Test Steps:
        - Validate the subcloud is factory-installed.
        - Enroll with an invalid bootstrap file and verify enroll-failed.
        - Delete the subcloud and re-enroll with the valid config.
    """
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    for subcloud_name in _configured_subcloud_names():
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

        get_logger().log_test_case_step(f"Verify {subcloud_name} completed factory-install")
        if not FileKeywords(subcloud_ssh).file_exists(FACTORY_INSTALL_COMPLETE_MARKER):
            fail("This subcloud was not factory installed, unable to proceed with enroll.")

        get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
        HealthKeywords(subcloud_ssh).validate_healty_cluster()

        assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        bootstrap_values = assets.get_bootstrap_file()
        install_values = assets.get_install_file()
        deployment_config_file = assets.get_deployment_config_file()

        fake_bootstrap_values = create_fake_bootstrap_values(bootstrap_values, system_controller_ssh)
        request.addfinalizer(_make_delete_file_finalizer(system_controller_ssh, fake_bootstrap_values))

        run_enroll_operations(system_controller_ssh, subcloud_name, fake_bootstrap_values, install_values, deployment_config_file)
        DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name, status="enroll-failed")
        DcManagerSubcloudDeleteKeywords(system_controller_ssh).dcmanager_subcloud_delete(subcloud_name)

        run_enroll_operations(system_controller_ssh, subcloud_name, bootstrap_values, install_values, deployment_config_file)
        DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name, status="complete")
        DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_availability_status(subcloud_name)
        DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

        get_logger().log_info(f"Performing post-enrollment checks on {subcloud_name}")
        HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p2
@mark.lab_has_subcloud
def test_enroll_sx_subcloud_after_factory_restore(request):
    """Enroll a subcloud after restoring it to factory state.

    Runs for every subcloud declared in the lab config.

    Test Steps:
        - Validate the subcloud is in the subcloud list; unmanage if managed.
        - Restore the subcloud to factory state.
        - Enroll (phased) and validate it comes online.
    """
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    dcm_sc_list_kw = DcManagerSubcloudListKeywords(system_controller_ssh)
    dc_manager_backup = DcManagerSubcloudBackupKeywords(system_controller_ssh)

    for subcloud_name in _configured_subcloud_names():
        subcloud_list = dcm_sc_list_kw.get_dcmanager_subcloud_list()
        if not subcloud_list.is_subcloud_in_output(subcloud_name):
            fail(f"{subcloud_name} not in subcloud list.")

        subcloud_show_obj = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object()
        if subcloud_show_obj.get_management() == "managed":
            get_logger().log_test_case_step(f"Unmanaging {subcloud_name} before restore")
            DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)

        subcloud_password = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name).get_admin_credentials().get_password()

        restore_values = f"/home/sysadmin/restore_values_{subcloud_name}.yml"
        FileKeywords(system_controller_ssh).create_file_with_echo(restore_values, "ipmi_sel_event_monitoring: false")
        request.addfinalizer(_make_delete_file_finalizer(system_controller_ssh, restore_values))

        assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        bootstrap_values = assets.get_bootstrap_file()
        install_values = assets.get_install_file()
        deployment_config_file = assets.get_deployment_config_file()

        get_logger().log_test_case_step(f"Restoring subcloud factory backup: {subcloud_name}")
        dc_manager_backup.restore_subcloud_backup(subcloud_password, system_controller_ssh, subcloud=subcloud_name, factory=True, restore_values_path=restore_values, timeout=7200)

        run_enroll_operations(system_controller_ssh, subcloud_name, bootstrap_values, install_values, deployment_config_file, phased=True)

        get_logger().log_test_case_step("Waiting for subcloud to unlock.")
        dcm_sc_list_kw.validate_subcloud_availability_status(subcloud_name)

        get_logger().log_info(f"Performing post-enrollment checks on {subcloud_name}")
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        HealthKeywords(subcloud_ssh).validate_healty_cluster()

        DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)
