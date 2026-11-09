"""Fresh interface metrics across an N-1 or N-2 platform upgrade and rollback."""

from collections.abc import Callable

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords import APPLICATION_NAME, NodeInterfaceMetricsExporterKeywords
from keywords.cloud_platform.applications.node_interface_metrics_exporter_state import NodeInterfaceMetricsExporterState
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.interface_metrics_compatibility_keywords import InterfaceMetricsCompatibilityKeywords
from keywords.cloud_platform.upgrade.platform_upgrade_preparation_keywords import PlatformUpgradePreparationKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.standard_platform_upgrade_keywords import StandardPlatformUpgradeKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords


@mark.p2
def test_interface_metrics_upgrade_rollback(request: FixtureRequest) -> None:
    """Verify automatic exporter update, rollback and metrics on every node.

    Args:
        request (FixtureRequest): Pytest owner of ordered platform/app recovery.

    Test Steps:
        - Reject invalid targets, outstanding deployments and blocking alarms.
        - Capture original exporter state and register release-first recovery.
        - Prepare the configured target load, license and filesystems.
        - Upload/apply the bundled baseline exporter if necessary.
        - Scrape metrics against independent host interface inventory.
        - Upgrade through activation and verify app release, alarms and metrics.
        - Roll back and verify the exact baseline app version and fresh metrics.

    Teardown:
        - Restore the original exporter state only after platform recovery.

    Notes:
        The installed release selects N-1 or N-2; app_upgrade_compat.to_version
        selects the target. No manual application-update is performed. VF
        identity checks apply when the host inventory contains configured VFs.
        Supports AIO-SX, AIO-DX and Standard topologies. A standby controller,
        dedicated compute host and configured VFs are not mandatory.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    deploy = SoftwareDeploySequenceKeywords(ssh_connection)
    platform_upgrade = StandardPlatformUpgradeKeywords(ssh_connection)
    recovery = UpgradeRecoveryKeywords(ssh_connection, platform_upgrade=platform_upgrade)
    health = ApplicationHealthKeywords(ssh_connection)
    exporter = NodeInterfaceMetricsExporterKeywords(ssh_connection)
    compatibility = InterfaceMetricsCompatibilityKeywords(ssh_connection)
    state = NodeInterfaceMetricsExporterState(exporter)
    preparation = PlatformUpgradePreparationKeywords(ssh_connection)
    get_logger().log_test_case_step("Validate releases and initial platform health")
    from_version = deploy.get_running_release()
    to_version = ConfigurationManager.get_app_upgrade_compat_config().get_to_version()
    compatibility.validate_upgrade_releases(from_version, to_version)
    if deploy.get_current_deploy_state():
        raise KeywordException("Resolve the existing deployment before exporter compatibility setup")
    platform_upgrade.require_no_blocking_alarms()
    get_logger().log_test_case_step("Capture baseline and register recovery")
    baseline_package = compatibility.get_baseline_package(from_version)
    artifact = baseline_package.get_artifact()
    baseline_version = baseline_package.get_version()

    def register_exporter_recovery(restore: Callable[[], None]) -> None:
        """Register app restoration guarded by successful platform recovery.

        Args:
            restore (Callable[[], None]): Original application state restorer.
        """

        def restore_after_platform_recovery() -> None:
            """Restore the application only after the baseline platform is recovered."""
            if deploy.get_running_release() != from_version or deploy.get_current_deploy_state():
                raise KeywordException("Platform recovery is incomplete; preserve exporter state until the deployment is recovered")
            restore()

        request.addfinalizer(restore_after_platform_recovery)

    state.capture(register_exporter_recovery, artifact)
    # Pytest finalizers run in reverse: restore the platform before the app.
    request.addfinalizer(lambda: recovery.restore_to_release(from_version))
    get_logger().log_info(f"Exporter compatibility: {from_version} -> {to_version} -> {from_version}")
    get_logger().log_test_case_step("Prepare target load, license and filesystems")
    preparation.prepare(to_version)
    get_logger().log_test_case_step("Prepare the baseline exporter")
    if exporter.application_state() is None:
        exporter.upload(artifact, baseline_version)
    if exporter.application_state() != (baseline_version, "applied"):
        exporter.apply()
    health.wait_for_app_applied(APPLICATION_NAME)
    validate_equals(exporter.application_state(), (baseline_version, "applied"), "exporter is applied at the baseline version")
    get_logger().log_test_case_step("Verify baseline metrics on participating nodes")
    baseline_nodes = compatibility.validate_metrics("pre")

    get_logger().log_test_case_step("Upgrade and verify exporter compatibility")
    preparation.require_precheck(to_version)
    platform_upgrade.upgrade_platform_in_order(deploy, to_version, leave_at_activate_done=True)
    validate_equals(deploy.get_running_release(), to_version, "platform is on the target release")
    health.wait_for_app_applied(APPLICATION_NAME)
    validate_str_contains(health.get_app_version(APPLICATION_NAME), f"{to_version}-", "exporter automatically updated to the target release")
    validate_equals(health.get_app_or_deploy_alarm_count(), 0, "no application or deploy alarms after upgrade")
    compatibility.validate_metrics("post-upgrade", baseline_nodes)

    get_logger().log_test_case_step("Roll back and verify baseline exporter compatibility")
    platform_upgrade.rollback_platform_in_order(deploy)
    validate_equals(deploy.get_running_release(), from_version, "platform returned to the starting release")
    health.wait_for_app_applied(APPLICATION_NAME)
    validate_equals(health.get_app_version(APPLICATION_NAME), baseline_version, "exporter returned to its exact baseline version")
    validate_equals_with_retry(health.get_app_or_deploy_alarm_count, 0, "no application or deploy alarms after rollback", timeout=300, polling_sleep_time=10)
    compatibility.validate_metrics("post-rollback", baseline_nodes)
