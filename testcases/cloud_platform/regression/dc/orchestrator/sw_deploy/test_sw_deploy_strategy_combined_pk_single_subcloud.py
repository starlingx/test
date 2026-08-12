"""Combined Platform & Kubernetes sw-deploy-strategy tests for DC subclouds.

This module validates the dcmanager sw-deploy-strategy with --kube-upgrade flag,
which performs a combined platform and Kubernetes upgrade on subclouds in a single
orchestrated operation. It also covers prestage and snapshot scenarios.

Supported modes:
    - Upgrade: --kube-upgrade [version] --release-id [release] --with-delete
    - Upgrade with prestage: adds --with-prestage
    - Upgrade with prestage + snapshot: adds --with-prestage --snapshot (no --with-delete)

Requirements change: Combined P&K upgrade is supported on both simplex AND duplex
subclouds (previously simplex-only).

Test execution:
    - test_combined_pk_sw_deploy_strategy_single_simplex_subcloud_n_release
    - test_combined_pk_sw_deploy_strategy_single_duplex_subcloud_n_release
    - test_combined_pk_sw_deploy_strategy_with_prestage_single_simplex_subcloud_n_release
    - test_combined_pk_sw_deploy_strategy_with_prestage_single_duplex_subcloud_n_release
    - test_combined_pk_sw_deploy_strategy_with_prestage_snapshot_single_simplex_subcloud_n_release
    - test_combined_pk_sw_deploy_strategy_with_prestage_snapshot_single_duplex_subcloud_n_release

Prerequisites:
    - System controller has N release deployed
    - Target K8s version available on system controller (state=available)
    - Subcloud is online and out-of-sync
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass


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
        str: The highest release name matching the load (e.g. "WRCP-26.03.200").
    """
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    releases = software_list.get_release_name_by_state(state)
    matching = [r for r in releases if load in r]
    validate_equals(len(matching) > 0, True, f"Release found matching load '{load}' in state '{state}'")
    return max(matching)


def get_target_kube_version(ssh_connection: SSHConnection) -> str:
    """Resolve the target Kubernetes version for combined P&K upgrade on DC.

    For distributed cloud, the target K8s version is the active version on the
    system controller. The combined strategy upgrades the subcloud's K8s to match
    the system controller.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.

    Returns:
        str: Target Kubernetes version (e.g. "v1.35.2").
    """
    kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    active_versions = kube_keywords.get_kubernetes_versions_by_state("active")
    validate_equals(len(active_versions) > 0, True, "Active Kubernetes version found on system controller")
    target = max(active_versions)
    get_logger().log_info(f"Resolved target K8s version (system controller active): {target}")
    return target


def run_combined_pk_sw_deploy_strategy(
    system_controller_ssh: SSHConnection,
    subcloud_name: str,
    release: str = None,
    kube_version: str = None,
    with_delete: bool = True,
    with_prestage: bool = False,
    snapshot: bool = False,
) -> None:
    """Create, apply, and verify combined P&K sw-deploy-strategy for a subcloud.

    Unified helper that handles all combined P&K strategy modes:
        - Upgrade: provide release and kube_version
        - Upgrade with prestage: set with_prestage=True
        - Upgrade with prestage + snapshot: set with_prestage=True, snapshot=True

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud to target.
        release (str): Full release name to deploy (e.g. "WRCP-26.10").
        kube_version (str): Target Kubernetes version (e.g. "v1.29.2").
        with_delete (bool): If True, adds --with-delete flag. Defaults to True.
        with_prestage (bool): If True, adds --with-prestage flag.
        snapshot (bool): If True, adds --snapshot flag.
    """
    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    # Build description for logging
    mode_parts = []
    mode_parts.append(f"release={release}, kube-upgrade={kube_version}")
    if with_prestage:
        mode_parts.append("with-prestage")
    if snapshot:
        mode_parts.append("snapshot")
    mode_desc = ", ".join(mode_parts)

    # Build create kwargs
    create_kwargs = {
        "subcloud_name": subcloud_name,
        "with_delete": with_delete,
        "snapshot": snapshot,
        "release": release,
        "kube_upgrade": kube_version,
    }
    if with_prestage:
        create_kwargs["with_prestage"] = True
        create_kwargs["sysadmin_password"] = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()

    # Create strategy
    get_logger().log_info(f"Creating combined P&K sw-deploy-strategy for subcloud {subcloud_name} [{mode_desc}]")
    strategy_keywords.dcmanager_sw_deploy_strategy_create(**create_kwargs)

    # Apply the strategy
    get_logger().log_info(f"Applying combined P&K sw-deploy-strategy [{mode_desc}]")
    strategy_keywords.dcmanager_sw_deploy_strategy_apply(target=subcloud_name)

    # Verify strategy step completed
    strategy_status = (
        DcmanagerStrategyStepKeywords(system_controller_ssh)
        .get_dcmanager_strategy_step_show(subcloud_name)
        .get_dcmanager_strategy_step_show()
        .get_state()
    )
    validate_equals(strategy_status, "complete", f"Combined P&K strategy step completed for subcloud {subcloud_name} [{mode_desc}]")

    # Verify subcloud deploy status is complete
    subcloud = (
        DcManagerSubcloudListKeywords(system_controller_ssh)
        .get_dcmanager_subcloud_list()
        .get_subcloud_by_name(subcloud_name)
    )
    validate_equals(subcloud.get_deploy_status(), "complete", f"Subcloud {subcloud_name} deploy status should be complete [{mode_desc}]")

    # Delete strategy
    get_logger().log_info("Deleting sw-deploy-strategy")
    strategy_keywords.dcmanager_sw_deploy_strategy_delete()


