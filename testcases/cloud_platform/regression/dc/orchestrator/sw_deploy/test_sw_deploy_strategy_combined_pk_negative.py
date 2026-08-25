"""Combined Platform & Kubernetes sw-deploy-strategy negative tests.

This module validates negative scenarios for the combined P&K sw-deploy-strategy
at the dcmanager level, where strategy creation or build is expected to fail with
a clear error. Everything is driven through dcmanager (create/apply) against a DC
subcloud; the VIM (sw-manager) strategy is built by dcmanager, so the tests never
talk to sw-manager directly.

Background:
    The happy-path automation for combined P&K sw-deploy-strategy is covered
    elsewhere. This module covers negative scenarios where strategy creation or
    build should fail with a clear, validated error message.

Test cases:
    - test_combined_pk_invalid_kube_version: invalid K8s version -> create is
      accepted on an out-of-date subcloud (with --with-prestage), then the VIM
      strategy build fails; dcmanager reports "Failed to create VIM strategy"
    - test_combined_pk_invalid_release: invalid release -> create is rejected
      immediately (SystemController-side check) with reason
      "Release ID: fake-release-99.99 not found or not deployed"
    - test_combined_pk_kube_version_lower_than_active: lower (downgrade) K8s
      version -> create is accepted (with --with-prestage), then the VIM
      strategy build fails; dcmanager reports "Failed to create VIM strategy"
    - test_combined_pk_kube_version_same_as_active: same K8s version -> create
      is accepted (with --with-prestage), then the VIM strategy build fails;
      dcmanager reports "Failed to create VIM strategy"
    - test_combined_pk_rollback_with_delete_rejected:
      --rollback and --with-delete are mutually exclusive -> command rejected

Note:
    The build-failure scenarios (invalid / same-as-active kube version) are only
    meaningful against an out-of-date (N-1 or N-2) subcloud. On an in-sync (N)
    subcloud the create is rejected up front with "does not require software
    update", so those tests target an N-1 subcloud.

Prerequisites:
    - System controller has N release deployed
    - Active Kubernetes version is known on the system controller
    - Lab has an online N-1 subcloud
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords

# --- Constants ---

INVALID_KUBE_VERSION = "v99.99.0"
INVALID_RELEASE = "fake-release-99.99"
FAILED_STATE = "failed"

# Expected strategy-step failure-reason substrings surfaced by dcmanager.
#
# For invalid / same-as-active kube versions, the detailed VIM reason (e.g.
# "Invalid to_version value") lives on the subcloud's VIM layer and is torn down
# as soon as the build fails, so it is not reliably observable. At the dcmanager
# level the strategy-step details consistently contain the VIM-build failure
# phrase below, which is the stable signal we assert on. The full observed
# details string is of the form:
#   "create VIM sw-deploy strategy: Failed for subcloud <name>: VIM strategy
#    build failed: {'completed': False, 'reason': ''} State: build-failed
#    Strategy: sw-upgrade"
REASON_VIM_BUILD_FAILED = "VIM strategy build failed"
REASON_RELEASE_NOT_FOUND = f"Release ID: {INVALID_RELEASE} not found or not deployed"

# Expected rejection substring for the dcmanager rollback + with-delete case.
# The dcmanager CLI reports: "Option --delete cannot be used with any of the
# following options: --rollback or --cleanup." Matched in lowercase.
REASON_ROLLBACK_WITH_DELETE = "cannot be used with"


# --- Helper Functions ---


def cleanup_dc_strategy(ssh_connection: SSHConnection) -> None:
    """Delete the dcmanager sw-deploy-strategy if it exists.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
    """
    get_logger().log_teardown_step("Delete dcmanager sw-deploy-strategy")
    DcmanagerStrategyCleanupKeywords(ssh_connection).cleanup_strategy("sw-deploy")


def get_sysadmin_password() -> str:
    """Return the sysadmin password from the lab config.

    Returns:
        str: The sysadmin password used for the --with-prestage strategy option.
    """
    return ConfigurationManager.get_lab_config().get_admin_credentials().get_password()


def assert_strategy_step_failed_with_reason(ssh_connection: SSHConnection, subcloud_name: str, expected_reason: str, description: str) -> None:
    """Apply the dcmanager strategy and assert the subcloud step fails with a reason.

    The strategy is applied without waiting for completion; the strategy-step is
    then polled until it reaches the 'failed' state and the details field is
    validated against the expected reason substring.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Subcloud whose strategy-step is being validated.
        expected_reason (str): Substring expected in the strategy-step details.
        description (str): Validation description for logging.
    """
    strategy_keywords = DcmanagerSwDeployStrategy(ssh_connection)

    get_logger().log_test_case_step("Apply the sw-deploy strategy (expect failure)")
    strategy_keywords.dcmanager_sw_deploy_strategy_apply(subcloud_name, wait_completion=False)

    step_keywords = DcmanagerStrategyStepKeywords(ssh_connection)
    # The strategy-step is expected to fail while building the VIM strategy (an
    # invalid / same-as-active kube target is caught there), which happens before
    # prestage/software-deploy. Allow generous headroom in case the build phase
    # is slow to report the failure.
    strategy_step = step_keywords.wait_for_strategy_step_state(subcloud_name, states=[FAILED_STATE], timeout=900)
    validate_equals(strategy_step.get_state(), FAILED_STATE, f"Strategy step reached failed state ({description})")

    details = strategy_step.get_details() or ""
    get_logger().log_info(f"Strategy-step failure details: {details}")
    validate_str_contains(details, expected_reason, description)


# --- dcmanager-level Negative Tests (DC subcloud) ---


@mark.p3
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_invalid_kube_version(request):
    """Verify combined P&K strategy build fails for an invalid K8s version.

    CLI: dcmanager sw-deploy-strategy create <subcloud> --release-id <release> --kube-upgrade v99.99.0

    Preconditions:
        - System controller has N release deployed
        - Lab has an online subcloud

    Test Steps:
        1. Pick an eligible subcloud and resolve the deployed release
        2. Create sw-deploy-strategy (--with-prestage) with an invalid --kube-upgrade version
        3. Apply and validate the subcloud strategy-step fails; dcmanager reports
           "Failed to create VIM strategy" (the VIM build rejects the invalid version)

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load="N-1",
    )
    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_dc_strategy(system_controller_ssh))

    releases = SoftwareListKeywords(system_controller_ssh).get_software_list().get_release_name_by_state("deployed")
    validate_equals(len(releases) > 0, True, "At least one deployed release found")
    release = max(releases)

    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    get_logger().log_test_case_step(f"Create combined P&K strategy for {subcloud_name} with invalid kube version {INVALID_KUBE_VERSION}")
    # NOTE: On an N-1/N-2 subcloud the create is ACCEPTED; the invalid kube
    # version is only rejected later, at VIM strategy build. On an in-sync (N)
    # subcloud the create is instead rejected with "does not require software
    # update", so this scenario is only meaningful against a behind subcloud.
    # --with-prestage is required so the apply gets past the sw-deploy pre-check
    # (which otherwise fails with "Release ... is not prestaged") and actually
    # reaches the kube-version validation at build.
    strategy_keywords.dcmanager_sw_deploy_strategy_create(
        subcloud_name=subcloud_name,
        release=release,
        kube_upgrade=INVALID_KUBE_VERSION,
        with_prestage=True,
        sysadmin_password=get_sysadmin_password(),
    )

    get_logger().log_test_case_step("Validate strategy build failed (VIM strategy build rejected the invalid kube version)")
    assert_strategy_step_failed_with_reason(
        system_controller_ssh,
        subcloud_name,
        REASON_VIM_BUILD_FAILED,
        "Build failed: VIM strategy could not be created for the invalid kube version",
    )


