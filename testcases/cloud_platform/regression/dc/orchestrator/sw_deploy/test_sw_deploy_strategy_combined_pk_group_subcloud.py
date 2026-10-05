"""Combined Platform & Kubernetes sw-deploy-strategy - Subcloud Group orchestration tests.

Applies a combined platform and Kubernetes sw-deploy strategy (--kube-upgrade)
to a subcloud group and verifies that every member completes, using the
centralized DcManagerSubcloudStateWatcherKeywords to monitor strategy-step
progress across all members (no inline strategy-step polling).

This is the group-scope counterpart of
test_sw_deploy_strategy_combined_pk_single_subcloud.py and covers the same mode
matrix, minus the simplex/duplex axis: a group is built from whatever online,
out-of-sync subclouds the lab has, so its members cannot be constrained to one
system type.

Supported modes:
    - Upgrade: --kube-upgrade [version] --release-id [release] --with-delete
    - Upgrade with prestage: adds --with-prestage
    - Upgrade with prestage + snapshot: adds --with-prestage --snapshot (no --with-delete)

Follows the established subcloud-group pattern used by the backup/restore group
tests: build a temporary group from picker-selected members, run the operation
against the group, watch all members to completion, then reset members to the
Default group and delete the test group in teardown.

Test execution:
    - test_combined_pk_sw_deploy_strategy_group_subcloud_n_release
    - test_combined_pk_sw_deploy_strategy_with_prestage_group_subcloud_n_release
    - test_combined_pk_sw_deploy_strategy_with_prestage_snapshot_group_subcloud_n_release

Prerequisites:
    - System controller accessible (--lab_config_file)
    - At least two online, out-of-sync subclouds (members are selected by
      availability and sync state only, not by release)
    - A deployed release matching the N load present in software list
    - Target K8s version active on the system controller

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/orchestrator/sw_deploy/test_sw_deploy_strategy_combined_pk_group_subcloud.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.lab_has_min_2_subclouds: a group needs at least two members
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords import STRATEGY_STEP_IN_PROGRESS_STATES, DcManagerSubcloudStateWatcherKeywords
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from testcases.cloud_platform.regression.dc.orchestrator.sw_deploy.test_sw_deploy_strategy_combined_pk_single_subcloud import get_highest_release_for_load, get_target_kube_version

TEST_GROUP_NAME = "TestGroup"


def run_group_combined_pk_sw_deploy_strategy(request: FixtureRequest, with_delete: bool = True, with_prestage: bool = False, snapshot: bool = False) -> None:
    """Build a subcloud group, run a combined P&K sw-deploy-strategy against it, and verify all members complete.

    Members are selected by availability and sync state only (online,
    out-of-sync), with no release filter, as the other subcloud-group
    orchestration tests do. The combined P&K parameters are threaded through the
    same way as the single-subcloud module (with_delete, with_prestage,
    snapshot) so the group coverage matches its mode matrix.

    The target N release is resolved from software list and the target
    Kubernetes version from the system controller's active version, reusing the
    single-subcloud combined P&K resolvers so both scopes agree on what "N"
    means.

    Args:
        request (FixtureRequest): pytest request fixture for teardown registration.
        with_delete (bool): Add --with-delete. Defaults to True.
        with_prestage (bool): Add --with-prestage (and the required sysadmin password).
        snapshot (bool): Add --snapshot. Mutually exclusive with --with-delete.
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build(TEST_GROUP_NAME)

    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    # Register teardown before the operation so a partial run still cleans up (LIFO).
    request.addfinalizer(lambda: DcmanagerStrategyCleanupKeywords(system_controller_ssh).cleanup_strategy("sw-deploy"))
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))

    # Only one dcmanager strategy may exist at a time, of any type. Fail fast with
    # an actionable message instead of an opaque return code from the create below.
    get_logger().log_test_case_step("Verify no pre-existing dcmanager strategy blocks this run")
    DcmanagerStrategyCleanupKeywords(system_controller_ssh).assert_no_strategy_exists()

    get_logger().log_test_case_step("Resolve the target N release and Kubernetes version")
    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    kube_version = get_target_kube_version(system_controller_ssh)

    create_kwargs = {
        "subcloud_group": TEST_GROUP_NAME,
        "release": release,
        "kube_upgrade": kube_version,
        "with_delete": with_delete,
        "snapshot": snapshot,
    }
    if with_prestage:
        create_kwargs["with_prestage"] = True
        create_kwargs["sysadmin_password"] = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()

    get_logger().log_test_case_step(f"Create combined P&K sw-deploy-strategy for group '{TEST_GROUP_NAME}' (release={release}, kube-upgrade={kube_version}, with_delete={with_delete}, with_prestage={with_prestage}, snapshot={snapshot}, members={members})")
    strategy_keywords.dcmanager_sw_deploy_strategy_create(**create_kwargs)

    get_logger().log_test_case_step(f"Apply combined P&K sw-deploy-strategy against group '{TEST_GROUP_NAME}' (no wait)")
    strategy_keywords.dcmanager_sw_deploy_strategy_apply(target=TEST_GROUP_NAME, is_group=True, wait_completion=False)

    get_logger().log_test_case_step("Watch all group members' strategy steps to completion")
    DcManagerSubcloudStateWatcherKeywords(system_controller_ssh).watch_strategy_steps(
        subcloud_names=members,
        in_progress_states=STRATEGY_STEP_IN_PROGRESS_STATES,
    )

    get_logger().log_test_case_step("Validate deploy_status is 'complete' for every group member")
    subcloud_list = DcManagerSubcloudListKeywords(system_controller_ssh).get_dcmanager_subcloud_list()
    for member in members:
        deploy_status = subcloud_list.get_subcloud_by_name(member).get_deploy_status()
        validate_equals(deploy_status, "complete", f"Subcloud '{member}' deploy status should be complete after group combined P&K sw-deploy")

    get_logger().log_test_case_step("Delete the sw-deploy-strategy")
    strategy_keywords.dcmanager_sw_deploy_strategy_delete()


