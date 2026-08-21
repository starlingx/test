"""Combined Platform & Kubernetes sw-deploy-strategy abort / auto-rollback tests.

This module validates abort and auto-rollback scenarios for the combined P&K
sw-deploy-strategy on DC subclouds, and the --cleanup path used to restore a
subcloud after an auto-rollback.

Background:
    The happy-path automation for combined P&K sw-deploy-strategy is covered
    elsewhere. This module covers abort/auto-rollback scenarios, validating
    dcmanager behavior when the combined P&K strategy fails or is aborted at
    different levels.

Test cases:
    - test_combined_pk_auto_rollback_kube_cp_failure: inject a K8S control
      plane failure during kube-host-upgrade-control-plane, verify the subcloud
      VIM auto-aborts, dcmanager detects the failure, and K8S reverts to the
      original version.
    - test_combined_pk_dcmanager_abort_queued_subclouds: abort the dcmanager
      strategy mid-apply with multiple subclouds queued; verify the executing
      subcloud continues and queued subclouds are cancelled.
    - test_combined_pk_cleanup_after_auto_rollback: after an auto-rollback,
      run dcmanager --cleanup to verify leftovers (aborted kube-upgrade +
      system-deploy) are cleaned up.

Notes:
    - Fault injection blocks the Kubernetes API server port (16443) via ip6tables
      on the subcloud during the control-plane upgrade. This is reliable and
      reproducible and does NOT require --snapshot (the ETCD snapshot is taken
      automatically by VIM; the abort happens before platform deploy-host).
    - The --cleanup path depends on the VIM fix that handles the upgrade-aborted
      state (skip kube-upgrade-complete, go directly to kube-upgrade-delete +
      system-deploy-delete). On loads without that fix, --cleanup fails at
      kube-upgrade-complete.
"""

import time

from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords, pick_subcloud_with_fallback
from keywords.cloud_platform.linux.iptables_fault_injection_keywords import IptablesFaultInjectionKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass

# --- Constants ---

# Kubernetes API server port blocked to fail the control-plane upgrade.
KUBE_APISERVER_PORT = 16443

# Expected kube-upgrade state after a successful auto-rollback.
KUBE_UPGRADE_ABORTED_STATE = "upgrade-aborted"

# Time (seconds) allowed for the subcloud strategy-step to begin applying after
# apply is issued.
STRATEGY_STEP_START_TIMEOUT = 900

# Time (seconds) allowed for the subcloud to progress through prestage + software
# deploy and reach the Kubernetes control-plane upgrade phase. Prestage alone can
# take a long time, so this is deliberately generous.
CONTROL_PLANE_PHASE_TIMEOUT = 5400


# --- Helper Functions ---


def cleanup_strategy(ssh_connection: SSHConnection) -> None:
    """Delete sw-deploy-strategy if it exists.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
    """
    get_logger().log_teardown_step("Delete sw-deploy-strategy")
    DcmanagerStrategyCleanupKeywords(ssh_connection).cleanup_strategy("sw-deploy")


def get_highest_release_for_load(ssh_connection: SSHConnection, load: str, state: str = "deployed") -> str:
    """Get the highest release version matching a load prefix from software list.

    Args:
        ssh_connection (SSHConnection): SSH connection to query software list.
        load (str): Load prefix to match (e.g. "26.03" or "25.09").
        state (str): Release state to filter by (e.g. "deployed", "unavailable").

    Returns:
        str: The highest release name matching the load (e.g. "starlingx-26.03.200").
    """
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    releases = software_list.get_release_name_by_state(state)
    matching = [r for r in releases if load in r]
    validate_equals(len(matching) > 0, True, f"Release found matching load '{load}' in state '{state}'")
    return max(matching)


