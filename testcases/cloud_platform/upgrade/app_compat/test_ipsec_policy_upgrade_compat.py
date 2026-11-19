"""Policy-enforced traffic across N-1/N-2 platform upgrade and rollback."""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.cloud_platform.applications.ipsec_policy_keywords import APPLICATION_NAME
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.ipsec_policy_compatibility_keywords import IPsecPolicyCompatibilityKeywords
from keywords.cloud_platform.upgrade.platform_upgrade_preparation_keywords import PlatformUpgradePreparationKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.standard_platform_upgrade_keywords import StandardPlatformUpgradeKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords


@mark.p2
@mark.lab_has_standby_controller
def test_ipsec_policy_upgrade_rollback(request: FixtureRequest) -> None:
    """Verify policy enforcement before upgrade, after activation and rollback.

    Args:
        request (FixtureRequest): Owner of ordered recovery finalizers.

    Preconditions:
        - Exclusively assigned disposable AIO-DX or Standard lab.
        - Baseline policy operator already applied and two eligible nodes.
        - Configured target ISO and prerequisites for the supported release path.
        - applications.ipsec-policy-operator.traffic_image is a reachable,
          immutable Python-capable image in app_upgrade_compat configuration.

    Test Steps:
        - Validate releases, image, topology and absence of pending deployment.
        - Prepare the target load, license and filesystems.
        - Verify baseline TCP/UDP responses and matching live tunnel counters.
        - Upgrade through activation and check automatic application update.
        - Verify original policies/settings and fresh enforcement on the target.
        - Roll back, verify the exact baseline app version and repeat checks.

    Teardown:
        - Remove phase-owned policies and traffic resources before release recovery.
        - Recover the starting platform release after an incomplete transition.
        - Preserve baseline application settings and existing policies.

    Notes:
        N-1/N-2 are separate runs selected by the installed baseline and target
        configuration. Fresh temporary policies exercise enforcement each phase;
        this does not assert uninterrupted traffic during the platform transition.
    """
    connection = LabConnectionKeywords().get_active_controller_ssh()
    deploy = SoftwareDeploySequenceKeywords(connection)
    platform = StandardPlatformUpgradeKeywords(connection)
    recovery = UpgradeRecoveryKeywords(connection, platform_upgrade=platform)
    health = ApplicationHealthKeywords(connection)
    preparation = PlatformUpgradePreparationKeywords(connection)
    compatibility = IPsecPolicyCompatibilityKeywords(connection)
    config = ConfigurationManager.get_app_upgrade_compat_config()
    get_logger().log_test_case_step("Validate baseline and configured compatibility inputs")
    baseline_release = IPsecPolicyCompatibilityKeywords.normalize_platform_release(deploy.get_running_release())
    target = config.get_to_version()
    image = config.get_ipsec_traffic_image()
    validate_equals(deploy.get_current_deploy_state(), "", "no deployment is in progress before policy compatibility testing")
    platform.require_no_blocking_alarms()
    health.wait_for_app_applied(APPLICATION_NAME)
    baseline_version = health.get_app_version(APPLICATION_NAME)
    validate_str_contains(baseline_version, f"{baseline_release}-", "policy application matches the baseline release")
    nodes = compatibility.validate_inputs(baseline_release, target, image)

    def restore_platform() -> None:
        """Recover the baseline after all phase resource finalizers."""
        recovery.restore_to_release(baseline_release)

    compatibility.capture_original_configuration()
    request.addfinalizer(restore_platform)
    get_logger().log_test_case_step("Prepare target load and verify baseline enforcement")
    preparation.prepare(target)
    compatibility.verify_enforcement(request.addfinalizer, "pre", image, nodes)
    preparation.require_precheck(target)
    get_logger().log_test_case_step("Upgrade through activation and verify policy enforcement")
    platform.upgrade_platform_in_order(deploy, target, leave_at_activate_done=True)
    validate_equals(IPsecPolicyCompatibilityKeywords.normalize_platform_release(deploy.get_running_release()), target, "platform reached the target")
    health.wait_for_app_applied(APPLICATION_NAME)
    validate_str_contains(health.get_app_version(APPLICATION_NAME), f"{target}-", "policy operator automatically updated")
    validate_equals_with_retry(health.get_app_or_deploy_alarm_count, 0, "no application or deploy alarms", timeout=300, polling_sleep_time=10)
    compatibility.verify_enforcement(request.addfinalizer, "post-upgrade", image, nodes)
    get_logger().log_test_case_step("Roll back and verify baseline policy enforcement")
    platform.rollback_platform_in_order(deploy)
    validate_equals(IPsecPolicyCompatibilityKeywords.normalize_platform_release(deploy.get_running_release()), baseline_release, "platform returned to baseline")
    health.wait_for_app_applied(APPLICATION_NAME)
    validate_equals(health.get_app_version(APPLICATION_NAME), baseline_version, "exact baseline policy operator restored")
    validate_equals_with_retry(health.get_app_or_deploy_alarm_count, 0, "no application or deploy alarms after rollback", timeout=300, polling_sleep_time=10)
    compatibility.verify_enforcement(request.addfinalizer, "post-rollback", image, nodes)
