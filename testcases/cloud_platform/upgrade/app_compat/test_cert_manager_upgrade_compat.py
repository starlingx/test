"""cert-manager platform-upgrade compatibility test.

Verify that cert-manager survives a platform release upgrade and rollback and still issues
certificates afterwards. The issuance check runs three times - before the upgrade, after it, and
after the rollback - because the question is not whether the pods restart, but whether the
controller still fulfils a certificate request on the new release and again once the platform is
rolled back.

cert-manager is updated in place by the platform during deploy activate; it is not removed first.

The release the system starts on comes from the platform itself, so this one test case covers both
the one-release-back and two-releases-back paths: the body is identical and only the starting
release differs, which is decided by the release the lab was installed with.
"""
from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.cert_manager_issuance_keywords import CertManagerIssuanceKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords

APP_KEY = "cert-manager"


@mark.p2
def test_cert_manager_upgrade_rollback(request):
    """Verify cert-manager survives a platform upgrade and rollback and still issues certificates.

    Test Steps:
        - Read the release the platform is on and the release to upgrade to
        - Verify cert-manager is applied at its baseline version with healthy pods
        - Verify a self-signed certificate is issued (pre-upgrade)
        - Upgrade the platform, leaving the deploy at activate-done so it can be rolled back
        - Verify cert-manager was updated to the target-release version by the platform
        - Verify pods are healthy and no application or deploy alarms are raised
        - Verify a self-signed certificate is issued (post-upgrade)
        - Roll the platform back and verify it is on the starting release
        - Verify cert-manager is restored to its baseline version with healthy pods
        - Verify a self-signed certificate is issued (post-rollback)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    deploy = SoftwareDeploySequenceKeywords(ssh_connection)
    health = ApplicationHealthKeywords(ssh_connection)
    issuance = CertManagerIssuanceKeywords(ssh_connection)
    recovery = UpgradeRecoveryKeywords(ssh_connection)
    compat_config = ConfigurationManager.get_app_upgrade_compat_config()

    app_name = compat_config.get_app_name(APP_KEY)
    namespace = compat_config.get_namespace(APP_KEY)
    from_version = deploy.get_running_release()
    to_version = compat_config.get_to_version()
    get_logger().log_info(f"cert-manager compatibility: {from_version} -> {to_version} -> {from_version}")

    def restore_the_starting_release():
        recovery.restore_to_release(from_version)

    request.addfinalizer(restore_the_starting_release)

    # Baseline: the application is up and working on the release we start from.
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"cert-manager is a {from_version} version at baseline")
    validate_equals(health.get_unhealthy_pod_count(namespace), 0, "cert-manager pods are healthy at baseline")
    issuance.validate_certificate_is_issued(request, "pre")

    # Upgrade the platform, stopping short of completing the deploy so it can be rolled back.
    deploy.deploy_upgrade(to_version, leave_at_activate_done=True)
    validate_str_contains(deploy.get_running_release(), to_version, f"platform is on {to_version} after upgrade")

    # The application should have been updated by the platform, and still work.
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), to_version, f"cert-manager is a {to_version} version after upgrade")
    validate_equals(health.get_unhealthy_pod_count(namespace), 0, "cert-manager pods are healthy after upgrade")
    validate_equals(health.get_app_or_deploy_alarm_count(), 0, "no application or deploy alarms after upgrade")
    issuance.validate_certificate_is_issued(request, "post-upgrade")

    # Roll the platform back, and the application should return to where it started.
    deploy.deploy_rollback()
    validate_str_contains(deploy.get_running_release(), from_version, f"platform is on {from_version} after rollback")

    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"cert-manager is a {from_version} version after rollback")
    validate_equals(health.get_unhealthy_pod_count(namespace), 0, "cert-manager pods are healthy after rollback")
    issuance.validate_certificate_is_issued(request, "post-rollback")