# --- Combined P&K SW Deploy Strategy Upgrade Tests ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_sw_deploy_strategy_single_simplex_subcloud_n_release(request):
    """Verify combined P&K sw-deploy-strategy targeting N release on a simplex subcloud.

    Creates a sw-deploy-strategy with --kube-upgrade targeting both platform
    and Kubernetes upgrade in a single orchestrated operation on a simplex
    subcloud.

    Preconditions:
        - System controller has N release deployed
        - Target K8s version is available on system controller
        - Subcloud is online and out-of-sync

    Setup:
        - Pick eligible simplex subcloud
        - Resolve target release and K8s version

    Test Steps:
        1. Resolve target N release from software list
        2. Resolve target K8s version from kube-version-list
        3. Create sw-deploy-strategy with --kube-upgrade for the subcloud
        4. Apply the strategy
        5. Validate strategy step completes
        6. Validate subcloud deploy status is complete

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    get_logger().log_info(f"Target N release resolved to: {release}")

    kube_version = get_target_kube_version(system_controller_ssh)

    run_combined_pk_sw_deploy_strategy(system_controller_ssh, subcloud_name, release, kube_version)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_combined_pk_sw_deploy_strategy_single_duplex_subcloud_n_release(request):
    """Verify combined P&K sw-deploy-strategy targeting N release on a duplex subcloud.

    Creates a sw-deploy-strategy with --kube-upgrade targeting both platform
    and Kubernetes upgrade in a single orchestrated operation on a duplex
    subcloud. This validates the requirement change that combined P&K upgrade
    is now supported on duplex subclouds (previously simplex-only).

    Preconditions:
        - System controller has N release deployed
        - Target K8s version is available on system controller
        - Subcloud is online and out-of-sync

    Setup:
        - Pick eligible duplex subcloud
        - Resolve target release and K8s version

    Test Steps:
        1. Resolve target N release from software list
        2. Resolve target K8s version from kube-version-list
        3. Create sw-deploy-strategy with --kube-upgrade for the subcloud
        4. Apply the strategy
        5. Validate strategy step completes
        6. Validate subcloud deploy status is complete

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    get_logger().log_info(f"Target N release resolved to: {release}")

    kube_version = get_target_kube_version(system_controller_ssh)

    run_combined_pk_sw_deploy_strategy(system_controller_ssh, subcloud_name, release, kube_version)


