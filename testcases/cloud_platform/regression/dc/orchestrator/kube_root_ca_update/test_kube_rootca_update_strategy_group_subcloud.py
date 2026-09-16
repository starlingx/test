"""DC kube-rootca-update-strategy - Subcloud Group orchestration test.

Applies a kube-rootca-update strategy to a subcloud group and verifies that
every member completes, using the centralized
DcManagerSubcloudStateWatcherKeywords to monitor strategy-step progress across
all members (no inline strategy-step polling).

Follows the established subcloud-group pattern used by the backup/restore group
tests: build a temporary group from picker-selected members, run the operation
against the group, watch all members to completion, then reset members to the
Default group and delete the test group in teardown.

Prerequisites:
    - System controller accessible (--lab_config_file)
    - At least two online subclouds (members are selected by availability
      and sync state only, not by release)

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/orchestrator/kube_root_ca_update/test_kube_rootca_update_strategy_group_subcloud.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.lab_has_min_2_subclouds: a group needs at least two members
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_kube_rootca_update_strategy_keywords import DcmanagerKubeRootcaUpdateStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords import (
    STRATEGY_STEP_IN_PROGRESS_STATES,
    DcManagerSubcloudStateWatcherKeywords,
)

TEST_GROUP_NAME = "TestGroup"
SUBJECT = "C=CA ST=ON L=Ottawa O=WindRiver OU=StarlingX CN=kubernetes"


@mark.p2
@mark.lab_has_min_2_subclouds
def test_kube_rootca_update_strategy_group_subcloud(request):
    """Apply a kube-rootca-update-strategy to a subcloud group and verify all members complete.

    Members are selected by availability and sync state only (online,
    out-of-sync), with no release filter, mirroring the single-subcloud
    kube-rootca picker usage. The kube root CA is rotated across the whole
    group; subject and expiry mirror the single-subcloud kube-rootca test.

    Test Steps:
        1. Select online, out-of-sync subclouds and assign them to a group
        2. Create a kube-rootca-update-strategy against the group and apply it (no wait)
        3. Watch every member's strategy step to completion via
           watch_strategy_steps() using STRATEGY_STEP_IN_PROGRESS_STATES
        4. Validate each member's kube-rootca_sync_status is 'in-sync'
        5. Delete the strategy

    Teardown:
        - Reset members to the Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build(TEST_GROUP_NAME)

    strategy_keywords = DcmanagerKubeRootcaUpdateStrategyKeywords(system_controller_ssh)

    # Register teardown before the operation so a partial run still cleans up (LIFO).
    request.addfinalizer(lambda: DcmanagerStrategyCleanupKeywords(system_controller_ssh).cleanup_strategy("kube-rootca-update"))
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))

    expiry_date = strategy_keywords.get_future_date(365)

    get_logger().log_test_case_step(f"Create kube-rootca-update-strategy for group '{TEST_GROUP_NAME}' (members={members})")
    strategy_keywords.dcmanager_kube_rootca_update_strategy_create(
        expiry_date=expiry_date,
        subject=SUBJECT,
        group=TEST_GROUP_NAME,
    )

    get_logger().log_test_case_step(f"Apply kube-rootca-update-strategy against group '{TEST_GROUP_NAME}' (no wait)")
    strategy_keywords.dcmanager_kube_rootca_update_strategy_apply(wait_completion=False)

    get_logger().log_test_case_step("Watch all group members' strategy steps to completion")
    DcManagerSubcloudStateWatcherKeywords(system_controller_ssh).watch_strategy_steps(
        subcloud_names=members,
        in_progress_states=STRATEGY_STEP_IN_PROGRESS_STATES,
    )

    get_logger().log_test_case_step("Validate kube-rootca_sync_status is 'in-sync' for every group member")
    for member in members:
        subcloud_show = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(member)
        kube_rootca_sync = subcloud_show.get_dcmanager_subcloud_show_object().get_kube_rootca_sync_status()
        validate_equals(kube_rootca_sync, "in-sync", f"Subcloud '{member}' kube-rootca sync status should be in-sync")

    get_logger().log_test_case_step("Delete the kube-rootca-update-strategy")
    strategy_keywords.dcmanager_kube_rootca_update_strategy_delete()
