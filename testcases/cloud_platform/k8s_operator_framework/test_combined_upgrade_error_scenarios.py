"""Validate combined upgrade error scenarios for system-deploy init and sw-deploy-strategy.

Prerequisites:
- Lab must have a release available for deployment (e.g., release_version).
- The system must be in a state where system-deploy init can be attempted.
- The system must have an active Kubernetes version with at least one lower version.
- For test_deploy_start_rejected_when_kube_control_plane_upgrade_incomplete: at least 2 major
  Kubernetes versions must be available between the running version and the target version.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_not_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_create_config import SwManagerSwDeployStrategyCreateConfig
from keywords.cloud_platform.swmanager.swmanager_sw_deploy_strategy_keywords import SwManagerSwDeployStrategyKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords


def get_lower_kube_version(ssh_connection: SSHConnection) -> str:
    """Retrieve a Kubernetes version lower than the currently active one.

    Queries 'system kube-version-list' to find the active version, then
    returns the highest version that is numerically lower.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: A Kubernetes version lower than the active version (e.g., 'v1.30.6').

    Raises:
        KeywordException: If no lower version is found in the version list.
    """
    kube_version_output = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list()
    lower_version = kube_version_output.get_highest_version_lower_than_active()
    get_logger().log_info(f"Highest Kubernetes version lower than active: {lower_version}")
    return lower_version


def get_inexistent_kube_version(ssh_connection: SSHConnection) -> str:
    """Generate a Kubernetes version that does not exist on the system.

    Queries 'system kube-version-list' to find the greatest version, then
    increments its minor version by 2 to produce a version guaranteed
    not to exist.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: A non-existent Kubernetes version (e.g., 'v1.37.2' if highest is 'v1.35.2').
    """
    kube_version_output = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list()
    greatest_version = kube_version_output.get_highest_kubernetes_version()
    get_logger().log_info(f"Greatest Kubernetes version: {greatest_version}")

    parts = greatest_version.lstrip("v").split(".")
    parts[1] = str(int(parts[1]) + 2)
    inexistent_version = f"v{'.'.join(parts)}"
    get_logger().log_info(f"Generated inexistent Kubernetes version: {inexistent_version}")
    return inexistent_version


@mark.p1
@mark.lab_is_simplex
def test_system_deploy_init_rejects_inexistent_kube_version() -> None:
    """Test that system-deploy init rejects an inexistent kube version.

    Verifies that 'software system-deploy init' returns an error when
    an non-existent Kubernetes version is specified via the
    --kube-upgrade flag.

    Test Steps:
        - Get active controller SSH connection
        - Execute 'software system-deploy init <release_version> --kube-upgrade <kube_version>'
          using USMKeywords and validate the command is rejected
        - Validate the error output contains the invalid version

    Raises:
        AssertionError: If the command succeeds unexpectedly or error message is wrong.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    inexistent_kube_version = get_inexistent_kube_version(ssh_connection)
    get_logger().log_setup_step("Get available software release")
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    available_release = software_list.get_release_name_by_state("available")
    validate_not_equals(available_release, [], "At least one release in 'available' state must exist")
    release = available_release[0]
    usm_keywords = USMKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Execute system-deploy init with invalid kube version '{inexistent_kube_version}'")
    error_output = usm_keywords.system_deploy_init_with_error(release=release, kube_upgrade=inexistent_kube_version)
    get_logger().log_info(f"system-deploy init error output:\n{error_output}")
    validate_str_contains(
        error_output,
        inexistent_kube_version,
        "Error output references the invalid kube version",
    )