def get_target_kube_version(ssh_connection: SSHConnection) -> str:
    """Resolve the target Kubernetes version (active version on system controller).

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.

    Returns:
        str: Target Kubernetes version (e.g. "v1.35.2").
    """
    active_versions = SystemKubernetesListKeywords(ssh_connection).get_kubernetes_versions_by_state("active")
    validate_equals(len(active_versions) > 0, True, "Active Kubernetes version found on system controller")
    target = max(active_versions)
    get_logger().log_info(f"Resolved target K8s version (system controller active): {target}")
    return target


def get_sysadmin_password() -> str:
    """Return the sysadmin password from the lab config.

    Returns:
        str: The sysadmin password used for prestage and sudo commands.
    """
    return ConfigurationManager.get_lab_config().get_admin_credentials().get_password()


def create_combined_pk_strategy_apply_no_wait(
    strategy_keywords: DcmanagerSwDeployStrategy,
    subcloud_name: str,
    release: str,
    kube_version: str,
) -> None:
    """Create a combined P&K strategy (with prestage, no delete) and apply without waiting.

    Per the auto-rollback scenario, the strategy uses --with-prestage and does NOT
    use --with-delete (a snapshot-capable path is needed and the ETCD snapshot is
    taken automatically). Apply is issued without waiting so a fault can be injected
    while the control-plane upgrade is in progress.

    Args:
        strategy_keywords (DcmanagerSwDeployStrategy): Strategy keyword instance.
        subcloud_name (str): Target subcloud name.
        release (str): Target release id.
        kube_version (str): Target Kubernetes version.
    """
    get_logger().log_test_case_step(f"Create combined P&K strategy for {subcloud_name} [release={release}, kube-upgrade={kube_version}, with-prestage]")
    strategy_keywords.dcmanager_sw_deploy_strategy_create(
        subcloud_name=subcloud_name,
        release=release,
        kube_upgrade=kube_version,
        with_prestage=True,
        sysadmin_password=get_sysadmin_password(),
        with_delete=False,
    )

    get_logger().log_test_case_step("Apply combined P&K strategy (without waiting for completion)")
    strategy_keywords.dcmanager_sw_deploy_strategy_apply(target=subcloud_name, wait_completion=False)


def wait_for_control_plane_phase_or_step_failure(
    system_controller_ssh: SSHConnection,
    subcloud_ssh: SSHConnection,
    subcloud_name: str,
    hostname: str,
    timeout: int,
    polling_sleep_time: int = 15,
) -> None:
    """Wait for the subcloud to enter the K8s control-plane upgrade phase.

    A combined P&K apply progresses through prestage and software deploy before
    the Kubernetes control-plane upgrade begins, so this can take a long time.
    The subcloud host status is polled for 'upgrading-control-plane'.

    Fails fast if the dcmanager strategy-step reaches 'failed' before the
    control-plane phase is reached (e.g. the VIM strategy build fails, or the
    apply errors during prestage/software deploy). Without this, the wait would
    spin uselessly against a host status that stays empty until the full timeout.

    Args:
        system_controller_ssh (SSHConnection): SSH to the system controller.
        subcloud_ssh (SSHConnection): SSH to the target subcloud.
        subcloud_name (str): Target subcloud name.
        hostname (str): Subcloud host to watch (controller-0 for AIO-SX).
        timeout (int): Maximum time (seconds) to wait for the control-plane phase.
        polling_sleep_time (int): Interval (seconds) between polls.

    Raises:
        KeywordException: If the dcmanager strategy-step fails before the
            control-plane phase is reached.
        TimeoutError: If neither the control-plane phase nor a step failure is
            observed within the timeout.
    """
    kube_host_kw = KubeHostUpgradeListKeywords(subcloud_ssh)
    step_kw = DcmanagerStrategyStepKeywords(system_controller_ssh)
    end_time = time.time() + timeout

    while True:
        # The host may not appear in kube-host-upgrade-list until the kube phase
        # begins, so guard with is_hostname_in_list before reading its status.
        host_list = kube_host_kw.kube_host_upgrade_list()
        host_status = None
        if host_list.is_hostname_in_list(hostname):
            host_status = host_list.get_host_upgrade_by_hostname(hostname).get_status()
        if host_status == "upgrading-control-plane":
            get_logger().log_info(f"{subcloud_name}/{hostname} reached control-plane upgrade phase")
            return

        step = step_kw.get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show()
        step_state = step.get_state()
        if step_state == "failed":
            details = step.get_details() or ""
            raise KeywordException(f"dcmanager strategy-step for {subcloud_name} failed before reaching the control-plane phase: {details}")

        if time.time() >= end_time:
            raise TimeoutError(f"Timed out waiting for {subcloud_name}/{hostname} to reach 'upgrading-control-plane' (last host status: {host_status}, step state: {step_state})")

        time.sleep(polling_sleep_time)


