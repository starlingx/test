"""Auditd event capture before and after a platform upgrade and rollback.

One body covers both one-release-back and two-releases-back runs, using the
installed platform release as its starting point. Audit enablement, baseline app
installation and configured platform preparation run before deploy-start, with
original audit state restored only after the platform returns to its release.
"""

import re

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.audit_event_capture_keywords import AuditEventCaptureKeywords
from keywords.cloud_platform.upgrade.audit_upgrade_setup_keywords import AuditUpgradeSetupKeywords
from keywords.cloud_platform.upgrade.platform_upgrade_preparation_keywords import PlatformUpgradePreparationKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.standard_platform_upgrade_keywords import StandardPlatformUpgradeKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords


@mark.p2
def test_audit_upgrade_rollback(request: FixtureRequest) -> None:
    """Verify fresh host audit events survive platform upgrade and rollback.

    Args:
        request (FixtureRequest): Pytest request for release and artifact recovery.

    Test Steps:
        - Reject equal/older targets and an existing deployment before setup.
        - Capture the original audit state and register ordered recovery.
        - Prepare configured load, license and required filesystems.
        - Enable auditing and upload/apply the baseline auditd application.
        - Verify applied baseline auditd version and fresh events on every node.
        - Upgrade the platform to activate-done, allowing its auditd auto-update.
        - Verify target platform/app versions, alarms and fresh events per node.
        - Roll back and verify the exact original application version is restored.
        - Verify fresh audit events on every node after rollback.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    deploy = SoftwareDeploySequenceKeywords(ssh_connection)
    platform_upgrade = StandardPlatformUpgradeKeywords(ssh_connection)
    recovery = UpgradeRecoveryKeywords(ssh_connection, platform_upgrade=platform_upgrade)
    health = ApplicationHealthKeywords(ssh_connection)
    capture = AuditEventCaptureKeywords(ssh_connection)
    compat_config = ConfigurationManager.get_app_upgrade_compat_config()
    app_name = compat_config.get_app_name("auditd")
    from_version = deploy.get_running_release()
    to_version = compat_config.get_to_version()
    if not all(isinstance(version, str) and re.fullmatch(r"\d+\.\d+", version) for version in (from_version, to_version)):
        raise ValueError("Compatibility requires numeric major.minor starting and target platform releases")
    if tuple(map(int, to_version.split("."))) <= tuple(map(int, from_version.split("."))):
        raise KeywordException(f"Target {to_version} must be newer than installed release {from_version}; provision an older starting release")
    if deploy.get_current_deploy_state():
        raise KeywordException("An existing platform deployment must be resolved before audit compatibility setup")
    # Diagnose environmental alarms before any setup mutation; never suppress them.
    platform_upgrade.require_no_blocking_alarms()
    setup = AuditUpgradeSetupKeywords(ssh_connection)
    preparation = PlatformUpgradePreparationKeywords(ssh_connection)
    baseline = setup.capture(from_version)
    hosts = baseline.hosts
    get_logger().log_info(f"auditd compatibility: {from_version} -> {to_version} -> {from_version}; hosts={hosts}")

    def restore_the_starting_release():
        recovery.restore_to_release(from_version)

    def restore_original_audit_state():
        # Recovery is best effort. Do not change the app/kernel under a failed or
        # incomplete deployment, even if the old platform happens to be booted.
        if deploy.get_running_release() != from_version or deploy.get_current_deploy_state():
            raise KeywordException("Platform recovery is incomplete; retain the audit baseline and recover the deployment before restoring audit state")
        setup.restore()

    # Reverse execution: phase artifacts, platform recovery, then original audit state.
    request.addfinalizer(restore_original_audit_state)
    request.addfinalizer(restore_the_starting_release)
    preparation.prepare(to_version)
    setup.prepare()

    health.wait_for_app_applied(app_name)
    baseline_version = health.get_app_version(app_name)
    validate_str_contains(baseline_version, f"{from_version}-", "auditd is at the starting release")
    capture.validate_event_capture(request, "pre", hosts)

    preparation.require_precheck(to_version)
    platform_upgrade.upgrade_platform_in_order(deploy, to_version, leave_at_activate_done=True)
    validate_equals(deploy.get_running_release(), to_version, "platform is on the target release")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), f"{to_version}-", "auditd auto-updated to the target release")
    validate_equals(health.get_app_or_deploy_alarm_count(), 0, "no application or deploy alarms after upgrade")
    capture.validate_event_capture(request, "post-upgrade", hosts)

    platform_upgrade.rollback_platform_in_order(deploy)
    validate_equals(deploy.get_running_release(), from_version, "platform is on the starting release after rollback")
    health.wait_for_app_applied(app_name)
    validate_equals(health.get_app_version(app_name), baseline_version, "auditd returned to its exact original version")
    validate_equals(health.get_app_or_deploy_alarm_count(), 0, "no application or deploy alarms after rollback")
    capture.validate_event_capture(request, "post-rollback", hosts)