@mark.p1
@mark.lab_is_simplex
def test_system_deploy_init_rejects_lower_kube_version() -> None:
    """Test that system-deploy init rejects a lower Kubernetes version.

    Verifies that 'software system-deploy init' returns an error when
    a Kubernetes version lower than the currently active one is specified
    via the --kube-upgrade flag.

    Test Steps:
        - Get active controller SSH connection
        - Retrieve available Kubernetes versions via 'system kube-version-list'
        - Determine the active version and select a lower version
        - Execute 'software system-deploy init' with the lower kube version
          and validate the command is rejected
        - Validate the error output contains the lower version

    Raises:
        AssertionError: If the command succeeds unexpectedly or error message is wrong.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    release = software_list.get_release_name_by_state("available")[0]
    lower_kube_version = get_lower_kube_version(ssh_connection)
    usm_keywords = USMKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Execute system-deploy init with lower kube version '{lower_kube_version}'")
    error_output = usm_keywords.system_deploy_init_with_error(release=release, kube_upgrade=lower_kube_version)
    get_logger().log_info(f"system-deploy init error output:\n{error_output}")
    validate_str_contains(
        error_output,
        lower_kube_version,
        "Error output references the lower kube version",
    )


@mark.p1
@mark.lab_is_simplex
def test_sw_deploy_strategy_create_build_failed_inexistent_kube_version(request: FixtureRequest) -> None:
    """Test that sw-deploy-strategy create results in build-failed for an invalid kube version.

    Verifies that 'sw-manager sw-deploy-strategy create' with an invalid
    Kubernetes version results in a strategy with state 'build-failed' and
    build-reason indicating the inexistent version.

    Test Steps:
        - Get active controller SSH connection
        - Create sw-deploy-strategy with inexistent kube version <kube_version>
        - Run 'sw-manager sw-deploy-strategy show' and validate state is 'build-failed'
        - Validate build-reason contains "Invalid to_version value: '<kube_version>'"
        - Delete the failed strategy in teardown

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If the strategy does not reach build-failed state or
            the build-reason does not match the expected error.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    inexistent_kube_version = get_inexistent_kube_version(ssh_connection)
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    release = software_list.get_release_name_by_state("available")[0]
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)

    def teardown() -> None:
        """Delete the sw-deploy-strategy if it exists."""
        get_logger().log_teardown_step("Delete sw-deploy-strategy")
        try:
            sw_deploy_strategy_keywords.get_sw_deploy_strategy_delete()
        except Exception:
            get_logger().log_info("No strategy to delete")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Create sw-deploy-strategy with invalid kube version '{inexistent_kube_version}'")
    config = SwManagerSwDeployStrategyCreateConfig(
        release=release,
        kube_upgrade=inexistent_kube_version,
    )
    sw_deploy_strategy_keywords.get_sw_deploy_strategy_create(config)
    sw_deploy_strategy_keywords.wait_for_state(["build-failed"])

    get_logger().log_test_case_step("Validate build-reason contains expected error message")
    strategy = sw_deploy_strategy_keywords.get_sw_deploy_strategy_show().get_swmanager_sw_deploy_strategy_show()
    build_reason = strategy.get_build_reason()
    get_logger().log_info(f"Strategy build-reason: {build_reason}")
    validate_str_contains(
        build_reason,
        f"Invalid to_version value: '{inexistent_kube_version}'",
        "Build-reason indicates the specified kube version is invalid",
    )