@mark.p1
@mark.lab_has_min_2_subclouds
def test_combined_pk_sw_deploy_strategy_group_subcloud_n_release(request):
    """Verify combined P&K sw-deploy-strategy on a subcloud group for the N release.

    Test Steps:
        1. Select online, out-of-sync subclouds and assign them to a group
        2. Resolve the highest deployed N release and the active K8s version
        3. Create a combined P&K sw-deploy-strategy (--kube-upgrade --release-id
           --with-delete) against the group and apply it (no wait)
        4. Watch every member's strategy step to completion via
           watch_strategy_steps() using STRATEGY_STEP_IN_PROGRESS_STATES
        5. Validate each member's deploy_status is 'complete'
        6. Delete the strategy

    Teardown:
        - Reset members to the Default group and delete the test group
    """
    run_group_combined_pk_sw_deploy_strategy(request)


@mark.p1
@mark.lab_has_min_2_subclouds
def test_combined_pk_sw_deploy_strategy_with_prestage_group_subcloud_n_release(request):
    """Verify combined P&K sw-deploy-strategy with prestage on a subcloud group for the N release.

    Test Steps:
        1. Select online, out-of-sync subclouds and assign them to a group
        2. Resolve the highest deployed N release and the active K8s version
        3. Create a combined P&K sw-deploy-strategy (--kube-upgrade --release-id
           --with-delete --with-prestage) against the group and apply it (no wait)
        4. Watch every member's strategy step to completion via
           watch_strategy_steps() using STRATEGY_STEP_IN_PROGRESS_STATES
        5. Validate each member's deploy_status is 'complete'
        6. Delete the strategy

    Teardown:
        - Reset members to the Default group and delete the test group
    """
    run_group_combined_pk_sw_deploy_strategy(request, with_prestage=True)


@mark.p1
@mark.lab_has_min_2_subclouds
def test_combined_pk_sw_deploy_strategy_with_prestage_snapshot_group_subcloud_n_release(request):
    """Verify combined P&K sw-deploy-strategy with prestage and snapshot on a subcloud group for the N release.

    --snapshot and --with-delete are mutually exclusive, so this variant drops
    --with-delete, matching the single-subcloud snapshot variants.

    Test Steps:
        1. Select online, out-of-sync subclouds and assign them to a group
        2. Resolve the highest deployed N release and the active K8s version
        3. Create a combined P&K sw-deploy-strategy (--kube-upgrade --release-id
           --with-prestage --snapshot, no --with-delete) against the group and
           apply it (no wait)
        4. Watch every member's strategy step to completion via
           watch_strategy_steps() using STRATEGY_STEP_IN_PROGRESS_STATES
        5. Validate each member's deploy_status is 'complete'
        6. Delete the strategy

    Teardown:
        - Reset members to the Default group and delete the test group
    """
    run_group_combined_pk_sw_deploy_strategy(request, with_delete=False, with_prestage=True, snapshot=True)
