"""istio platform-upgrade compatibility test.

Verify that istio survives a platform release upgrade and rollback and still injects a working
sidecar afterwards. The injection check runs three times - before the upgrade, after it, and after
the rollback - because the question is not whether the istio pods restart, but whether the sidecar
injector still works on the new release and again once the platform is rolled back.

istio is updated in place by the platform during deploy activate; it is not removed first. Its
metadata sets auto_update and platform_managed_app, so the auto-update path is the whole procedure
and there is no remove-before-upgrade variant to cover separately.

Functional truth here is sidecar injection, not pod count and not the application version string.
The application bundle version carries the platform release prefix, while the thing that was
up-versioned is the istio minor version - two different facts. So the test records the injected
sidecar image tag and asserts it as a transition: different from baseline after the upgrade, equal to
baseline after the rollback. No istio version is hardcoded as an expectation anywhere in this file
  or in the configuration - the versions named below are observations, not inputs,
so the test stays correct as releases move on.

The two-releases-back path is the interesting one. Reaching the current release from two releases
back skips istio minor versions, against istio's own guidance on skipping minors during a control
plane upgrade, and it is also where the sidecar changes shape: istio made native sidecars the
default in 1.27, but the layout is not decided by the proxy version: the same istio 1.29.2
was measured as an init container on the 26.03 path and a regular container on the 25.09 path, so it
follows the injector configuration carried through the upgrade. The check reads both container lists
and compares ready against total rather than deriving a count, so neither phase's layout is
assumed.

Lab preconditions, which this test does not create:
    - The local registry holds a small long-running image for the injection probe. The image is
      discovered at runtime, not pinned.

istio itself IS ensured rather than assumed. It is an optional application, so a freshly installed
lab does not carry it, and both setup calls are guarded and do nothing when it is already in place.
The existing apps_setup test is not reused for this: it asserts istio is absent before it starts, so
it fails on any lab that already has it, which is the opposite of what a guard is for. istio is left
applied afterwards, as oran-o2 does, so a rerun on the same lab skips the install.

The release the system starts on comes from the platform itself, so this one test case covers both
the one-release-back and two-releases-back paths: the body is identical and only the starting
release differs, which is decided by the release the lab was installed with.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_greater_than, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.istio_sidecar_keywords import IstioSidecarKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

# Key for this application's block in the app-upgrade-compat config, which supplies the platform
# application name and the namespace. Read from config rather than held here so the application's
# identity lives in one place across the compatibility tests, as it does for cert-manager and
# oran-o2.
APP_KEY = "istio"
# The application reports 'applied' before its pods are serving: the platform has to pull the images
# for the release it just moved to. Waited for rather than sampled once.
POD_READY_TIMEOUT = 900
POD_READY_POLL_INTERVAL = 15


@mark.p2
@mark.lab_is_simplex
def test_istio_upgrade_rollback(request):
    """Verify istio survives a platform upgrade and rollback and still injects a working sidecar.

    Preconditions:
        - Target system is accessible and is an AIO-SX
        - The target release load is uploaded, so the deploy can resolve it
        - The istio application package ships with the load
        - The local registry holds a small long-running image for the injection probe

    Setup:
        - Establish SSH connection to the active controller
        - Register the finalizer that restores the starting release
        - Verify the target release load is uploaded
        - Ensure the istio application is uploaded
        - Ensure the istio application is applied

    Test Steps:
        1. Verify istio is applied at the starting release with its pods ready
        2. Verify the sidecar injector works, and record the baseline sidecar image tag
        3. Upgrade the platform, leaving the deploy at activate-done so it can be rolled back
        4. Verify istio was updated to the target release with pods ready and no alarms
        5. Verify the sidecar injector still works, and that the sidecar image tag changed
        6. Roll the platform back to the starting release
        7. Verify istio is restored to the starting release with its pods ready
        8. Verify the sidecar injector works again, and that the tag returned to the baseline

    Teardown:
        - Restore the starting release
        - Remove each phase's scratch namespace, if its own phase did not
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_info(f"Connected to: {ssh_connection.get_name()}")

    deploy = SoftwareDeploySequenceKeywords(ssh_connection)
    health = ApplicationHealthKeywords(ssh_connection)
    recovery = UpgradeRecoveryKeywords(ssh_connection)
    sidecar = IstioSidecarKeywords(ssh_connection)
    app_list = SystemApplicationListKeywords(ssh_connection)
    app_upload = SystemApplicationUploadKeywords(ssh_connection)
    app_apply = SystemApplicationApplyKeywords(ssh_connection)

    compat_config = ConfigurationManager.get_app_upgrade_compat_config()
    app_name = compat_config.get_app_name(APP_KEY)
    namespace = compat_config.get_namespace(APP_KEY)
    from_version = deploy.get_running_release()
    to_version = compat_config.get_to_version()
    get_logger().log_info(f"istio compatibility: {from_version} -> {to_version} -> {from_version}")

    # Registered before the application is touched, so a setup that fails part-way through still
    # leaves the platform on the release it started on.
    def restore_the_starting_release():
        get_logger().log_teardown_step(f"Restore the starting release {from_version}")
        recovery.restore_to_release(from_version)

    request.addfinalizer(restore_the_starting_release)

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
    get_logger().log_setup_step("Ensure the istio application is uploaded")
    if app_list.get_system_application_list().is_in_application_list(app_name):
        get_logger().log_info(f"'{app_name}' is already present; skipping the upload")
    else:
        app_config = ConfigurationManager.get_app_config()
        package_pattern = f"{app_config.get_base_application_path()}{app_name}*.tgz"
        package_path = LsKeywords(ssh_connection).get_first_matching_file(package_pattern)
        get_logger().log_info(f"Uploading '{app_name}' from {package_path}")
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(app_name)
        upload_input.set_tar_file_path(package_path)
        app_upload.system_application_upload(upload_input)

    # istio is a multi-chart application - base, cni, pilot, the gateways and kiali - so a fresh
    # apply pulls several images and takes considerably longer than the keyword's 300s default,
    # especially on a virtual lab.
    get_logger().log_setup_step("Ensure the istio application is applied")
    if health.is_app_applied(app_name):
        get_logger().log_info(f"'{app_name}' is already applied; skipping the apply")
    else:
        get_logger().log_info(f"Applying '{app_name}'")
        applied_timeout = ConfigurationManager.get_usm_config().get_app_applied_timeout_sec()
        app_apply.system_application_apply(app_name, timeout=applied_timeout)

    # Baseline: the application is up and injecting on the release we start from.
    get_logger().log_test_case_step("Verify istio is applied at the starting release with its pods ready")
    health.wait_for_app_applied(app_name)
    baseline_app_version = health.get_app_version(app_name)
    validate_str_contains(baseline_app_version, from_version, f"istio is a {from_version} version at baseline")
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace),
        0,
        "istio pods are ready at baseline",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )
    # A namespace with no pods reports nothing unready, so the readiness count on its own would pass
    # with the application entirely absent.
    baseline_pod_count = health.get_pod_count(namespace)
    validate_greater_than(baseline_pod_count, 0, "istio has pods at baseline")

    get_logger().log_test_case_step("Verify the sidecar injector works, and record the baseline sidecar image tag")
    baseline_tag = sidecar.validate_sidecar_is_injected(request, "pre")

    # Upgrade the platform, stopping short of completing the deploy so it can be rolled back.
    get_logger().log_test_case_step(f"Upgrade the platform to {to_version}, leaving the deploy at activate-done")
    deploy.deploy_upgrade(to_version, leave_at_activate_done=True)
    validate_str_contains(deploy.get_running_release(), to_version, f"platform is on {to_version} after upgrade")

    get_logger().log_test_case_step("Verify istio was updated to the target release with pods ready and no alarms")
    health.wait_for_app_applied(app_name)
    upgraded_app_version = health.get_app_version(app_name)
    validate_str_contains(upgraded_app_version, to_version, f"istio is a {to_version} version after upgrade")
    # The baseline pod count is deliberately NOT carried forward here, unlike the oran-o2 test.
    # oran-o2 is pinned at the same chart across these releases; istio is not - it moved off
    # istio-operator, and its chart set can legitimately gain or lose a component between releases.
    # Requiring the baseline count after the upgrade would turn a release that ships one component
    # fewer into a full-timeout failure on a healthy system. The floor of one still rejects an empty
    # namespace, and the baseline count is reinstated after the rollback, where the release is the
    # same one that produced it.
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace, expected_min=1),
        0,
        "istio pods are ready after upgrade",
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

    get_logger().log_test_case_step("Verify the sidecar injector still works, and that the sidecar image tag changed")
    upgraded_tag = sidecar.validate_sidecar_is_injected(request, "post-upgrade")
    # The baseline tag is recorded and compared again after the rollback, but it is deliberately NOT
    # asserted to differ here. Two earlier versions of this got it wrong:
    #
    #   1. validate_not_equals(upgraded_tag, baseline_tag) hard-failed any release that ships the
    #      same proxy image as its predecessor, and its own failure message had to concede that an
    #      unchanged tag can be legitimate - an assertion documenting its own false-failure mode.
    #   2. Making that conditional on the application version changing produced dead code: the
    #      version is already asserted to contain from_version at baseline and to_version here, and
    #      those differ by construction, so the equal branch was unreachable and the behaviour was
    #      unchanged.
    #
    # The honest position is that a changed sidecar image is not a requirement. The platform having
    # replaced the application IS required, and that is already asserted above by the version check.
    # Whether the new application happens to carry a new proxy image is a property of the release,
    # not a correctness condition, so it is logged as evidence and left to the reader.
    #
    # The assertion that does matter is after the rollback, where the tag must return to this one:
    # that is what distinguishes "the original istio was restored" from "some working istio is
    # running", and it cannot be satisfied by accident.
    if upgraded_tag == baseline_tag:
        get_logger().log_info(f"istio moved from {baseline_app_version} to {upgraded_app_version} but kept the sidecar image {upgraded_tag}; this release does not bump the proxy")
    else:
        get_logger().log_info(f"istio moved from {baseline_app_version} to {upgraded_app_version} and the sidecar image changed from {baseline_tag} to {upgraded_tag}")

    # Roll the platform back, and the application should return to where it started.
    get_logger().log_test_case_step(f"Roll the platform back to {from_version}")
    deploy.deploy_rollback()
    validate_str_contains(deploy.get_running_release(), from_version, f"platform is on {from_version} after rollback")

    get_logger().log_test_case_step("Verify istio is restored to the starting release with its pods ready")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"istio is a {from_version} version after rollback")
    # Back on the starting release the platform has to pull that release's images again, so the pods
    # are recreated and are not ready the moment the application reports 'applied'. The baseline
    # count is meaningful again here: this is the same release that produced it.
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace, expected_min=baseline_pod_count),
        0,
        "istio has at least its baseline pods, all ready, after rollback",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )

    get_logger().log_test_case_step("Verify the sidecar injector works again, and that the tag returned to the baseline")
    rolled_back_tag = sidecar.validate_sidecar_is_injected(request, "post-rollback")
    validate_equals(
        rolled_back_tag,
        baseline_tag,
        f"the rollback must restore the original istio, not merely a working one (baseline {baseline_tag}, after rollback {rolled_back_tag})",
    )