@mark.p1
@mark.lab_is_simplex
def test_sw_deploy_strategy_create_build_failed_lower_kube_version(request: FixtureRequest) -> None:
    """Test that sw-deploy-strategy create results in build-failed for a lower kube version.

    Verifies that 'sw-manager sw-deploy-strategy create' with a Kubernetes
    version lower than the currently active one results in a strategy with
    state 'build-failed' and build-reason indicating the version is invalid.

    Test Steps:
        - Get active controller SSH connection
        - Retrieve available Kubernetes versions via 'system kube-version-list'
        - Determine the active version and select a lower version
        - Create sw-deploy-strategy with the lower kube version
        - Run 'sw-manager sw-deploy-strategy show' and validate state is 'build-failed'
        - Validate build-reason contains error indicating the version is invalid
        - Delete the failed strategy in teardown

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If the strategy does not reach build-failed state or
            the build-reason does not match the expected error.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    release = software_list.get_release_name_by_state("available")[0]
    lower_kube_version = get_lower_kube_version(ssh_connection)
    sw_deploy_strategy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)

    def teardown() -> None:
        """Delete the sw-deploy-strategy if it exists."""
        get_logger().log_teardown_step("Delete sw-deploy-strategy")
        try:
            sw_deploy_strategy_keywords.get_sw_deploy_strategy_delete()
        except Exception:
            get_logger().log_info("No strategy to delete")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Create sw-deploy-strategy with lower kube version '{lower_kube_version}'")
    config = SwManagerSwDeployStrategyCreateConfig(
        release=release,
        kube_upgrade=lower_kube_version,
    )
    sw_deploy_strategy_keywords.get_sw_deploy_strategy_create(config)
    sw_deploy_strategy_keywords.wait_for_state(["build-failed"])

    get_logger().log_test_case_step("Validate build-reason contains expected error message")
    strategy = sw_deploy_strategy_keywords.get_sw_deploy_strategy_show().get_swmanager_sw_deploy_strategy_show()
    build_reason = strategy.get_build_reason()
    get_logger().log_info(f"Strategy build-reason: {build_reason}")
    validate_str_contains(
        build_reason,
        "Kubernetes target version cannot be unavailable",
        "Build-reason indicates the specified lower kube version is invalid",
    )


@mark.p1
@mark.lab_is_simplex
def test_deploy_start_rejected_when_kube_control_plane_upgrade_incomplete(request: FixtureRequest) -> None:
    """Test that software deploy start is rejected when K8s control-plane upgrade is incomplete.

    Verifies that 'software deploy start' is rejected when a Kubernetes
    upgrade has been initiated and control-plane upgrade completed but not for the specified kubernetes version.
    The system should block the deploy because the kube upgrade target version does not match
    the system-deploy to_k8s_version.

    Note:
        This test requires at least 2 major Kubernetes versions between
        the running version and the target version to run correctly.

    Test Steps:
        - Get active controller SSH connection
        - Execute 'software system-deploy init <release_version> --kube-upgrade <kube_version>'
        - Execute 'system kube-upgrade-start <kube_version>'
        - Execute 'system kube-upgrade-download-images' and wait for completion
        - Execute 'system kube-pre-application-update' and wait for completion
        - Execute 'system kube-upgrade-networking' and wait for completion
        - Execute 'system kube-upgrade-storage' and wait for completion
        - Execute 'system kube-host-upgrade controller-0 control-plane' and wait for completion
        - Execute 'software deploy start' and validate it is rejected with an error
        - Validate error contains message about Kubernetes upgrade blocking deployment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If the deploy start command succeeds unexpectedly.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kube_version_output = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list()
    target_kube_version = kube_version_output.get_highest_version_by_state("available")
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    release = software_list.get_release_name_by_state("available")[0]
    usm_keywords = USMKeywords(ssh_connection)
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)

    host = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    def teardown_kube_upgrade() -> None:
        """Abort and delete Kubernetes upgrade if needed."""
        get_logger().log_teardown_step("Abort and delete Kubernetes upgrade if needed")
        try:
            kube_upgrade_keywords.kube_upgrade_abort()
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=300)
            kube_upgrade_keywords.kube_upgrade_delete()
        except Exception:
            get_logger().log_info("No Kubernetes upgrade to clean up")

    def teardown_system_deploy() -> None:
        """Delete system-deploy if needed."""
        get_logger().log_teardown_step("Delete system-deploy if needed")
        try:
            usm_keywords.system_deploy_delete()
        except Exception:
            get_logger().log_info("No system-deploy to delete")

    request.addfinalizer(teardown_system_deploy)
    request.addfinalizer(teardown_kube_upgrade)

    get_logger().log_test_case_step(f"Execute system-deploy init with release={release} kube_version={target_kube_version}")
    usm_keywords.system_deploy_init(release=release, kube_upgrade=target_kube_version)

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_kube_version}")
    kube_upgrade_keywords.kube_upgrade_start(target_kube_version)

    get_logger().log_test_case_step("Download Kubernetes images")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "downloaded-images",
        timeout=600,
        failure_states=["downloading-images-failed"],
    )

    get_logger().log_test_case_step("Run kube-pre-application-update")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updated-apps",
        timeout=600,
        failure_states=["pre-updating-apps-failed"],
    )

    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-networking",
        timeout=600,
        failure_states=["upgrading-networking-failed"],
    )

    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-storage",
        timeout=600,
        failure_states=["upgrading-storage-failed"],
    )

    get_logger().log_test_case_step(f"Upgrade control-plane on {host}")
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(host)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-first-master",
        timeout=600,
        failure_states=["upgrading-first-master-failed"],
    )

    get_logger().log_test_case_step("Execute 'software deploy start' and expect rejection")
    error_output = usm_keywords.deploy_start_with_error(targets=release)
    get_logger().log_info(f"Deploy start error output:\n{error_output}")
    validate_str_contains(
        error_output,
        "Kubernetes upgrade does not block deployment: [Fail]",
        "Deploy start rejected due to incomplete Kubernetes upgrade",
    )