# --- Scenario 1: Subcloud VIM Auto-Rollback (Primary) ---


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_auto_rollback_kube_cp_failure(request):
    """Verify subcloud VIM auto-rollback on K8S control-plane upgrade failure.

    Injects a Kubernetes control-plane upgrade failure during the combined P&K
    upgrade (by blocking the API server port on the subcloud), then verifies the
    subcloud VIM auto-aborts, dcmanager detects the failure, and K8S reverts to
    the original version. Platform remains unchanged (no deploy-host occurred).

    Preconditions:
        - System controller has N release deployed
        - Target K8s version is available on system controller
        - Subcloud is online and out-of-sync

    Test Steps:
        1. Pick an eligible simplex subcloud and resolve release + K8s version
        2. Record the subcloud's original K8s control-plane/kubelet versions
        3. Create combined P&K strategy (--with-prestage, no --with-delete)
        4. Apply without waiting
        5. Wait for the subcloud to enter the control-plane upgrade phase
        6. Inject fault: block the K8s API server port on the subcloud
        7. Wait for the subcloud kube-upgrade to reach upgrade-aborted
        8. Remove the fault-injection rule
        9. Validate dcmanager strategy-step reports the subcloud as failed
        10. Validate K8s reverted to the original CP + kubelet versions

    Teardown:
        - Remove the ip6tables rule (idempotent)
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.SIMPLEX,
    )
    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    fault_injection = IptablesFaultInjectionKeywords(subcloud_ssh)
    # Ensure the rule is always removed, even if the test fails mid-way.
    request.addfinalizer(lambda: fault_injection.unblock_port(KUBE_APISERVER_PORT))

    # Resolve release and target K8s version
    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    kube_version = get_target_kube_version(system_controller_ssh)

    # Record original K8s versions on the subcloud (controller-0 for AIO-SX)
    kube_host_kw = KubeHostUpgradeListKeywords(subcloud_ssh)
    original_host = kube_host_kw.kube_host_upgrade_list().get_kube_host_upgrade_list()[0]
    original_hostname = original_host.get_hostname()
    original_cp_version = original_host.get_control_plane_version()
    original_kubelet_version = original_host.get_kubelet_version()
    get_logger().log_info(f"Original K8s versions on {original_hostname}: CP={original_cp_version}, kubelet={original_kubelet_version}")

    # Create + apply strategy without waiting
    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)
    create_combined_pk_strategy_apply_no_wait(strategy_keywords, subcloud_name, release, kube_version)

    # Phase 1: confirm the subcloud strategy-step actually started applying. A
    # combined P&K apply progresses through prestage and software deploy before
    # the Kubernetes control-plane upgrade begins, so we gate on the dcmanager
    # strategy-step first rather than polling the (still-empty) kube-host list.
    get_logger().log_test_case_step("Wait for subcloud strategy-step to begin applying")
    strategy_step_kw = DcmanagerStrategyStepKeywords(system_controller_ssh)
    strategy_step_kw.wait_for_strategy_step_state(
        subcloud_name=subcloud_name,
        states=["applying", "complete", "failed"],
        timeout=STRATEGY_STEP_START_TIMEOUT,
        polling_sleep_time=15,
    )

    # Phase 2: wait for the subcloud to actually enter the control-plane upgrade
    # phase. This can take a long time because prestage + software deploy run
    # first. Fail fast if the dcmanager strategy-step fails before the
    # control-plane phase (e.g. the VIM strategy build fails), instead of
    # spinning against an empty host status until the full timeout.
    get_logger().log_test_case_step("Wait for subcloud to enter control-plane upgrade phase")
    wait_for_control_plane_phase_or_step_failure(
        system_controller_ssh=system_controller_ssh,
        subcloud_ssh=subcloud_ssh,
        subcloud_name=subcloud_name,
        hostname=original_hostname,
        timeout=CONTROL_PLANE_PHASE_TIMEOUT,
        polling_sleep_time=15,
    )

    get_logger().log_test_case_step(f"Inject fault: block K8s API server port {KUBE_APISERVER_PORT} on {subcloud_name}")
    fault_injection.block_port(KUBE_APISERVER_PORT)

    # Wait for the VIM auto-rollback to complete (kube-upgrade reaches upgrade-aborted)
    get_logger().log_test_case_step("Wait for subcloud kube-upgrade to reach upgrade-aborted (auto-rollback)")
    KubeUpgradeShowKeywords(subcloud_ssh).wait_for_kube_upgrade_state(
        expected_state=KUBE_UPGRADE_ABORTED_STATE,
        timeout=1800,
        polling_sleep_time=15,
    )

    # Remove the fault now that the abort has been triggered
    get_logger().log_test_case_step("Remove fault-injection rule")
    fault_injection.unblock_port(KUBE_APISERVER_PORT)

    # Validate dcmanager detected the failure and reported the subcloud step as failed
    get_logger().log_test_case_step("Validate dcmanager strategy-step reports subcloud as failed")
    strategy_step = DcmanagerStrategyStepKeywords(system_controller_ssh).wait_for_strategy_step_state(
        subcloud_name=subcloud_name,
        states=["failed"],
        timeout=600,
        polling_sleep_time=15,
    )
    validate_equals(strategy_step.get_state(), "failed", f"dcmanager strategy-step for {subcloud_name} is failed")

    # Validate K8s reverted to the original versions on the subcloud
    get_logger().log_test_case_step("Validate K8s reverted to original control-plane and kubelet versions")
    reverted_host = kube_host_kw.kube_host_upgrade_list().get_host_upgrade_by_hostname(original_hostname)
    validate_equals(
        reverted_host.get_control_plane_version(),
        original_cp_version,
        f"Subcloud {subcloud_name} control-plane version reverted to original",
    )
    validate_equals(
        reverted_host.get_kubelet_version(),
        original_kubelet_version,
        f"Subcloud {subcloud_name} kubelet version reverted to original",
    )


# --- Scenario 2: dcmanager Strategy Abort (queued subclouds) ---


@mark.p3
@mark.lab_has_min_2_subclouds
def test_combined_pk_dcmanager_abort_queued_subclouds(request):
    """Verify dcmanager abort mid-apply with multiple subclouds queued.

    Aborts the dcmanager strategy while applying across multiple subclouds. The
    currently-executing subcloud continues (its VIM strategy is not interrupted),
    while queued subclouds are cancelled and the dcmanager strategy reaches the
    aborted state.

    Preconditions:
        - Lab has at least two online subclouds
        - System controller has N release deployed

    Test Steps:
        1. Pick two or more eligible subclouds
        2. Create a combined P&K group strategy and apply without waiting
        3. Wait for the first subcloud step to begin executing
        4. Issue dcmanager sw-deploy-strategy abort
        5. Validate the executing subcloud runs to completion (not interrupted)
        6. Validate queued subclouds do not complete (cancelled)
        7. Validate the dcmanager strategy reaches the aborted state

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    subclouds = SubcloudPickerKeywords(system_controller_ssh).pick_all(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.SIMPLEX,
    )
    validate_equals(len(subclouds) >= 2, True, "At least two eligible subclouds available for queued-abort test")
    subcloud_names = [sc.get_name() for sc in subclouds]
    executing_subcloud = subcloud_names[0]
    queued_subclouds = subcloud_names[1:]
    get_logger().log_info(f"Executing subcloud: {executing_subcloud}; queued subclouds: {queued_subclouds}")

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    kube_version = get_target_kube_version(system_controller_ssh)

    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    # Create a system-wide strategy: omitting both a subcloud name and a group
    # tells dcmanager to build the strategy across every eligible
    # (managed/out-of-sync) subcloud. The orchestrator then applies to all of
    # them, which is what lets us abort while one subcloud is executing and the
    # rest are still queued.
    get_logger().log_test_case_step("Create combined P&K strategy across queued subclouds")
    strategy_keywords.dcmanager_sw_deploy_strategy_create(
        release=release,
        kube_upgrade=kube_version,
        with_prestage=True,
        sysadmin_password=get_sysadmin_password(),
        with_delete=False,
    )

    get_logger().log_test_case_step("Apply strategy (without waiting for completion)")
    strategy_keywords.dcmanager_sw_deploy_strategy_apply(target=executing_subcloud, wait_completion=False)

    # Wait for the first subcloud to begin executing before aborting.
    get_logger().log_test_case_step(f"Wait for executing subcloud {executing_subcloud} to start applying")
    strategy_step_kw = DcmanagerStrategyStepKeywords(system_controller_ssh)
    strategy_step_kw.wait_for_strategy_step_state(
        subcloud_name=executing_subcloud,
        states=["applying", "complete", "failed"],
        timeout=600,
        polling_sleep_time=10,
    )

    # Abort the dcmanager strategy.
    get_logger().log_test_case_step("Abort the dcmanager sw-deploy-strategy")
    strategy_keywords.dcmanager_sw_deploy_strategy_abort()

    # Executing subcloud continues to completion (VIM strategy is not interrupted).
    get_logger().log_test_case_step(f"Validate executing subcloud {executing_subcloud} runs to completion")
    executing_step = strategy_step_kw.wait_for_strategy_step_state(
        subcloud_name=executing_subcloud,
        states=["complete", "failed"],
        timeout=3600,
        polling_sleep_time=30,
    )
    validate_equals(
        executing_step.get_state(),
        "complete",
        f"Executing subcloud {executing_subcloud} completed and was not interrupted by abort",
    )

    # Queued subclouds are cancelled - they must not reach complete.
    get_logger().log_test_case_step("Validate queued subclouds were cancelled (not completed)")
    for queued in queued_subclouds:
        queued_state = strategy_step_kw.get_dcmanager_strategy_step_show(queued).get_dcmanager_strategy_step_show().get_state()
        get_logger().log_info(f"Queued subcloud {queued} strategy-step state: {queued_state}")
        validate_equals(
            queued_state != "complete",
            True,
            f"Queued subcloud {queued} was cancelled (state '{queued_state}' is not complete)",
        )


