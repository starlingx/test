"""reloader platform-upgrade compatibility test.

Verify that reloader survives a platform release upgrade and rollback and still reloads a watched
workload afterwards. The reload check runs three times - before the upgrade, after it, and after the
rollback - because the question is not whether reloader's own pods restart, but whether it still
reacts to a watched ConfigMap and Secret change on the new release and again once the platform is
rolled back.

Functional truth here is a reload that delivers, not pod count and not the application version
string. reloader's only job is to react, so a reloader that is installed, applied, running,
annotated and silently not reloading is indistinguishable from a healthy one by any readiness,
version or alarm check. Before this test, the repository only checked reloader's pod count, never a
reload.

reloader is updated in place by the platform during deploy activate; it is not removed first. Its
metadata sets ``auto_update: true`` but ``platform_managed_app: no``, and that combination is the
one thing this test does differently from its siblings. Unmanaged applications are still a
first-class category in the activate-time update ordering, so the platform does carry reloader
forward - but only if it is in ``applied`` status, which sysinv gates on in two independent places.
Nothing applies an unmanaged application for you, so an application left merely uploaded is silently
never updated: every post-upgrade assertion would still pass while the platform never touched it.
That is why ``applied`` is asserted immediately before the upgrade and not only after it.

The application is ensured to be uploaded and applied as a setup step rather than assumed, because
an unmanaged application is absent on a freshly installed lab by design. Both setup calls are
guarded and do nothing when it is already in place.

This test targets one release back only, and that is a property of the application rather than a
reduction in scope. An N-2 run needs a baseline two releases back that carries reloader, and
26.10 is the first release that ships app-reloader. The earliest target with a valid N-2 baseline is therefore the release after 27.03,
and no lab can supply what the load does not contain. The test needs no change when that path
becomes available: the starting release is read from the platform and nothing branches on release
distance. Started on a release that predates the application, it fails naming that rather than
failing obscurely on a missing package.

The version assertions compare against the release the platform reports rather than a pinned build.
Deploy activate installs whatever application build ships with the target load, so matching on the
release is what makes this test independent of which respin the lab was installed from.

Not exercised: the certificate-renewal path reloader serves for ejbca; multi-node topologies; and
any assertion that the rollback restored the original application rather than a working one.
reloader's functional output is a rollout, which is identical in every phase, so it has no analogue
of the istio sidecar image tag comparison. The application version assertions carry that weight
alone.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_greater_than, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.reloader_restart_keywords import ReloaderRestartKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.standard_platform_upgrade_keywords import StandardPlatformUpgradeKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

# Key for this application's block in the app-upgrade-compat config, which supplies the platform
# application name, the namespace, and this application's own target release. Read from config
# rather than held here so the application's identity lives in one place across the compatibility
# tests, as it does for the other applications in the family.
APP_KEY = "reloader"
# The application package that ships with the load. Matched by pattern rather than by a pinned file
# name so the test does not have to know the build number of the load the lab was installed from.
APP_PACKAGE_PATTERN = "/usr/local/share/applications/helm/*reloader*"
# The first release that carries app-reloader, used only to explain a failure. It is not a target,
# and it is deliberately NOT used in a comparison - see the precondition below.
FIRST_RELEASE_WITH_RELOADER = "26.10"
# The application reports 'applied' before its pod is serving: the platform has to pull the image for
# the release it just moved to. Waited for rather than sampled once.
#
# Larger than the ReloaderRestartKeywords constant of the same name, which is 300 and governs the
# scratch probe and control pods coming up from an image already in the local registry. This budget
# covers an image pull for a release the system has just moved to, so the two are not an
# inconsistency to be reconciled. The same two names at the same two values appear in the istio and
# metrics-server members of this family.
POD_READY_TIMEOUT = 900
POD_READY_POLL_INTERVAL = 15


@mark.p2
@mark.lab_is_simplex
def test_reloader_upgrade_rollback(request: FixtureRequest) -> None:
    """Verify reloader survives a platform upgrade and rollback and still delivers a reload.

    Preconditions:
        - Target system is accessible and is an AIO-SX
        - The system is on a release that carries app-reloader
        - The target release load is uploaded, so the deploy can resolve it
        - The reloader application package is present on the load

    Setup:
        - Establish SSH connection to the active controller
        - Register the finalizer that restores the starting release
        - Verify the starting release carries the application
        - Verify the target release load is uploaded
        - Require no blocking alarms before creating anything
        - Ensure the reloader application is uploaded
        - Ensure the reloader application is applied

    Test Steps:
        1. Verify reloader is applied at the starting release with its pods ready
        2. Verify a watched ConfigMap and Secret change still delivers a reload
        3. Require no blocking alarms, then verify reloader is applied before the upgrade
        4. Upgrade the platform, leaving the deploy at activate-done so it can be rolled back
        5. Verify reloader was updated to the target release with pods ready and no alarms
        6. Verify a watched ConfigMap and Secret change still delivers a reload
        7. Roll the platform back to the starting release
        8. Verify reloader is restored to the starting release with its pods ready and no alarms
        9. Verify a watched ConfigMap and Secret change still delivers a reload

    Teardown:
        - Remove each phase's scratch namespace, if its own phase did not
        - Restore the starting release

        pytest runs finalizers last-registered-first, and the release restore is registered before
        anything is created so that a setup failure still restores it - which puts it last. Each
        phase removes its own namespace on its happy path and marks it done, so at most one cleanup
        has work to do, and that cleanup is tolerant and cannot raise over the real failure.
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_info(f"Connected to: {ssh_connection.get_name()}")

    deploy = SoftwareDeploySequenceKeywords(ssh_connection)
    health = ApplicationHealthKeywords(ssh_connection)
    recovery = UpgradeRecoveryKeywords(ssh_connection)
    platform_upgrade = StandardPlatformUpgradeKeywords(ssh_connection)
    reload_check = ReloaderRestartKeywords(ssh_connection)
    app_list = SystemApplicationListKeywords(ssh_connection)
    app_upload = SystemApplicationUploadKeywords(ssh_connection)
    app_apply = SystemApplicationApplyKeywords(ssh_connection)

    compat_config = ConfigurationManager.get_app_upgrade_compat_config()
    app_name = compat_config.get_app_name(APP_KEY)
    namespace = compat_config.get_namespace(APP_KEY)
    from_version = deploy.get_running_release()
    # This application's own target, not the shared one: reloader did not exist on the shared
    # target's baseline releases, so that target has no valid starting point for it.
    to_version = compat_config.get_to_version(APP_KEY)
    get_logger().log_info(f"reloader compatibility: {from_version} -> {to_version} -> {from_version}")

    # Registered before the application is touched, so a setup that fails part-way through still
    # leaves the platform on the release it started on.
    def restore_the_starting_release():
        get_logger().log_teardown_step(f"Restore the starting release {from_version}")
        recovery.restore_to_release(from_version)

    request.addfinalizer(restore_the_starting_release)

    # Checked before anything else, because a lab on a release that predates the application cannot
    # run this test at all and the next step would otherwise fail on a tarball glob that matched
    # nothing - an error that says nothing about why. An assertion rather than a skip: a skipped run
    # is invisible in the dashboard roll-up, which is how a test reports green for cycles without
    # ever having run.
    # The precondition that matters is whether this load carries the application, so that is what is
    # asserted - not whether the release number sorts above the first release that shipped it.
    # Comparing release strings would be wrong for an unpadded minor ("26.9" sorts above "26.10")
    # and for a three-digit major, and would have to be revisited every time the numbering changed.
    # Asking the load directly cannot drift.
    get_logger().log_setup_step("Verify the starting release carries the application")
    already_present = app_list.get_system_application_list().is_in_application_list(app_name)
    # get_matching_files reports a pattern that matched nothing as an empty list, and raises only
    # when it could not establish the outcome at all. The distinction matters here: catching the
    # asserting variant's exception instead would fold an SSH failure into the precondition below,
    # reporting a load that does carry the application as one that does not.
    package_matches = [] if already_present else LsKeywords(ssh_connection).get_matching_files(APP_PACKAGE_PATTERN)
    validate_equals(
        bool(already_present or package_matches),
        True,
        f"reloader is not available on release {from_version}: neither the application nor its package is present. The application was introduced in {FIRST_RELEASE_WITH_RELOADER}, so earlier releases cannot serve as a baseline. This test supports one release back from {FIRST_RELEASE_WITH_RELOADER} onward; two releases back becomes available when the target's N-2 release carries reloader",
    )
    package_path = package_matches[0] if package_matches else ""

    # Resolved now rather than at the upgrade step. Without the target load this test can do nothing
    # useful, and the baseline verification ahead of the upgrade takes long enough that discovering
    # it there wastes the run.
    get_logger().log_setup_step("Verify the target release load is uploaded")
    target_release_id = deploy.get_release_id_for_version(to_version)
    get_logger().log_info(f"Target load resolved to '{target_release_id}'")

    # Presence is read from the application list rather than through is_already_uploaded, which
    # reports False for an application that is already applied. Force is deliberately not set on the
    # upload: it would remove and delete an application that is already in place, which is the
    # opposite of what a guard is for.
    # Environmental alarms are diagnosed before anything is created, and never suppressed. A
    # standing alarm is reported here, named, rather than as a reloader failure later: the counter
    # used after the upgrade matches on alarm id prefixes only and does not filter by entity, so a
    # pre-existing alarm raised by some other application would otherwise be attributed to this
    # test. 'software deploy start' rejects any active alarm regardless, so this is also the truth
    # about whether the upgrade could proceed at all.
    get_logger().log_setup_step("Require no blocking alarms before creating anything")
    platform_upgrade.require_no_blocking_alarms()

    get_logger().log_setup_step("Ensure the reloader application is uploaded")
    if already_present:
        get_logger().log_info(f"'{app_name}' is already present; skipping the upload")
    else:
        get_logger().log_info(f"Uploading '{app_name}' from {package_path}")
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(app_name)
        upload_input.set_tar_file_path(package_path)
        app_upload.system_application_upload(upload_input)

    # Unlike the platform-managed applications in this family, reloader is never applied for us, so
    # this is the normal path rather than the exception.
    get_logger().log_setup_step("Ensure the reloader application is applied")
    if health.is_app_applied(app_name):
        get_logger().log_info(f"'{app_name}' is already applied; skipping the apply")
    else:
        get_logger().log_info(f"Applying '{app_name}'")
        applied_timeout = ConfigurationManager.get_usm_config().get_app_applied_timeout_sec()
        app_apply.system_application_apply(app_name, timeout=applied_timeout)

    # Baseline: the application is up and reloading on the release we start from.
    get_logger().log_test_case_step("Verify reloader is applied at the starting release with its pods ready")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"reloader is a {from_version} version at baseline")
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace),
        0,
        "reloader pods are ready at baseline",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )
    # The readiness read above enforces the keyword's own default floor of one pod, so an empty
    # namespace already fails it. This count is captured for the later phases, which require at
    # least as many pods as the baseline had rather than merely one - an application that came back
    # from the upgrade with fewer pods than it started with would otherwise pass.
    baseline_pod_count = health.get_pod_count(namespace)
    validate_greater_than(baseline_pod_count, 0, "reloader has pods at baseline")

    get_logger().log_test_case_step("Verify a watched ConfigMap and Secret change still delivers a reload")
    reload_check.validate_reload_delivers(request, "pre")

    # The one assertion this test makes that its siblings do not need. reloader sets
    # platform_managed_app: no, and the activate-time update selects only applications in 'applied'
    # status. An application left merely uploaded is skipped entirely, and every assertion after the
    # upgrade would still pass while the platform never touched it.
    # Checked again here, after the apply. The gate in setup catches an alarm that was already
    # standing; this one catches an alarm our own apply raised, which would otherwise first surface
    # as the bare refusal from 'software deploy start' - the failure the gate exists to replace with
    # a named one.
    get_logger().log_test_case_step("Require no blocking alarms before starting the upgrade")
    platform_upgrade.require_no_blocking_alarms()

    get_logger().log_test_case_step("Verify reloader is applied immediately before the upgrade")
    validate_equals(health.is_app_applied(app_name), True, "reloader must be applied before the upgrade, or the platform will not carry it forward")

    # Upgrade the platform, stopping short of completing the deploy so it can be rolled back.
    get_logger().log_test_case_step(f"Upgrade the platform to {to_version}, leaving the deploy at activate-done")
    deploy.deploy_upgrade(to_version, leave_at_activate_done=True)
    validate_str_contains(deploy.get_running_release(), to_version, f"platform is on {to_version} after upgrade")

    # The application should have been carried forward by the platform despite being unmanaged.
    get_logger().log_test_case_step("Verify reloader was updated to the target release with pods ready and no alarms")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), to_version, f"reloader is a {to_version} version after upgrade")
    # The baseline count is carried forward here, unlike the istio test. istio's chart set can
    # legitimately gain or lose a component between releases, so requiring the baseline count would
    # false-fail a healthy system. reloader is single-chart - one Deployment - so a smaller pod count
    # after the upgrade is a regression, and the single-chart siblings assert it the same way.
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace, expected_min=baseline_pod_count),
        0,
        "reloader has at least its baseline pods, all ready, after upgrade",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )
    validate_equals_with_retry(
        health.get_app_or_deploy_alarm_count,
        0,
        "no application or deploy alarms after upgrade",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )

    get_logger().log_test_case_step("Verify a watched ConfigMap and Secret change still delivers a reload")
    reload_check.validate_reload_delivers(request, "post-upgrade")

    # Roll the platform back, and the application should return to where it started.
    get_logger().log_test_case_step(f"Roll the platform back to {from_version}")
    deploy.deploy_rollback()
    validate_str_contains(deploy.get_running_release(), from_version, f"platform is on {from_version} after rollback")

    get_logger().log_test_case_step("Verify reloader is restored to the starting release with its pods ready")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"reloader is a {from_version} version after rollback")
    # Back on the starting release the platform has to pull that release's image again, so the pod is
    # recreated and is not ready the moment the application reports 'applied'.
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace, expected_min=baseline_pod_count),
        0,
        "reloader has at least its baseline pods, all ready, after rollback",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )
    # Rollback re-applies the application on the starting release, which is the same event the
    # post-upgrade alarm check guards, so it is asserted here too. Retried rather than read once
    # because alarms raised during the rollback take time to clear.
    validate_equals_with_retry(
        health.get_app_or_deploy_alarm_count,
        0,
        "no application or deploy alarms after rollback",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )

    get_logger().log_test_case_step("Verify a watched ConfigMap and Secret change still delivers a reload")
    reload_check.validate_reload_delivers(request, "post-rollback")