@mark.p3
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_invalid_release(request):
    """Verify combined P&K strategy create is rejected for an invalid release.

    CLI: dcmanager sw-deploy-strategy create <subcloud> --release-id fake-release-99.99 --kube-upgrade <active>

    Unlike the invalid-kube-version case, an invalid release id is validated
    against the SystemController's release inventory at create time, so the
    create command is rejected immediately (even on an out-of-date subcloud)
    rather than failing later at build.

    Preconditions:
        - System controller has an active K8s version
        - Lab has an N-1 subcloud (out-of-date, so the target is meaningful)

    Test Steps:
        1. Pick an eligible N-1 subcloud and resolve the active K8s version
        2. Attempt to create the sw-deploy-strategy with an invalid release id
        3. Validate the create command is rejected with reason
           "Release ID: fake-release-99.99 not found or not deployed"

    Teardown:
        - Delete strategy if any was created
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load="N-1",
    )
    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_dc_strategy(system_controller_ssh))

    active_versions = SystemKubernetesListKeywords(system_controller_ssh).get_kubernetes_versions_by_state("active")
    validate_equals(len(active_versions) > 0, True, "Active Kubernetes version found")
    kube_version = max(active_versions)

    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    get_logger().log_test_case_step(f"Attempt to create combined P&K strategy for {subcloud_name} with invalid release {INVALID_RELEASE} (expect rejection)")
    output = strategy_keywords.dcmanager_sw_deploy_strategy_create_with_error(
        subcloud_name=subcloud_name,
        release=INVALID_RELEASE,
        kube_upgrade=kube_version,
    )

    get_logger().log_test_case_step("Validate create was rejected with release-not-found reason")
    validate_str_contains(output, REASON_RELEASE_NOT_FOUND, "Create rejected: release not found or not deployed")


@mark.p3
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_kube_version_lower_than_active(request):
    """Verify combined P&K strategy build fails for a K8s version lower than active.

    CLI: dcmanager sw-deploy-strategy create <subcloud> --release-id <release> --kube-upgrade v1.32.2

    This scenario is a downgrade attempt (target K8s version lower than the
    subcloud's active one). It historically triggered a VIM crash loop that
    required manual DB cleanup; the strategy build is expected to reject the
    downgrade. Like the other build-failure scenarios it targets an N-1 subcloud
    and uses --with-prestage so the apply reaches the VIM strategy build.

    Preconditions:
        - System controller has N release deployed
        - The subcloud has a Kubernetes version lower than its active one
          (in the 'unavailable' state) to use as the downgrade target
        - Lab has an N-1 subcloud

    Test Steps:
        1. Pick an eligible N-1 subcloud and resolve the deployed release
        2. Create sw-deploy-strategy (--with-prestage) with a lower --kube-upgrade version
        3. Apply and validate the subcloud strategy-step fails; dcmanager reports
           "Failed to create VIM strategy" (the VIM build rejects the downgrade)

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load="N-1",
    )
    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_dc_strategy(system_controller_ssh))

    releases = SoftwareListKeywords(system_controller_ssh).get_software_list().get_release_name_by_state("deployed")
    validate_equals(len(releases) > 0, True, "At least one deployed release found")
    release = max(releases)
    # The upgrade runs on the subcloud, so resolve the downgrade target from the
    # subcloud's own kube-version-list (its active version may differ from the
    # system controller's). KubernetesVersionListOutput owns the selection logic.
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    lower_version = SystemKubernetesListKeywords(subcloud_ssh).get_system_kube_version_list().get_highest_version_lower_than_active()

    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    get_logger().log_test_case_step(f"Create combined P&K strategy for {subcloud_name} with lower kube version {lower_version}")
    strategy_keywords.dcmanager_sw_deploy_strategy_create(
        subcloud_name=subcloud_name,
        release=release,
        kube_upgrade=lower_version,
        with_prestage=True,
        sysadmin_password=get_sysadmin_password(),
    )

    get_logger().log_test_case_step("Validate strategy build failed (VIM strategy build rejected the lower kube version)")
    assert_strategy_step_failed_with_reason(
        system_controller_ssh,
        subcloud_name,
        REASON_VIM_BUILD_FAILED,
        "Build failed: VIM strategy could not be created for the lower kube version",
    )


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_kube_version_same_as_active(request):
    """Verify combined P&K strategy is rejected for a K8s version equal to active.

    CLI: dcmanager sw-deploy-strategy create <subcloud> --release-id <release> --kube-upgrade <active_version>

    Preconditions:
        - System controller has N release deployed
        - Active K8s version is known
        - Lab has an online subcloud

    Test Steps:
        1. Pick an eligible N-1 subcloud and resolve the deployed release
        2. Resolve the subcloud's own active K8s version
        3. Create sw-deploy-strategy (--with-prestage) targeting that same version
        4. Apply and validate the subcloud strategy-step fails; dcmanager reports
           "Failed to create VIM strategy" (the VIM build rejects the no-op upgrade)

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load="N-1",
    )
    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_dc_strategy(system_controller_ssh))

    releases = SoftwareListKeywords(system_controller_ssh).get_software_list().get_release_name_by_state("deployed")
    validate_equals(len(releases) > 0, True, "At least one deployed release found")
    release = max(releases)

    # "Same as active" must be the SUBCLOUD's active K8s version, not the system
    # controller's. Targeting the SC active would be a valid upgrade for an N-1
    # subcloud rather than a no-op.
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    active_versions = SystemKubernetesListKeywords(subcloud_ssh).get_kubernetes_versions_by_state("active")
    validate_equals(len(active_versions) > 0, True, "Active Kubernetes version found on subcloud")
    active_version = max(active_versions)

    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    get_logger().log_test_case_step(f"Create combined P&K strategy for {subcloud_name} with same kube version {active_version}")
    strategy_keywords.dcmanager_sw_deploy_strategy_create(
        subcloud_name=subcloud_name,
        release=release,
        kube_upgrade=active_version,
        with_prestage=True,
        sysadmin_password=get_sysadmin_password(),
    )

    get_logger().log_test_case_step("Validate strategy build failed (VIM strategy build rejected the same-as-active kube version)")
    assert_strategy_step_failed_with_reason(
        system_controller_ssh,
        subcloud_name,
        REASON_VIM_BUILD_FAILED,
        "Build failed: VIM strategy could not be created for the same-as-active kube version",
    )


@mark.p3
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_combined_pk_rollback_with_delete_rejected(request):
    """Verify dcmanager rejects --rollback combined with --with-delete.

    CLI: dcmanager sw-deploy-strategy create --rollback --with-delete <subcloud>

    These options are mutually exclusive (rollback requires the LVM/ETCD snapshots
    that --with-delete would have already removed); the create command should be
    rejected immediately with a clear error message.

    Preconditions:
        - Lab has an online subcloud

    Test Steps:
        1. Pick an eligible subcloud
        2. Attempt create with both --rollback and --with-delete
        3. Validate the command is rejected with a mutually-exclusive error

    Teardown:
        - Delete strategy if any was created
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_dc_strategy(system_controller_ssh))

    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    get_logger().log_test_case_step(f"Attempt rollback + with-delete create for subcloud {subcloud_name} (expect rejection)")
    output = strategy_keywords.dcmanager_sw_deploy_strategy_create_with_error(
        subcloud_name=subcloud_name,
        rollback=True,
        with_delete=True,
    )

    get_logger().log_test_case_step("Validate rejection error message")
    validate_str_contains(
        output.lower(),
        REASON_ROLLBACK_WITH_DELETE,
        "Rollback and with-delete reported as mutually exclusive",
    )
