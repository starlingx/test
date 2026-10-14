"""dell-storage platform-upgrade compatibility test.

Verify that dell-storage is carried forward by the platform across a platform release upgrade and
rollback: applied, at the expected release build, with its pods ready and no application or deploy
alarms raised. The question is not whether the CSI driver pods restart, but whether the platform
still has the application applied and serving on the new release, and again once the platform is
rolled back.

dell-storage is updated in place by the platform during deploy activate; it is not removed first.
Its metadata sets auto_update and platform_managed_app, so the auto-update path is the whole
procedure and there is no remove-before-upgrade variant to cover separately.

What makes this application different from the rest of this suite, and what every precondition
below exists for: its metadata sets desired_state 'uploaded', so the platform uploads it but never
applies it. An applied dell-storage is therefore a property of the lab, established before this
test runs, and never something this test creates.

Lab preconditions, which this test does not create and deliberately does not attempt to:
    - The storage configuration declares a reachable PowerStore array, so that the application's
      helm overrides carry an array entry marked as the default one. This is a configuration
      prerequisite rather than a hardware one: the driver's default-array lookup is a
      control-plane call to the array's management endpoint, and the node DaemonSet runs on the
      host network, so it reaches that endpoint over the host's own default route. A plain virtual
      lab with the array declared therefore satisfies it, with no storage hardware attached and no
      storage cabling. What the configuration must supply is reachability of the management
      endpoint and an entry marked as the default; what it does not have to supply is a local
      appliance.
      Without a default array declared, the node driver cannot resolve one, its containers
      crash-loop, and the apply runs the helm release's full timeout before failing and leaving an
      application-apply alarm standing. That failure takes tens of minutes to arrive and has
      nothing to do with a platform upgrade, so this test refuses to start rather than
      re-discovering it: the applied state is asserted up front and the run stops in seconds if it
      is absent.
    - dell-storage applied against that array. Applying it, and the helm overrides that make an
      apply possible, belong to the lab bring-up that runs before this test, not to this test. A
      self-provisioning precondition here would hide the failure of whatever was supposed to
      establish the baseline, and on a lab without the array declared it would guarantee the long
      failure rather than avoid it.
    - The target release load is uploaded, so the deploy can resolve it, and that load carries the
      dell-storage application package.

The data path is a separate matter and is not a precondition here. Volume operations - iSCSI or
NFS traffic to the array's data network - do need a lab with the storage interface and the L2 path
to reach it, which a virtual lab does not have. This test never performs a volume operation, so
that boundary does not touch it; a test that writes to a claim is a different test with a
different lab requirement.

Scope is the platform-carried state of the application: applied, at the right release build, with
ready pods and no alarms. Verifying that the driver can serve a volume - creating a claim, writing
to it, reading it back - is a storage-function question with its own coverage and its own lab
requirements, and is not asserted here.

Readiness is compared as ready against total containers rather than against a container count. The
shipped overrides disable several of the driver's optional sidecars, so the number of containers a
pod runs is a property of the release's overrides rather than a correctness condition, and
asserting it would turn an override change into a test failure.

The release the system starts on comes from the platform itself, so this one test case covers both
the one-release-back and two-releases-back paths: the body is identical and only the starting
release differs, which is decided by the release the lab was installed with.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry, validate_greater_than, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords
from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

# Key for this application's block in the app-upgrade-compat config, which supplies the platform
# application name and the namespace. Read from config rather than held here so the application's
# identity lives in one place across the compatibility tests, as it does for cert-manager, oran-o2
# and istio.
APP_KEY = "app-dell-storage"
# The application reports 'applied' before its pods are serving: the platform has to pull the images
# for the release it just moved to, and the node driver registers with the kubelet after that.
# Waited for rather than sampled once.
POD_READY_TIMEOUT = 900
POD_READY_POLL_INTERVAL = 15


@mark.p2
# Expresses "this lab declares a reachable default array and dell-storage is applied against it",
# which is configuration rather than attached hardware - see the module docstring. The marker
# filters a lab that does not meet it out of the run instead of failing it there.
@mark.lab_dell_storage
def test_dell_storage_upgrade_rollback(request: FixtureRequest):
    """Verify dell-storage survives a platform upgrade and rollback applied, with its pods ready.

    Preconditions:
        - Target system is accessible
        - The storage configuration declares a reachable PowerStore array, supplying an array
          entry marked as the default one. A configuration prerequisite, not attached hardware
        - dell-storage is applied against that array, established by the lab bring-up that runs
          before this test
        - The target release load is uploaded, so the deploy can resolve it
        - The target release load carries the dell-storage application package

    Setup:
        - Establish SSH connection to the active controller
        - Register the finalizer that restores the starting release
        - Verify dell-storage is applied, and stop here if it is not
        - Verify the target release load is uploaded
        - Verify the load carries the dell-storage application package

    Test Steps:
        1. Verify dell-storage is applied at the starting release with its pods ready
        2. Upgrade the platform, leaving the deploy at activate-done so it can be rolled back
        3. Verify dell-storage was updated to the target release with pods ready and no alarms
        4. Roll the platform back to the starting release
        5. Verify dell-storage is restored to the starting release with its pods ready

    Teardown:
        - Restore the starting release
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_info(f"Connected to: {ssh_connection.get_name()}")

    deploy = SoftwareDeploySequenceKeywords(ssh_connection)
    health = ApplicationHealthKeywords(ssh_connection)
    recovery = UpgradeRecoveryKeywords(ssh_connection)
    app_list = SystemApplicationListKeywords(ssh_connection)

    compat_config = ConfigurationManager.get_app_upgrade_compat_config()
    app_name = compat_config.get_app_name(APP_KEY)
    namespace = compat_config.get_namespace(APP_KEY)
    from_version = deploy.get_running_release()
    to_version = compat_config.get_to_version()
    get_logger().log_info(f"dell-storage compatibility: {from_version} -> {to_version} -> {from_version}")

    # Registered before anything is touched. It reads as inverted against the precondition below,
    # which changes nothing and so has nothing to restore, and it is kept this way deliberately:
    # restore_to_release no-ops when the platform is already on the starting release with no deploy
    # open, so registering it first costs nothing, and it removes the possibility of a later edit
    # inserting a state change above the finalizer.
    def restore_the_starting_release():
        get_logger().log_teardown_step(f"Restore the starting release {from_version}")
        recovery.restore_to_release(from_version)

    request.addfinalizer(restore_the_starting_release)

    # A read, not a wait, and the first thing the test does. Unlike every other application in this
    # suite, dell-storage sets desired_state 'uploaded', so the platform never applies it: an
    # applied dell-storage is the lab's product and this test neither creates it nor waits for it.
    # Discovering a missing baseline through wait_for_app_applied instead would spend that whole
    # budget on a system that was never going to reach 'applied', and an apply attempted without a
    # reachable array fails only after the helm release's full timeout. timeout=0 makes this a
    # single read, and the failure_values list makes a wrong baseline fail fast naming the status
    # it found rather than polling for a state nothing is going to produce. This test provisions
    # nothing: establishing the applied baseline is the lab bring-up's job, not this test's.
    get_logger().log_setup_step("Verify dell-storage is applied, and stop here if it is not")
    app_list.validate_app_status(app_name, "applied", timeout=0, failure_values=("uploaded", "apply-failed", "remove-failed"))

    # Resolved now rather than at the upgrade step. Without the target load this test can do nothing
    # useful, and the baseline verification ahead of the upgrade takes long enough that discovering
    # it there wastes the run. Resolving it here fails in seconds with the message naming what to
    # upload, and logs the release ID the upgrade will be given.
    get_logger().log_setup_step("Verify the target release load is uploaded")
    target_release_id = deploy.get_release_id_for_version(to_version)
    get_logger().log_info(f"Target load resolved to '{target_release_id}'")

    # A resolvable release says nothing about which application packages ship inside it, and an
    # application missing from a load is a failure this suite has been bitten by. It surfaces late
    # and confusingly: the deploy succeeds, and only the post-upgrade version assertion fails,
    # after the whole upgrade has run. Checking the package is present names the problem instead.
    get_logger().log_setup_step("Verify the load carries the dell-storage application package")
    package_pattern = f"{ConfigurationManager.get_app_config().get_base_application_path()}{app_name}*.tgz"
    package_path = LsKeywords(ssh_connection).get_first_matching_file(package_pattern)
    validate_str_contains(package_path, app_name, f"the load carries a '{app_name}' application package matching {package_pattern}")

    # Baseline: the application is applied and serving on the release we start from.
    get_logger().log_test_case_step("Verify dell-storage is applied at the starting release with its pods ready")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"dell-storage is a {from_version} version at baseline")
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace),
        0,
        "dell-storage pods are ready at baseline",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )
    # A namespace with no pods reports nothing unready, so the readiness count on its own would pass
    # with the application entirely absent - and for an application whose desired state is
    # 'uploaded', present-but-not-applied is the likeliest wrong baseline there is. The count
    # observed here is carried into the later waits as the floor, rather than a literal: it was
    # measured as 2 on a single-node system, the controller Deployment plus the node DaemonSet, but
    # the controller replica count follows the number of provisioned controllers, so a system with
    # more of them legitimately has more pods and a hardcoded 2 would pass with half the
    # application missing.
    baseline_pod_count = health.get_pod_count(namespace)
    validate_greater_than(baseline_pod_count, 0, "dell-storage has pods at baseline")
    get_logger().log_info(f"Baseline pod count in namespace '{namespace}': {baseline_pod_count}")

    # Upgrade the platform, stopping short of completing the deploy so it can be rolled back.
    get_logger().log_test_case_step(f"Upgrade the platform to {to_version}, leaving the deploy at activate-done")
    deploy.deploy_upgrade(to_version, leave_at_activate_done=True)
    validate_str_contains(deploy.get_running_release(), to_version, f"platform is on {to_version} after upgrade")

    get_logger().log_test_case_step("Verify dell-storage was updated to the target release with pods ready and no alarms")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), to_version, f"dell-storage is a {to_version} version after upgrade")
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace, expected_min=baseline_pod_count),
        0,
        "dell-storage has at least its baseline pods, all ready, after upgrade",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )
    # Retried rather than sampled once: a post-activate alarm can still be clearing at the moment
    # the application first reports 'applied'.
    validate_equals_with_retry(
        health.get_app_or_deploy_alarm_count,
        0,
        "no application or deploy alarms after upgrade",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )

    # Roll the platform back, and the application should return to where it started.
    get_logger().log_test_case_step(f"Roll the platform back to {from_version}")
    deploy.deploy_rollback()
    validate_str_contains(deploy.get_running_release(), from_version, f"platform is on {from_version} after rollback")

    get_logger().log_test_case_step("Verify dell-storage is restored to the starting release with its pods ready")
    health.wait_for_app_applied(app_name)
    validate_str_contains(health.get_app_version(app_name), from_version, f"dell-storage is a {from_version} version after rollback")
    # Back on the starting release the platform has to pull that release's images again, so the pods
    # are recreated and are not ready the moment the application reports 'applied'. The baseline
    # count is meaningful again here: this is the same release that produced it.
    validate_equals_with_retry(
        lambda: health.get_not_ready_pod_count(namespace, expected_min=baseline_pod_count),
        0,
        "dell-storage has at least its baseline pods, all ready, after rollback",
        timeout=POD_READY_TIMEOUT,
        polling_sleep_time=POD_READY_POLL_INTERVAL,
    )
