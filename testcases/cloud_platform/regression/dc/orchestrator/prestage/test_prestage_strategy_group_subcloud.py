"""DC prestage-strategy - Subcloud Group orchestration tests.

Applies a prestage strategy to a subcloud group and verifies that every member
completes, using the centralized DcManagerSubcloudStateWatcherKeywords to
monitor strategy-step progress across all members (no inline strategy-step
polling).

Mirrors the operation coverage of the single-subcloud prestage module
(test_prestage_strategy_single_subcloud.py) at group scope: the same
for-install / for-sw-deploy x N / N-1 matrix, driven by the prestage-strategy
create parameters (release, sw_deploy). Group members are selected by
availability and sync state only (no release filter), following the
subcloud-group pattern used by the backup/restore group tests: build a
temporary group from picker-selected members, run the operation against the
group, watch all members to completion, then reset members to the Default
group and delete the test group in teardown.

Prerequisites:
    - System controller accessible (--lab_config_file)
    - At least two online subclouds (members are selected by availability
      and sync state only, not by release)

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/orchestrator/prestage/test_prestage_strategy_group_subcloud.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.lab_has_min_2_subclouds: a group needs at least two members
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_prestage_strategy_keywords import DcmanagerPrestageStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords import (
    STRATEGY_STEP_IN_PROGRESS_STATES,
    DcManagerSubcloudStateWatcherKeywords,
)
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass

TEST_GROUP_NAME = "TestGroup"


def run_group_prestage_strategy(request, release: str = None, for_sw_deploy: bool = True) -> None:
    """Build a subcloud group, run a prestage-strategy against it, and verify all members complete.

    Members are selected by availability and sync state only (online,
    out-of-sync), with no release filter, mirroring the single-subcloud
    prestage picker usage. The prestage operation is parameterized the same
    way as the single-subcloud module (release, sw_deploy) so the group
    coverage matches the for-install / for-sw-deploy x N / N-1 matrix.

    Args:
        request: The pytest request fixture (used to register teardown).
        release (str): Release version to pass to the strategy. None targets N.
        for_sw_deploy (bool): Use --for-sw-deploy when True, --for-install when False.
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build(TEST_GROUP_NAME)

    prestage_keywords = DcmanagerPrestageStrategyKeywords(system_controller_ssh)

    # Register teardown before the operation so a partial run still cleans up (LIFO).
    request.addfinalizer(lambda: prestage_keywords.get_dcmanager_prestage_strategy_delete())
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))

    get_logger().log_test_case_step(f"Create prestage-strategy for group '{TEST_GROUP_NAME}' (release={release}, for_sw_deploy={for_sw_deploy}, members={members})")
    prestage_keywords.get_dcmanager_prestage_strategy_create(subcloud_group=TEST_GROUP_NAME, release=release, sw_deploy=for_sw_deploy)

    get_logger().log_test_case_step(f"Apply prestage-strategy against group '{TEST_GROUP_NAME}' (no wait)")
    prestage_keywords.get_dcmanager_prestage_strategy_apply(wait_completion=False)

    get_logger().log_test_case_step("Watch all group members' strategy steps to completion")
    DcManagerSubcloudStateWatcherKeywords(system_controller_ssh).watch_strategy_steps(
        subcloud_names=members,
        in_progress_states=STRATEGY_STEP_IN_PROGRESS_STATES,
    )

    get_logger().log_test_case_step("Validate prestage_status is 'complete' for every group member")
    subcloud_list = DcManagerSubcloudListKeywords(system_controller_ssh).get_dcmanager_subcloud_list()
    for member in members:
        prestage_status = subcloud_list.get_subcloud_by_name(member).get_prestage_status()
        validate_equals(prestage_status, "complete", f"Subcloud '{member}' prestage status should be complete after group prestage")

    get_logger().log_test_case_step("Delete the prestage-strategy")
    prestage_keywords.get_dcmanager_prestage_strategy_delete()


def _n_minus_1_release() -> str:
    """Resolve the N-1 release version string, as the single-subcloud module does."""
    return str(CloudPlatformVersionManagerClass().get_last_major_release())


# --- Prestage Strategy for Install ---


@mark.p2
@mark.lab_has_min_2_subclouds
def test_prestage_strategy_group_subcloud_for_install_n_release(request):
    """Verify group prestage-strategy for-install with N release; all members complete.

    Test Steps:
        1. Select online, out-of-sync subclouds and assign them to a group
        2. Create a prestage-strategy (for-install, no --release) and apply it (no wait)
        3. Watch every member's strategy step to completion
        4. Validate each member's prestage_status is 'complete'
        5. Delete the strategy

    Teardown:
        - Reset members to the Default group and delete the test group
    """
    run_group_prestage_strategy(request, for_sw_deploy=False)


@mark.p2
@mark.lab_has_min_2_subclouds
def test_prestage_strategy_group_subcloud_for_install_n_minus_1_release(request):
    """Verify group prestage-strategy for-install with N-1 release; all members complete.

    Test Steps:
        1. Resolve N-1 release version
        2. Select online, out-of-sync subclouds and assign them to a group
        3. Create a prestage-strategy (for-install, --release N-1) and apply it (no wait)
        4. Watch every member's strategy step to completion
        5. Validate each member's prestage_status is 'complete'
        6. Delete the strategy

    Teardown:
        - Reset members to the Default group and delete the test group
    """
    run_group_prestage_strategy(request, release=_n_minus_1_release(), for_sw_deploy=False)


# --- Prestage Strategy for SW Deploy ---


@mark.p2
@mark.lab_has_min_2_subclouds
def test_prestage_strategy_group_subcloud_for_sw_deploy_n_release(request):
    """Verify group prestage-strategy --for-sw-deploy with N release; all members complete.

    Test Steps:
        1. Select online, out-of-sync subclouds and assign them to a group
        2. Create a prestage-strategy (--for-sw-deploy, no --release) and apply it (no wait)
        3. Watch every member's strategy step to completion
        4. Validate each member's prestage_status is 'complete'
        5. Delete the strategy

    Teardown:
        - Reset members to the Default group and delete the test group
    """
    run_group_prestage_strategy(request, for_sw_deploy=True)


@mark.p2
@mark.lab_has_min_2_subclouds
def test_prestage_strategy_group_subcloud_for_sw_deploy_n_minus_1_release(request):
    """Verify group prestage-strategy --for-sw-deploy with N-1 release; all members complete.

    Test Steps:
        1. Resolve N-1 release version
        2. Select online, out-of-sync subclouds and assign them to a group
        3. Create a prestage-strategy (--for-sw-deploy, --release N-1) and apply it (no wait)
        4. Watch every member's strategy step to completion
        5. Validate each member's prestage_status is 'complete'
        6. Delete the strategy

    Teardown:
        - Reset members to the Default group and delete the test group
    """
    run_group_prestage_strategy(request, release=_n_minus_1_release(), for_sw_deploy=True)