# --- Scenario 3: --cleanup After Auto-Rollback ---


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_cleanup_after_auto_rollback(request):
    """Verify dcmanager --cleanup restores a subcloud after auto-rollback.

    After a combined P&K auto-rollback leaves the subcloud with a kube-upgrade in
    upgrade-aborted state plus a leftover system-deploy entity, run dcmanager
    --cleanup and verify the leftovers are removed (kube-upgrade deleted,
    system-deploy deleted, alarms cleared).

    This depends on the VIM fix that handles the upgrade-aborted state in the
    --cleanup strategy build (skip kube-upgrade-complete, go directly to
    kube-upgrade-delete + system-deploy-delete).

    Preconditions:
        - System controller has N release deployed
        - Target K8s version is available on system controller
        - Subcloud is online and out-of-sync
        - VIM on the subcloud handles the upgrade-aborted state in --cleanup

    Test Steps:
        1. Pick an eligible simplex subcloud and resolve release + K8s version
        2. Trigger an auto-rollback (block API server port during control-plane)
        3. Confirm the subcloud kube-upgrade is in upgrade-aborted state
        4. Delete the failed dcmanager strategy
        5. Create a dcmanager --cleanup strategy and apply
        6. Validate --cleanup completes
        7. Validate kube-upgrade is no longer in progress on the subcloud

    Teardown:
        - Remove the ip6tables rule (idempotent)
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.SIMPLEX,
    )
    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    fault_injection = IptablesFaultInjectionKeywords(subcloud_ssh)
    request.addfinalizer(lambda: fault_injection.unblock_port(KUBE_APISERVER_PORT))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    kube_version = get_target_kube_version(system_controller_ssh)

    kube_host_kw = KubeHostUpgradeListKeywords(subcloud_ssh)
    original_hostname = kube_host_kw.kube_host_upgrade_list().get_kube_host_upgrade_list()[0].get_hostname()

    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    # Trigger the auto-rollback (same flow as scenario 1).
    create_combined_pk_strategy_apply_no_wait(strategy_keywords, subcloud_name, release, kube_version)

    # Wait for the control-plane upgrade phase, failing fast if the dcmanager
    # strategy-step reaches 'failed' before it (e.g. the VIM strategy build
    # fails). Without this the wait would spin against an empty host status
    # until the full timeout even when the deploy has already failed.
    get_logger().log_test_case_step("Wait for subcloud to enter control-plane upgrade phase")
    wait_for_control_plane_phase_or_step_failure(
        system_controller_ssh=system_controller_ssh,
        subcloud_ssh=subcloud_ssh,
        subcloud_name=subcloud_name,
        hostname=original_hostname,
        timeout=CONTROL_PLANE_PHASE_TIMEOUT,
        polling_sleep_time=15,
    )

    get_logger().log_test_case_step(f"Inject fault: block K8s API server port {KUBE_APISERVER_PORT} on {subcloud_name}")
    fault_injection.block_port(KUBE_APISERVER_PORT)

    get_logger().log_test_case_step("Wait for subcloud kube-upgrade to reach upgrade-aborted (auto-rollback)")
    kube_upgrade_kw = KubeUpgradeShowKeywords(subcloud_ssh)
    kube_upgrade_kw.wait_for_kube_upgrade_state(
        expected_state=KUBE_UPGRADE_ABORTED_STATE,
        timeout=1800,
        polling_sleep_time=15,
    )

    get_logger().log_test_case_step("Remove fault-injection rule")
    fault_injection.unblock_port(KUBE_APISERVER_PORT)

    # Delete the failed strategy before creating the --cleanup strategy.
    get_logger().log_test_case_step("Delete failed sw-deploy-strategy before cleanup")
    strategy_keywords.dcmanager_sw_deploy_strategy_delete()

    # Run dcmanager --cleanup.
    get_logger().log_test_case_step(f"Create and apply dcmanager --cleanup strategy for {subcloud_name}")
    strategy_keywords.dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, cleanup=True)
    strategy_keywords.dcmanager_sw_deploy_strategy_apply(target=subcloud_name)

    # Validate the strategy step completed.
    cleanup_step = DcmanagerStrategyStepKeywords(system_controller_ssh).get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show().get_state()
    validate_equals(cleanup_step, "complete", f"dcmanager --cleanup completed for {subcloud_name}")

    # Validate kube-upgrade is no longer in progress on the subcloud.
    get_logger().log_test_case_step("Validate kube-upgrade is no longer in progress after cleanup")
    validate_equals(
        kube_upgrade_kw.is_kube_upgrade_in_progress(),
        False,
        "Subcloud kube-upgrade cleared after --cleanup",
    )

    # Delete the cleanup strategy.
    get_logger().log_test_case_step("Delete --cleanup strategy")
    strategy_keywords.dcmanager_sw_deploy_strategy_delete()
