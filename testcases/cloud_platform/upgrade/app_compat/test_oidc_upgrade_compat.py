"""oidc-auth-apps platform-upgrade compatibility test.

Verify that oidc-auth-apps survives a platform release upgrade and rollback and that a user can
still authenticate afterwards. The authentication check runs three times - before the upgrade, after
it, and after the rollback - because the question is not whether the OIDC pods restart, but whether
a user can still obtain a token from the issuer and act on the Kubernetes API with it on the new
release, and again once the platform is rolled back.

oidc-auth-apps is updated in place by the platform during deploy activate; it is not removed first.
Its metadata sets ``auto_update`` and ``platform_managed_app``, so the auto-update path is the whole
procedure and there is no remove-before-upgrade variant to cover separately. Measured on a live system:
the platform moved it to the target release's build during activate, unasked.

Functional truth here is an authentication performed **from scratch**, not pod readiness and not the
application version string. In several reported upgrade defects the pods were up and the application
reported ``applied`` while authentication was broken, which is the class of defect a readiness
count cannot see. The session is re-established in every phase: the token lives in the
user's kubeconfig, so reusing a session would validate that token against the apiserver and say
nothing about whether the issuer still works.

The Kubernetes username is read back from oidc-auth rather than assumed. It is the claim named by
the kube_apiserver ``oidc-username-claim`` service parameter, resolved through the dex connector's
attribute mapping, and three different mappings exist across the codebase and the documentation. On
the lab this was developed against it resolves to the LDAP GECOS field.

The post-rollback phase is the highest-value assertion in this test. A previously reported defect
had the OIDC CLI login failing only after a rollback, because kubeconfig-setup wrote an exec plugin
format the older release could not read - on precisely the sequence this check runs. Measured here,
the rollback direction is also the slower one to recover: the login returned on the first attempt
after the upgrade but needed around 90 seconds after the rollback.

Lab preconditions, which this test does not create:
    - oidc-auth-apps configured for the platform's local LDAP, with the four kube_apiserver
      ``oidc-*`` service parameters in effect. Changing them restarts the apiserver, so the test
      asserts them rather than setting them.
    - a check LDAP user, and a ClusterRoleBinding whose subject is ``<issuer-url>#<resolved
      username>``, granting it enough to list pods.
    - cert-manager applied and the oidc-auth-apps-certificate secret present.

The release the system starts on comes from the platform itself, so this one test case covers both
the one-release-back and two-releases-back paths: the body is identical and only the starting
release differs, which is decided by the release the lab was installed with.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_greater_than, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.oidc_auth_check_keywords import OidcAuthCheckKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords

APP_KEY = "oidc-auth-apps"
# The application reports 'applied' before its pods are serving: the platform has to pull the images
# for the release it just moved to. Waited for rather than sampled once.
POD_READY_TIMEOUT = 900
POD_READY_POLL_INTERVAL = 15
# oidc-auth-apps lives in kube-system alongside the whole control plane, so pod counts are scoped by
# label rather than by namespace. Without this the floor and the readiness count would describe the
# platform rather than the application.
#
# The three charts share no common label - measured on a live system, oidc-dex carries app=dex, the
# client carries app=stx-oidc-client, and the secret-observer job pods carry only batch labels - so
# the two long-running deployments are counted separately and asserted individually. That is a
# stronger floor than a single selector would give: each component must be present in its own
# right. The cron job is covered by validate_secret_observer_is_scheduled instead, and its pods
# reach Completed, which the readiness count already excludes.
OIDC_POD_LABELS = ("app=dex", "app=stx-oidc-client")


def _assert_oidc_pods_ready(health: ApplicationHealthKeywords, namespace: str, phase: str) -> None:
    """Wait for each oidc-auth-apps deployment to have at least one pod, all of them ready.

    Retried in **every** phase, including the baseline. The application recycles its own pods
    without being asked: secret-observer restarts stx-oidc-client and oidc-dex on a */15 cron
    whenever the certificate secret changes, and a release change replaces certificates. Measured
    on a live system, a baseline check caught stx-oidc-client mid-replacement, with the incoming pod
    briefly unschedulable - "0/1 nodes are available: 1 node(s) didn't match pod anti-affinity
    rules" - while the outgoing one was still terminating. A single sample at the baseline
    therefore fails on timing rather than on the application's state, which is the same trap the
    authoring guide describes for applications that reach 'applied' before they are serving.

    Args:
        health (ApplicationHealthKeywords): the health keyword.
        namespace (str): the namespace the application installs into.
        phase (str): where in the upgrade this is running, for the assertion message.
    """
    for label in OIDC_POD_LABELS:
        validate_equals_with_retry(
            lambda current_label=label: health.get_not_ready_pod_count(namespace, expected_min=1, label=current_label),
            0,
            f"[{phase}] oidc-auth-apps pods matching '{label}' are ready",
            timeout=POD_READY_TIMEOUT,
            polling_sleep_time=POD_READY_POLL_INTERVAL,
        )


@mark.p2
# Simplex only. The deploy sequence this test drives locks and unlocks a single controller; on a
# duplex system the host-by-host order differs and the rollback has a different shape, so the test
# would be asserting against a sequence it does not actually perform.
@mark.lab_is_simplex
def test_oidc_upgrade_rollback(request):
    """Verify oidc-auth-apps survives a platform upgrade and rollback and still authenticates.

    Test Steps:
        - Read the release the platform is on and the release to upgrade to
        - Verify oidc-auth-apps is applied at its baseline version with its pods ready
        - Verify the secret-observer cron job is scheduled
        - Authenticate from scratch and act on the API; record the resolved username and image tags
        - Upgrade the platform, leaving the deploy at activate-done so it can be rolled back
        - Verify oidc-auth-apps was updated to the target-release version by the platform
        - Verify pods are ready and no application or deploy alarms are raised
        - Authenticate from scratch again, and verify the resolved username is unchanged
        - Roll the platform back and verify it is on the starting release
        - Verify oidc-auth-apps is restored to its baseline version with its pods ready
        - Authenticate from scratch a third time, and verify the image tags returned to baseline
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    deploy = SoftwareDeploySequenceKeywords(ssh_connection)
    health = ApplicationHealthKeywords(ssh_connection)
    recovery = UpgradeRecoveryKeywords(ssh_connection)
    oidc = OidcAuthCheckKeywords(ssh_connection)

    compat_config = ConfigurationManager.get_app_upgrade_compat_config()
    app_name = compat_config.get_app_name(APP_KEY)
    namespace = compat_config.get_namespace(APP_KEY)

    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    test_user = ConfigurationManager.get_security_config().get_dex_connector_config().get_test_user()
    oidc_username = test_user.get_username()
    oidc_password = test_user.get_password()

    from_version = deploy.get_running_release()
    to_version = compat_config.get_to_version()
    get_logger().log_info(f"oidc-auth-apps compatibility: {from_version} -> {to_version} -> {from_version}")

    # The Kubernetes username has to be known before anything is registered or changed: it is what
    # the role-binding snapshot and the narrow grant are keyed on. It cannot be derived from the
    # login name, because the apiserver prefixes it with the issuer URL unless the configured claim
    # is email, so the same user differs between labs.
    resolved_username = oidc.read_resolved_username(oidc_username, oidc_password, oam_ip)
    # Owned here and registered for restore before anything is suspended, so a failure part-way
    # through the suspend still has its restore registered against what was already removed.
    suspended_bindings = []

    def restore_oidc_access():
        """Remove this test's grant and put back the role bindings it suspended."""
        oidc.restore_access(suspended_bindings, resolved_username)

    def restore_the_starting_release():
        """Return the platform to the starting release if the test left it elsewhere."""
        recovery.restore_to_release(from_version)

    # Registration order matters and is the reverse of execution order: pytest runs finalizers
    # last-in-first-out. Registering the access restore first means it runs last, after the
    # platform is back on its starting release, rather than in the middle of a deploy where it
    # could only fail.
    request.addfinalizer(restore_oidc_access)
    request.addfinalizer(restore_the_starting_release)

    oidc.suspend_broad_access(resolved_username, suspended_bindings)

    # Baseline: the application is up and a user can authenticate on the release we start from.
    get_logger().log_test_case_step("Verify oidc-auth-apps is applied and healthy at baseline")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"oidc-auth-apps is a {from_version} version at baseline")
    for label in OIDC_POD_LABELS:
        validate_greater_than(health.get_pod_count(namespace, label=label), 0, f"oidc-auth-apps has pods matching '{label}' at baseline")
    _assert_oidc_pods_ready(health, namespace, "pre")
    # Fail with a sentence that names what the lab is missing, rather than as a mid-phase
    # authentication timeout that reads like a product defect.
    oidc.validate_preconditions()
    oidc.validate_apiserver_oidc_flags_in_effect("pre")
    oidc.validate_secret_observer_is_scheduled("pre")

    get_logger().log_test_case_step("Authenticate from scratch at baseline")
    baseline = oidc.validate_oidc_access(request, "pre", oidc_username, oidc_password, oam_ip)

    # Upgrade the platform, stopping short of completing the deploy so it can be rolled back.
    get_logger().log_test_case_step(f"Upgrade the platform to {to_version}")
    deploy.deploy_upgrade(to_version, leave_at_activate_done=True)
    validate_str_contains(deploy.get_running_release(), to_version, f"platform is on {to_version} after upgrade")

    get_logger().log_test_case_step("Verify oidc-auth-apps was updated by the platform and is healthy")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), to_version, f"oidc-auth-apps is a {to_version} version after upgrade")
    _assert_oidc_pods_ready(health, namespace, "post-upgrade")
    validate_equals_with_retry(
        health.get_app_or_deploy_alarm_count,
        0,
        "no application or deploy alarms after upgrade",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )
    oidc.validate_apiserver_oidc_flags_in_effect("post-upgrade")
    oidc.validate_secret_observer_is_scheduled("post-upgrade")

    get_logger().log_test_case_step("Authenticate from scratch after the upgrade")
    post_upgrade = oidc.validate_oidc_access(request, "post-upgrade", oidc_username, oidc_password, oam_ip)
    # The claim configuration is carried through the upgrade, so the username the issuer resolves
    # must not change. A changed username means the binding no longer matches and authorization
    # would be silently lost on a system that still authenticates.
    validate_equals(post_upgrade["username"], baseline["username"], "the resolved OIDC username is unchanged after the upgrade")

    # Roll the platform back, and the application should return to where it started.
    get_logger().log_test_case_step(f"Roll the platform back to {from_version}")
    deploy.deploy_rollback()
    validate_str_contains(deploy.get_running_release(), from_version, f"platform is on {from_version} after rollback")

    get_logger().log_test_case_step("Verify oidc-auth-apps is restored and healthy")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"oidc-auth-apps is a {from_version} version after rollback")
    _assert_oidc_pods_ready(health, namespace, "post-rollback")
    oidc.validate_apiserver_oidc_flags_in_effect("post-rollback")
    oidc.validate_secret_observer_is_scheduled("post-rollback")

    get_logger().log_test_case_step("Authenticate from scratch after the rollback")
    post_rollback = oidc.validate_oidc_access(request, "post-rollback", oidc_username, oidc_password, oam_ip)
    validate_equals(post_rollback["username"], baseline["username"], "the resolved OIDC username is unchanged after the rollback")
    # The images are asserted as a transition rather than against a pinned value, so the test stays
    # correct as releases move on. No oidc or dex version is hardcoded anywhere in this file.
    validate_equals(post_rollback["dex_image"], baseline["dex_image"], "the oidc-dex image returned to its baseline after rollback")
    validate_equals(post_rollback["client_image"], baseline["client_image"], "the stx-oidc-client image returned to its baseline after rollback")
