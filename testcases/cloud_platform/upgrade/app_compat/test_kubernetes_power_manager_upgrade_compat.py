"""kubernetes-power-manager platform-upgrade compatibility test.

Verify that kubernetes-power-manager (KPM) survives a platform release upgrade and rollback and
keeps its per-node power-node-agent reconciled afterwards. KPM is an upstream Intel application
that is not part of the platform install baseline, so unlike the other app-compat tests this one
installs it first when it is not already present, then checks it three times - before the upgrade,
after it, and after the rollback.

kubernetes-power-manager is updated in place by the platform during deploy activate; it is not
removed first.

The release the system starts on comes from the platform itself, so this one test case covers both
the one-release-back and two-releases-back paths: the body is identical and only the starting
release differs, which is decided by the release the lab was installed with.

KPM runs the controller-manager and a per-node power-node-agent DaemonSet; it needs a duplex lab.
The real CPU-knob effects (cpufreq/powercap) only hold on physical hardware, so this test asserts
the app is applied, versioned to the running release, and its agent is reconciled on every node,
not that a specific host power state was programmed.
"""
from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.kubernetes_power_manager_compat_check_keywords import KubernetesPowerManagerCompatCheckKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords

APP_KEY = "kubernetes-power-manager"
NFD_KEY = "node-feature-discovery"


@mark.p2
@mark.lab_is_duplex
def test_kubernetes_power_manager_upgrade_rollback(request):
    """Verify kubernetes-power-manager survives a platform upgrade and rollback.

    Test Steps:
        - Read the release the platform is on and the release to upgrade to
        - Ensure node-feature-discovery is applied first (kubernetes-power-manager's dependent app;
          the power-node-agent relies on the node feature labels NFD publishes)
        - Install kubernetes-power-manager if it is not already applied (upstream app, not part of
          the install baseline)
        - Assign the power-management=enabled label so the power-node-agent is scheduled
        - Verify it is applied at its baseline version with healthy pods and the power-node-agent
          reconciled on every node
        - Upgrade the platform, leaving the deploy at activate-done so it can be rolled back
        - Verify it was updated to the target-release version by the platform, pods are healthy,
          the agent is reconciled, and no application or deploy alarms are raised
        - Roll the platform back and verify it is on the starting release
        - Verify it is restored to its baseline version with healthy pods and the agent reconciled
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    deploy = SoftwareDeploySequenceKeywords(ssh_connection)
    health = ApplicationHealthKeywords(ssh_connection)
    kpm = KubernetesPowerManagerCompatCheckKeywords(ssh_connection)
    recovery = UpgradeRecoveryKeywords(ssh_connection)
    compat_config = ConfigurationManager.get_app_upgrade_compat_config()

    app_name = compat_config.get_app_name(APP_KEY)
    namespace = compat_config.get_namespace(APP_KEY)
    nfd_app_name = compat_config.get_app_name(NFD_KEY)
    base_application_path = ConfigurationManager.get_app_config().get_base_application_path()
    tar_file_path = f"{base_application_path}{app_name}*.tgz"
    nfd_tar_file_path = f"{base_application_path}{nfd_app_name}*.tgz"
    expected_nodes = len(SystemHostListKeywords(ssh_connection).get_system_host_list().get_hosts())

    from_version = deploy.get_running_release()
    to_version = compat_config.get_to_version()
    get_logger().log_info(f"kubernetes-power-manager compatibility: {from_version} -> {to_version} -> {from_version}")

    def restore_the_starting_release():
        recovery.restore_to_release(from_version)

    request.addfinalizer(restore_the_starting_release)

    # node-feature-discovery is KPM's dependent app: the power-node-agent relies on the node
    # feature labels NFD publishes, so ensure NFD is applied before KPM. Like KPM, NFD is an
    # upstream app that may not be part of the install baseline, so install it if it is absent.
    nfd_uploaded = kpm.ensure_applied(nfd_app_name, nfd_tar_file_path)
    health.wait_for_app_applied(nfd_app_name)

    # Install-if-missing: KPM is an upstream app that is not in the install baseline, so unlike the
    # other app-compat tests the baseline cannot assume it is already applied.
    kpm_uploaded = kpm.ensure_applied(app_name, tar_file_path)

    # The power-node-agent DaemonSet selects nodes by the power-management=enabled label; without it
    # the agent is never scheduled (DESIRED=0). Assign it where missing after KPM is applied, per
    # the manual install procedure. When the label is newly assigned it is a configuration change,
    # so the app is reapplied to settle it before the baseline checks and the later deploy start.
    labelled_hosts = kpm.ensure_power_management_label(app_name)

    # Leave the lab as this test found it: remove only what this run installed (the label on the
    # hosts it labelled, and each app it uploaded), so a later test in the same lab does not inherit
    # KPM, NFD or the power-management label from here. Registered after the installs so teardown
    # unwinds them in reverse (label, then KPM, then NFD), and only for what was actually added.
    def clean_up_what_this_test_installed():
        kpm.remove_power_management_label(labelled_hosts)
        if kpm_uploaded:
            kpm.remove_app(app_name)
        if nfd_uploaded:
            kpm.remove_app(nfd_app_name)

    request.addfinalizer(clean_up_what_this_test_installed)

    # Baseline: the application is up and working on the release we start from.
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"kubernetes-power-manager is a {from_version} version at baseline")
    validate_equals(health.get_unhealthy_pod_count(namespace), 0, "kubernetes-power-manager pods are healthy at baseline")
    kpm.wait_for_power_node_agent_ready(namespace, expected_nodes)

    # Upgrade the platform, stopping short of completing the deploy so it can be rolled back.
    deploy.deploy_upgrade(to_version, leave_at_activate_done=True)
    validate_str_contains(deploy.get_running_release(), to_version, f"platform is on {to_version} after upgrade")

    # The application should have been updated by the platform, and still work. NFD is re-verified
    # too: it is the dependency the power-node-agent relies on, so it must still be applied for the
    # agent check below to be meaningful.
    health.wait_for_app_applied(nfd_app_name)
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), to_version, f"kubernetes-power-manager is a {to_version} version after upgrade")
    validate_equals(health.get_unhealthy_pod_count(namespace), 0, "kubernetes-power-manager pods are healthy after upgrade")
    validate_equals(health.get_app_or_deploy_alarm_count(), 0, "no application or deploy alarms after upgrade")
    kpm.wait_for_power_node_agent_ready(namespace, expected_nodes)

    # Roll the platform back, and the application should return to where it started.
    deploy.deploy_rollback()
    validate_str_contains(deploy.get_running_release(), from_version, f"platform is on {from_version} after rollback")

    health.wait_for_app_applied(nfd_app_name)
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"kubernetes-power-manager is a {from_version} version after rollback")
    validate_equals(health.get_unhealthy_pod_count(namespace), 0, "kubernetes-power-manager pods are healthy after rollback")
    kpm.wait_for_power_node_agent_ready(namespace, expected_nodes)
