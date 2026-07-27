from pytest import mark

from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_kube_deploy_strategy_keywords import DcmanagerKubeStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords


# --- Helper Functions ---


def cleanup_strategy(ssh_connection: SSHConnection) -> None:
    """Delete kube-upgrade-strategy if it exists.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
    """
    get_logger().log_teardown_step("Delete kube-upgrade-strategy")
    DcmanagerStrategyCleanupKeywords(ssh_connection).cleanup_strategy("kube-upgrade")


def get_active_kube_version(ssh_connection: SSHConnection) -> str:
    """Get the active Kubernetes version from the system controller.

    For DC kube-upgrade to N release, the target is the active K8s version
    on the system controller. The subcloud should be upgraded to match it.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.

    Returns:
        str: Active Kubernetes version (e.g. "v1.35.2").
    """
    kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    active_versions = kube_keywords.get_kubernetes_versions_by_state("active")
    validate_equals(len(active_versions) > 0, True, "Active Kubernetes version found on system controller")
    target = max(active_versions)
    get_logger().log_info(f"System controller active K8s version: {target}")
    return target


def run_kube_upgrade_strategy(system_controller_ssh: SSHConnection, subcloud_name: str, kube_version: str = None) -> None:
    """Create, apply, and verify kube-upgrade-strategy for a subcloud.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud to target.
        kube_version (str): Target K8s version. If None, dcmanager auto-resolves.
    """
    strategy_keywords = DcmanagerKubeStrategyKeywords(system_controller_ssh)

    get_logger().log_info(f"Creating kube-upgrade-strategy for subcloud {subcloud_name}" + (f" targeting {kube_version}" if kube_version else ""))
    strategy_keywords.dcmanager_kube_upgrade_strategy_create(subcloud=subcloud_name, kube_version=kube_version)

    get_logger().log_info("Applying kube-upgrade-strategy")
    strategy_keywords.dcmanager_kube_upgrade_strategy_apply()

    get_logger().log_info("Deleting kube-upgrade-strategy")
    strategy_keywords.dcmanager_kube_strategy_delete()


# --- Single Simplex Subcloud ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_kube_upgrade_strategy_single_simplex_subcloud_n_release(request):
    """Verify kube-upgrade-strategy for a simplex subcloud running N release.

    Targets the system controller's active K8s version to bring the subcloud
    in sync.

    Test Steps:
        1. Resolve active K8s version from system controller
        2. Create kube-upgrade-strategy targeting the subcloud with that version
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        load="N",
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    kube_version = get_active_kube_version(system_controller_ssh)
    run_kube_upgrade_strategy(system_controller_ssh, subcloud_name, kube_version=kube_version)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_kube_upgrade_strategy_single_simplex_subcloud_n_minus_1_release(request):
    """Verify kube-upgrade-strategy for a simplex subcloud running N-1 release.

    Test Steps:
        1. Create kube-upgrade-strategy targeting the subcloud
        2. Apply the strategy
        3. Validate strategy completes
        4. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        load="N-1",
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    run_kube_upgrade_strategy(system_controller_ssh, subcloud_name)


# --- Single Duplex Subcloud ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_kube_upgrade_strategy_single_duplex_subcloud_n_release(request):
    """Verify kube-upgrade-strategy for a duplex subcloud running N release.

    Targets the system controller's active K8s version to bring the subcloud
    in sync.

    Test Steps:
        1. Resolve active K8s version from system controller
        2. Create kube-upgrade-strategy targeting the subcloud with that version
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        load="N",
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    kube_version = get_active_kube_version(system_controller_ssh)
    run_kube_upgrade_strategy(system_controller_ssh, subcloud_name, kube_version=kube_version)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_kube_upgrade_strategy_single_duplex_subcloud_n_minus_1_release(request):
    """Verify kube-upgrade-strategy for a duplex subcloud running N-1 release.

    Test Steps:
        1. Create kube-upgrade-strategy targeting the subcloud
        2. Apply the strategy
        3. Validate strategy completes
        4. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        load="N-1",
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    run_kube_upgrade_strategy(system_controller_ssh, subcloud_name)
