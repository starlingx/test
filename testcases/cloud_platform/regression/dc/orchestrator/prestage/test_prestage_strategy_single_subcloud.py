from pytest import mark

from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_prestage_strategy_keywords import DcmanagerPrestageStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass


# --- Helper Functions ---


def cleanup_strategy(ssh_connection: SSHConnection) -> None:
    """Delete prestage-strategy if it exists.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
    """
    get_logger().log_teardown_step("Delete prestage-strategy")
    DcmanagerStrategyCleanupKeywords(ssh_connection).cleanup_strategy("prestage")


def run_prestage_strategy(system_controller_ssh: SSHConnection, subcloud_name: str, release: str = None, for_sw_deploy: bool = True) -> None:
    """Create, apply, and verify prestage-strategy for a subcloud.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud to target.
        release (str): Release version to pass to the strategy.
        for_sw_deploy (bool): Use --for-sw-deploy flag. False = for-install.
    """
    strategy_keywords = DcmanagerPrestageStrategyKeywords(system_controller_ssh)

    get_logger().log_info(f"Creating prestage-strategy for subcloud {subcloud_name} (release={release}, for_sw_deploy={for_sw_deploy})")
    strategy_keywords.get_dcmanager_prestage_strategy_create(
        release=release,
        sw_deploy=for_sw_deploy,
        subcloud_name=subcloud_name,
    )

    get_logger().log_info("Applying prestage-strategy")
    result = strategy_keywords.get_dcmanager_prestage_strategy_apply()
    validate_equals(result.get_state(), "complete", f"Prestage strategy for subcloud {subcloud_name} should complete successfully")

    get_logger().log_info("Deleting prestage-strategy")
    strategy_keywords.get_dcmanager_prestage_strategy_delete()


# --- Prestage Strategy for Install (simplex) ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_prestage_strategy_single_simplex_subcloud_for_install_n_release(request):
    """Verify prestage-strategy for-install with N release on a simplex subcloud.

    Test Steps:
        1. Create prestage-strategy (for-install, no --release)
        2. Apply the strategy
        3. Validate strategy completes
        4. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    run_prestage_strategy(system_controller_ssh, subcloud_name, for_sw_deploy=False)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_prestage_strategy_single_simplex_subcloud_for_install_n_minus_1_release(request):
    """Verify prestage-strategy for-install with N-1 release on a simplex subcloud.

    Test Steps:
        1. Resolve N-1 release version
        2. Create prestage-strategy (for-install, --release N-1)
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    run_prestage_strategy(system_controller_ssh, subcloud_name, release=n_minus_1_release, for_sw_deploy=False)


# --- Prestage Strategy for SW Deploy (simplex) ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_prestage_strategy_single_simplex_subcloud_for_sw_deploy_n_release(request):
    """Verify prestage-strategy --for-sw-deploy with N release on a simplex subcloud.

    Test Steps:
        1. Create prestage-strategy (--for-sw-deploy, no --release)
        2. Apply the strategy
        3. Validate strategy completes
        4. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    run_prestage_strategy(system_controller_ssh, subcloud_name, for_sw_deploy=True)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_prestage_strategy_single_simplex_subcloud_for_sw_deploy_n_minus_1_release(request):
    """Verify prestage-strategy --for-sw-deploy with N-1 release on a simplex subcloud.

    Test Steps:
        1. Resolve N-1 release version
        2. Create prestage-strategy (--for-sw-deploy, --release N-1)
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    run_prestage_strategy(system_controller_ssh, subcloud_name, release=n_minus_1_release, for_sw_deploy=True)


# --- Prestage Strategy for Install (duplex) ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_prestage_strategy_single_duplex_subcloud_for_install_n_release(request):
    """Verify prestage-strategy for-install with N release on a duplex subcloud.

    Test Steps:
        1. Create prestage-strategy (for-install, no --release)
        2. Apply the strategy
        3. Validate strategy completes
        4. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    run_prestage_strategy(system_controller_ssh, subcloud_name, for_sw_deploy=False)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_prestage_strategy_single_duplex_subcloud_for_install_n_minus_1_release(request):
    """Verify prestage-strategy for-install with N-1 release on a duplex subcloud.

    Test Steps:
        1. Resolve N-1 release version
        2. Create prestage-strategy (for-install, --release N-1)
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    run_prestage_strategy(system_controller_ssh, subcloud_name, release=n_minus_1_release, for_sw_deploy=False)


# --- Prestage Strategy for SW Deploy (duplex) ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_prestage_strategy_single_duplex_subcloud_for_sw_deploy_n_release(request):
    """Verify prestage-strategy --for-sw-deploy with N release on a duplex subcloud.

    Test Steps:
        1. Create prestage-strategy (--for-sw-deploy, no --release)
        2. Apply the strategy
        3. Validate strategy completes
        4. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    run_prestage_strategy(system_controller_ssh, subcloud_name, for_sw_deploy=True)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_prestage_strategy_single_duplex_subcloud_for_sw_deploy_n_minus_1_release(request):
    """Verify prestage-strategy --for-sw-deploy with N-1 release on a duplex subcloud.

    Test Steps:
        1. Resolve N-1 release version
        2. Create prestage-strategy (--for-sw-deploy, --release N-1)
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    run_prestage_strategy(system_controller_ssh, subcloud_name, release=n_minus_1_release, for_sw_deploy=True)
