"""DC sw-deploy-strategy - Subcloud Group orchestration test.

Applies a software deploy strategy to a subcloud group and verifies that every
member completes, using the centralized DcManagerSubcloudStateWatcherKeywords to
monitor strategy-step progress across all members (no inline strategy-step
polling).

Follows the established subcloud-group pattern used by the backup/restore group
tests: build a temporary group from picker-selected members, run the operation
against the group, watch all members to completion, then reset members to the
Default group and delete the test group in teardown.

Prerequisites:
    - System controller accessible (--lab_config_file)
    - At least two online, out-of-sync subclouds (members are selected by
      availability and sync state only, not by release)
    - A deployed release matching the N load present in software list

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/orchestrator/sw_deploy/test_sw_deploy_strategy_group_subcloud.py \
        --lab_config_file=<LAB_CONFIG> -v

Markers:
    - @mark.lab_has_min_2_subclouds: a group needs at least two members
"""

from pytest import fail, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords import (
    STRATEGY_STEP_IN_PROGRESS_STATES,
    DcManagerSubcloudStateWatcherKeywords,
)
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass

TEST_GROUP_NAME = "TestGroup"


def _get_highest_release_for_load(ssh_connection: SSHConnection, load: str, state: str = "deployed") -> str:
    """Get the highest release name matching a load prefix from software list.

    sw-deploy needs the full release name (e.g. WRCP-26.03.200), not just the
    load identifier (26.03).

    Args:
        ssh_connection (SSHConnection): SSH connection to query software list.
        load (str): Load prefix to match (e.g. "26.03").
        state (str): Release state to filter by. Defaults to "deployed".

    Returns:
        str: The highest release name matching the load.
    """
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    releases = software_list.get_release_name_by_state(state)
    matching = [r for r in releases if load in r]
    if not matching:
        fail(f"No release found matching load '{load}' in state '{state}'. Available: {releases}")
    return max(matching)


@mark.p2
@mark.lab_has_min_2_subclouds
def test_sw_deploy_strategy_group_subcloud(request):
    """Apply a sw-deploy-strategy to a subcloud group and verify all members complete.

    Members are selected by availability and sync state only (online,
    out-of-sync), with no release filter, mirroring the single-subcloud
    sw-deploy picker usage. The strategy targets the highest deployed N
    release; out-of-sync members have a software delta to reconcile.

    Test Steps:
        1. Select online, out-of-sync subclouds and assign them to a group
        2. Resolve the highest deployed N release from software list
        3. Create a sw-deploy-strategy against the group and apply it (no wait)
        4. Watch every member's strategy step to completion via
           watch_strategy_steps() using STRATEGY_STEP_IN_PROGRESS_STATES
        5. Validate each member's deploy_status is 'complete'
        6. Delete the strategy

    Teardown:
        - Reset members to the Default group and delete the test group
    """
    system_controller_ssh, members = DcmanagerSubcloudGroupKeywords.dcmanager_subcloud_group_build(TEST_GROUP_NAME)

    # Register teardown before the operation so a partial run still cleans up (LIFO).
    request.addfinalizer(lambda: DcmanagerStrategyCleanupKeywords(system_controller_ssh).cleanup_strategy("sw-deploy"))
    request.addfinalizer(lambda: DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_delete_and_reset(TEST_GROUP_NAME, members))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = _get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    get_logger().log_test_case_step(f"Create sw-deploy-strategy for group '{TEST_GROUP_NAME}' (release={release}, members={members})")
    strategy_keywords.dcmanager_sw_deploy_strategy_create(subcloud_group=TEST_GROUP_NAME, release=release, with_delete=True)

    get_logger().log_test_case_step(f"Apply sw-deploy-strategy against group '{TEST_GROUP_NAME}' (no wait)")
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
        validate_equals(deploy_status, "complete", f"Subcloud '{member}' deploy status should be complete after group sw-deploy")

    get_logger().log_test_case_step("Delete the sw-deploy-strategy")
    strategy_keywords.dcmanager_sw_deploy_strategy_delete()