# --- Combined P&K SW Deploy Strategy with Prestage Tests ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_sw_deploy_strategy_with_prestage_single_simplex_subcloud_n_release(request):
    """Verify combined P&K sw-deploy-strategy with --with-prestage on a simplex subcloud.

    Creates a sw-deploy-strategy with --kube-upgrade and --with-prestage, performing
    prestage, platform upgrade, and Kubernetes upgrade in a single orchestrated
    operation on a simplex subcloud.

    Preconditions:
        - System controller has N release deployed
        - Target K8s version is active on system controller
        - Subcloud is online and out-of-sync

    Setup:
        - Pick eligible simplex subcloud
        - Resolve target release and K8s version

    Test Steps:
        1. Resolve target N release from software list
        2. Resolve target K8s version from kube-version-list (system controller active)
        3. Create sw-deploy-strategy with --kube-upgrade --with-prestage for the subcloud
        4. Apply the strategy
        5. Validate strategy step completes
        6. Validate subcloud deploy status is complete

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    get_logger().log_info(f"Target N release resolved to: {release}")

    kube_version = get_target_kube_version(system_controller_ssh)

    run_combined_pk_sw_deploy_strategy(system_controller_ssh, subcloud_name, release, kube_version, with_prestage=True)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_combined_pk_sw_deploy_strategy_with_prestage_single_duplex_subcloud_n_release(request):
    """Verify combined P&K sw-deploy-strategy with --with-prestage on a duplex subcloud.

    Creates a sw-deploy-strategy with --kube-upgrade and --with-prestage, performing
    prestage, platform upgrade, and Kubernetes upgrade in a single orchestrated
    operation on a duplex subcloud.

    Preconditions:
        - System controller has N release deployed
        - Target K8s version is active on system controller
        - Subcloud is online and out-of-sync

    Setup:
        - Pick eligible duplex subcloud
        - Resolve target release and K8s version

    Test Steps:
        1. Resolve target N release from software list
        2. Resolve target K8s version from kube-version-list (system controller active)
        3. Create sw-deploy-strategy with --kube-upgrade --with-prestage for the subcloud
        4. Apply the strategy
        5. Validate strategy step completes
        6. Validate subcloud deploy status is complete

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    get_logger().log_info(f"Target N release resolved to: {release}")

    kube_version = get_target_kube_version(system_controller_ssh)

    run_combined_pk_sw_deploy_strategy(system_controller_ssh, subcloud_name, release, kube_version, with_prestage=True)


# --- Combined P&K SW Deploy Strategy with Prestage + Snapshot Tests ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_sw_deploy_strategy_with_prestage_snapshot_single_simplex_subcloud_n_release(request):
    """Verify combined P&K sw-deploy-strategy with --with-prestage --snapshot on a simplex subcloud.

    Creates a sw-deploy-strategy with --kube-upgrade, --with-prestage, and --snapshot,
    performing upgrade with snapshot, platform upgrade, and Kubernetes upgrade in a
    single orchestrated operation on a simplex subcloud. The --snapshot flag instructs
    the system to take a snapshot of the subcloud before applying the upgrade.

    Preconditions:
        - System controller has N release deployed
        - Target K8s version is active on system controller
        - Subcloud is online and out-of-sync

    Setup:
        - Pick eligible simplex subcloud
        - Resolve target release and K8s version

    Test Steps:
        1. Resolve target N release from software list
        2. Resolve target K8s version from kube-version-list (system controller active)
        3. Create sw-deploy-strategy with --kube-upgrade --with-prestage --snapshot
        4. Apply the strategy
        5. Validate strategy step completes
        6. Validate subcloud deploy status is complete

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    get_logger().log_info(f"Target N release resolved to: {release}")

    kube_version = get_target_kube_version(system_controller_ssh)

    run_combined_pk_sw_deploy_strategy(system_controller_ssh, subcloud_name, release, kube_version, with_prestage=True, with_delete=False, snapshot=True)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_combined_pk_sw_deploy_strategy_with_prestage_snapshot_single_duplex_subcloud_n_release(request):
    """Verify combined P&K sw-deploy-strategy with --with-prestage --snapshot on a duplex subcloud.

    Creates a sw-deploy-strategy with --kube-upgrade, --with-prestage, and --snapshot,
    performing upgrade with snapshot, platform upgrade, and Kubernetes upgrade in a
    single orchestrated operation on a duplex subcloud. The --snapshot flag instructs
    the system to take a snapshot of the subcloud before applying the upgrade.

    Preconditions:
        - System controller has N release deployed
        - Target K8s version is active on system controller
        - Subcloud is online and out-of-sync

    Setup:
        - Pick eligible duplex subcloud
        - Resolve target release and K8s version

    Test Steps:
        1. Resolve target N release from software list
        2. Resolve target K8s version from kube-version-list (system controller active)
        3. Create sw-deploy-strategy with --kube-upgrade --with-prestage --snapshot
        4. Apply the strategy
        5. Validate strategy step completes
        6. Validate subcloud deploy status is complete

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    get_logger().log_info(f"Target N release resolved to: {release}")

    kube_version = get_target_kube_version(system_controller_ssh)

    run_combined_pk_sw_deploy_strategy(system_controller_ssh, subcloud_name, release, kube_version, with_prestage=True, with_delete=False, snapshot=True)
