"""metrics-server platform-upgrade compatibility test.

Verify that metrics-server stays applied at the expected release, with healthy pods, serving the
Metrics API, and no alarms, across a platform release upgrade and rollback. The scope is the applied
state of the application and the API it serves: whether the platform carries it forward to the new
release and restores it on the way back, and whether the aggregated Metrics API is still serving at
each step.

metrics-server is updated in place by the platform during deploy activate; it is not removed first.
Its metadata sets auto_update, platform_managed_app and maintain_user_overrides and declares no
desired-state override, so the auto-update path is the whole procedure and there is no
remove-before-upgrade variant to cover separately.

The application is ensured to be uploaded and applied as a setup step rather than assumed, because a
lab can legitimately have it absent: it ships bundled on the load but a freshly installed system does
not necessarily have it uploaded. Both setup calls are guarded and do nothing when the application is
already in place. The generic application-apply keyword is used, because metrics-server has no custom
override keyword and its system overrides are empty.

Pod health alone does not prove metrics-server is doing its job. Its single Deployment can be Running
and Ready while the v1beta1.metrics.k8s.io APIService reports Available=False - an aggregation-layer,
serving-certificate or kubelet-TLS problem - in which case `kubectl top` and every HPA that depends on
it are broken although the pod looks healthy. So each phase also runs a read-only Metrics-API serving
check: the APIService is Available, `kubectl top nodes` returns a real node reading, and
`kubectl top pods` returns a real pod reading.

The version assertions compare against the release the platform reports rather than a pinned build.
Deploy activate installs whatever application build ships with the target load, so matching on the
release is what makes this test independent of which respin the lab was installed from.

The release the system starts on comes from the platform itself, so this one test case covers both
the one-release-back and two-releases-back paths: the body is identical and only the starting release
differs, which is decided by the release the lab was installed with.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry, validate_greater_than, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.metrics_server_api_keywords import MetricsServerApiKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

# Key for this application's block in the app-upgrade-compat config, which supplies the platform
# application name and the namespace. Read from config rather than held here so the application's
# identity lives in one place across the compatibility tests, as it does for cert-manager, oran-o2
# and istio.
APP_KEY = "metrics-server"
# The application package that ships with the load. Matched by pattern rather than by a pinned file
# name so the test does not have to know the build number of the load the lab was installed from.
# Confirmed to match exactly one bundled package on the load.
APP_PACKAGE_PATTERN = "/usr/local/share/applications/helm/*metrics-server*"
# The application reports 'applied' before its pod is serving: the platform has to pull the image
# for the release it just moved to, and the Metrics API aggregation layer settles after that. Waited
# for rather than sampled once.
POD_READY_TIMEOUT = 900
POD_READY_POLL_INTERVAL = 15


@mark.p2
def test_metrics_server_upgrade_rollback(request):
    """Verify metrics-server stays applied and serving across a platform upgrade and rollback.

    Preconditions:
        - Target system is accessible
        - The target release load is uploaded, so the deploy can resolve it
        - The metrics-server application package is present on the load

    Setup:
        - Establish SSH connection to the active controller
        - Register the finalizer that restores the starting release
        - Verify the target release load is uploaded
        - Ensure the metrics-server application is uploaded
        - Ensure the metrics-server application is applied

    Test Steps:
        1. Verify metrics-server is applied at the starting release with its pods ready
        2. Verify the Metrics API is serving at the starting release
        3. Upgrade the platform, leaving the deploy at activate-done so it can be rolled back
        4. Verify metrics-server was updated to the target release with pods ready and no alarms
        5. Verify the Metrics API is serving at the target release
        6. Roll the platform back to the starting release
        7. Verify metrics-server is restored to the starting release with its pods ready
        8. Verify the Metrics API is serving again at the starting release

    Teardown:
        - Restore the starting release
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_info(f"Connected to: {ssh_connection.get_name()}")

    deploy = SoftwareDeploySequenceKeywords(ssh_connection)
    health = ApplicationHealthKeywords(ssh_connection)
    recovery = UpgradeRecoveryKeywords(ssh_connection)
    metrics_api = MetricsServerApiKeywords(ssh_connection)
    app_list = SystemApplicationListKeywords(ssh_connection)
    app_upload = SystemApplicationUploadKeywords(ssh_connection)
    app_apply = SystemApplicationApplyKeywords(ssh_connection)

    compat_config = ConfigurationManager.get_app_upgrade_compat_config()
    app_name = compat_config.get_app_name(APP_KEY)
    namespace = compat_config.get_namespace(APP_KEY)
    from_version = deploy.get_running_release()
    to_version = compat_config.get_to_version()
    get_logger().log_info(f"metrics-server compatibility: {from_version} -> {to_version} -> {from_version}")

    # Registered before the application is touched, so a setup that fails part-way through still
    # leaves the platform on the release it started on.
    def restore_the_starting_release():
        get_logger().log_teardown_step(f"Restore the starting release {from_version}")
        recovery.restore_to_release(from_version)

    request.addfinalizer(restore_the_starting_release)

    # Checked here rather than left to the upgrade step, which is where the resolution would
    # otherwise happen. Without the target load this test cannot do anything useful, and the
    # baseline verification ahead of the upgrade takes long enough that discovering it there wastes
    # the run. Resolving it now fails in seconds with the message naming what to upload, and logs
    # the release ID the upgrade will be given.
    get_logger().log_setup_step("Verify the target release load is uploaded")
    target_release_id = deploy.get_release_id_for_version(to_version)
    get_logger().log_info(f"Target load resolved to '{target_release_id}'")

    # Presence is read from the application list rather than through is_already_uploaded, which
    # reports False for an application that is already applied. Force is deliberately not set on
    # the upload: it would remove and delete an application that is already in place, which is the
    # opposite of what a guard is for.
    get_logger().log_setup_step("Ensure the metrics-server application is uploaded")
    if app_list.get_system_application_list().is_in_application_list(app_name):
        get_logger().log_info(f"'{app_name}' is already present; skipping the upload")
    else:
        package_path = LsKeywords(ssh_connection).get_first_matching_file(APP_PACKAGE_PATTERN)
        get_logger().log_info(f"Uploading '{app_name}' from {package_path}")
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(app_name)
        upload_input.set_tar_file_path(package_path)
        app_upload.system_application_upload(upload_input)

    get_logger().log_setup_step("Ensure the metrics-server application is applied")
    if health.is_app_applied(app_name):
        get_logger().log_info(f"'{app_name}' is already applied; skipping the apply")
    else:
        get_logger().log_info(f"Applying '{app_name}'")
        applied_timeout = ConfigurationManager.get_usm_config().get_app_applied_timeout_sec()
        app_apply.system_application_apply(app_name, timeout=applied_timeout)

    # Baseline: the application is up on the release we start from.
    get_logger().log_test_case_step("Verify metrics-server is applied at the starting release with its pods ready")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"metrics-server is a {from_version} version at baseline")
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace),
        0,
        "metrics-server pods are ready at baseline",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )
    # A namespace with no pods reports nothing unready, so the readiness count on its own would pass
    # with the application entirely absent. The baseline count is carried into the later waits.
    baseline_pod_count = health.get_pod_count(namespace)
    validate_greater_than(baseline_pod_count, 0, "metrics-server has pods at baseline")

    get_logger().log_test_case_step("Verify the Metrics API is serving at the starting release")
    metrics_api.validate_metrics_api_is_serving("pre")

    # Upgrade the platform, stopping short of completing the deploy so it can be rolled back.
    get_logger().log_test_case_step(f"Upgrade the platform to {to_version}, leaving the deploy at activate-done")
    deploy.deploy_upgrade(to_version, leave_at_activate_done=True)
    validate_str_contains(deploy.get_running_release(), to_version, f"platform is on {to_version} after upgrade")

    # The application should have been carried forward by the platform.
    get_logger().log_test_case_step("Verify metrics-server was updated to the target release with pods ready and no alarms")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), to_version, f"metrics-server is a {to_version} version after upgrade")
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace, expected_min=baseline_pod_count),
        0,
        "metrics-server has at least its baseline pods, all ready, after upgrade",
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

    get_logger().log_test_case_step("Verify the Metrics API is serving at the target release")
    metrics_api.validate_metrics_api_is_serving("post-upgrade")

    # Roll the platform back, and the application should return to where it started.
    get_logger().log_test_case_step(f"Roll the platform back to {from_version}")
    deploy.deploy_rollback()
    validate_str_contains(deploy.get_running_release(), from_version, f"platform is on {from_version} after rollback")

    get_logger().log_test_case_step("Verify metrics-server is restored to the starting release with its pods ready")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"metrics-server is a {from_version} version after rollback")
    # Back on the starting release the platform has to pull that release's image again, so the pod
    # is recreated and is not ready the moment the application reports 'applied'.
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace, expected_min=baseline_pod_count),
        0,
        "metrics-server has at least its baseline pods, all ready, after rollback",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )

    get_logger().log_test_case_step("Verify the Metrics API is serving again at the starting release")
    metrics_api.validate_metrics_api_is_serving("post-rollback")
