import time
from typing import Tuple

from pytest import mark

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import fail, validate_equals, validate_less_than_or_equal
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_management_enum import DcManagerSubcloudListManagementEnum
from keywords.cloud_platform.dcmanager.objects.subcloud_pick_result import SubcloudPickResult
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords
from keywords.linux.log.log_grep_keywords import LogGrepKeywords
from keywords.openstack.openstack.user.openstack_user_keywords import OpenstackUserListKeywords
from keywords.openstack.openstack.user.openstack_user_set_keywords import OpenstackUserSetKeywords

# Log of the dcorch service on the System Controller. dcorch writes every sync to this single file.
DCORCH_LOG = "/var/log/dcorch/dcorch.log"

# When the identity audit finds a user that differs between the System Controller and a subcloud,
# dcorch logs "<subcloud region>/identity: Scheduling put work for users/<user id>". A converged
# sync never logs this for a user it has already synced, so the lines are counted per user and per
# subcloud region.
PUT_WORK_LOG_TEMPLATE = "{region}/identity: Scheduling put work for users/{user_id}"

# dcorch audits each subcloud every 1200 seconds, but only checks whether an audit is due every
# 300 seconds, so two audits of the same subcloud can be up to 1200 + 300 seconds apart. A window
# of N * (1200 + 300) seconds therefore always contains N complete audits; the margin lets the
# last audit finish.
AUDIT_INTERVAL_SECONDS = 1200
AUDIT_CHECK_DELAY_SECONDS = 300
AUDIT_MARGIN_SECONDS = 60

# Complete audits observed after the option has been set.
OBSERVED_AUDITS = 2

# Put work allowed to be scheduled for the user in the observed window. With the fix the user is
# not sent again after the option is synced, so any new line means the sync is repeating.
ALLOWED_NEW_PUT_WORK = 0

# Older releases to look for, in order of preference.
OLDER_RELEASE_LOADS = ("N-1", "N-2")

TEST_USER = "admin"


def pick_older_release_subcloud() -> Tuple[SSHConnection, SubcloudPickResult, str]:
    """Pick an online, managed subcloud running N-1, or N-2 if there is no N-1 subcloud.

    The release is resolved by the picker, so neither a subcloud nor a version is hardcoded.

    Returns:
        Tuple[SSHConnection, SubcloudPickResult, str]: SSH connection to the System Controller that owns the subcloud, the picked subcloud, and the load that matched.

    Raises:
        KeywordException: If the lab has neither an N-1 nor an N-2 subcloud that is online and managed.
    """
    last_error = None
    for load in OLDER_RELEASE_LOADS:
        try:
            system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
                availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
                management_status=DcManagerSubcloudListManagementEnum.MANAGED,
                load=load,
            )
            return system_controller_ssh, result, load
        except KeywordException as error:
            get_logger().log_info(f"No online, managed {load} subcloud available: {error}")
            last_error = error
    raise KeywordException(f"The lab has no online, managed subcloud running any of {OLDER_RELEASE_LOADS}.") from last_error


def get_subcloud_region(subcloud: SubcloudPickResult) -> str:
    """Get the region name dcorch uses for a subcloud in its log.

    Args:
        subcloud (SubcloudPickResult): The picked subcloud.

    Returns:
        str: The region name of the subcloud.

    Raises:
        KeywordException: If the picker did not load 'dcmanager subcloud show' for the subcloud.
    """
    show_object = subcloud.get_show_object()
    if show_object is None or not show_object.get_region_name():
        raise KeywordException(f"The region name of subcloud '{subcloud.get_name()}' is not available from the picker result.")
    return show_object.get_region_name()


def get_user_id(system_controller_ssh: SSHConnection, username: str) -> str:
    """Get the Keystone ID of a user, which is the ID dcorch logs for it.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the System Controller.
        username (str): Name of the user.

    Returns:
        str: The user ID.

    Raises:
        KeywordException: If no user with that name exists.
    """
    for user in OpenstackUserListKeywords(system_controller_ssh).get_openstack_user_list().get_users():
        if user.get_name() == username:
            return user.get_id()
    raise KeywordException(f"User '{username}' was not found in the Keystone user list.")


def wait_audits(audits: int, description: str) -> None:
    """Sleep long enough for a number of complete dcorch audits of a subcloud.

    Args:
        audits (int): Number of complete audits to wait for.
        description (str): What the wait is for, used in the log.
    """
    seconds = audits * (AUDIT_INTERVAL_SECONDS + AUDIT_CHECK_DELAY_SECONDS) + AUDIT_MARGIN_SECONDS
    get_logger().log_info(f"Waiting {seconds}s ({audits} audit(s) of up to {AUDIT_INTERVAL_SECONDS + AUDIT_CHECK_DELAY_SECONDS}s apart plus {AUDIT_MARGIN_SECONDS}s margin) for: {description}")
    time.sleep(seconds)


def count_put_work(system_controller_ssh: SSHConnection, region: str, user_id: str) -> int:
    """Count the times an audit scheduled put work for a user on one subcloud.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the System Controller.
        region (str): Region name of the subcloud.
        user_id (str): Keystone ID of the user.

    Returns:
        int: Number of log lines that scheduled put work for the user on the subcloud.
    """
    pattern = PUT_WORK_LOG_TEMPLATE.format(region=region, user_id=user_id)
    count = LogGrepKeywords(system_controller_ssh).count_pattern_occurrences(DCORCH_LOG, pattern)
    get_logger().log_info(f"'{pattern}' lines in {DCORCH_LOG}: {count}")
    return count


def validate_no_new_put_work(system_controller_ssh: SSHConnection, region: str, user_id: str, baseline_count: int, description: str) -> None:
    """Check that no new put work was scheduled for the user since a baseline.

    A count below the baseline means the log was rotated during the window, so the observation
    says nothing about repetition and the check fails instead of passing.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the System Controller.
        region (str): Region name of the subcloud.
        user_id (str): Keystone ID of the user.
        baseline_count (int): Count taken at the start of the observed window.
        description (str): What is being validated, used in the validation message.
    """
    final_count = count_put_work(system_controller_ssh, region, user_id)
    if final_count < baseline_count:
        fail(f"{description}: the count went from {baseline_count} to {final_count}, so {DCORCH_LOG} was rotated during the observed window and repetition cannot be judged. Re-run the test.")

    new_put_work = final_count - baseline_count
    validate_less_than_or_equal(new_put_work, ALLOWED_NEW_PUT_WORK, f"{description}: new put work scheduled in the window (baseline {baseline_count}, final {final_count})")


@mark.p1
@mark.lab_has_subcloud
def test_dcorch_identity_sync_converges_on_older_release_subcloud(request):
    """Verify dcorch identity sync converges for a user_option against an N-1/N-2 subcloud.

    After dcorch started syncing the Keystone user_option table, a System Controller on release
    N returned user_option data that an N-1/N-2 subcloud did not, so the user always looked out
    of sync and the audit scheduled it to be sent again on every audit. The fix is review
    1001352. A single check of the synced state cannot tell a converged sync from one that is
    about to run again, so this test counts the audit's "Scheduling put work" lines for the user
    on the subcloud in dcorch.log over several audits and checks that the count does not grow.

    dcorch syncs the change itself right after it is made, and then audits each subcloud every
    1200 seconds. The test body takes about 51 minutes (two audits plus the check delay and
    margin) and the teardown about 26 minutes (one audit), so a run is around 80 minutes. It is
    meant for a weekly suite, not a daily one.

    Prerequisites:
        - An online, managed subcloud running N-1 or N-2 (N-1 is preferred).

    Setup:
        - Pick the subcloud with the picker's load filter (N-1, then N-2)
        - Clear ignore_password_expiry on the user first if it is already set

    Test Steps:
        1. Take the put work count for the user on the subcloud as baseline
        2. Set the ignore_password_expiry user option on admin from the System Controller
        3. Wait at least two complete audits of the subcloud
        4. Verify no new put work was scheduled for the user on the subcloud since the baseline

    Teardown:
        - Always clear ignore_password_expiry on admin and verify it is cleared
        - Wait one audit, then verify it scheduled no new put work for the user on the subcloud
    """
    system_controller_ssh, subcloud, load = pick_older_release_subcloud()
    region = get_subcloud_region(subcloud)
    user_id = get_user_id(system_controller_ssh, TEST_USER)
    get_logger().log_info(f"Using {load} subcloud '{subcloud.get_name()}' (region {region}) to check identity sync convergence of user '{TEST_USER}' ({user_id})")

    user_keywords = OpenstackUserSetKeywords(system_controller_ssh)

    def cleanup():
        get_logger().log_teardown_step(f"Clear ignore_password_expiry on '{TEST_USER}' and confirm identity sync settles")
        user_keywords.set_user_ignore_password_expiry(TEST_USER, False)
        validate_equals(user_keywords.get_user_ignore_password_expiry(TEST_USER), False, f"ignore_password_expiry is cleared on '{TEST_USER}'")

        settled_baseline = count_put_work(system_controller_ssh, region, user_id)
        wait_audits(1, "one audit after the option was cleared")
        validate_no_new_put_work(system_controller_ssh, region, user_id, settled_baseline, "After clearing the option, identity sync has settled")

    # Registered before the option is touched, so it runs even if the setup or the test fails part way.
    request.addfinalizer(cleanup)

    if user_keywords.get_user_ignore_password_expiry(TEST_USER):
        get_logger().log_info(f"ignore_password_expiry is already set on '{TEST_USER}'; clearing it so setting it again produces a change to sync")
        user_keywords.set_user_ignore_password_expiry(TEST_USER, False)

    get_logger().log_test_case_step("Take the put work baseline")
    baseline_count = count_put_work(system_controller_ssh, region, user_id)

    get_logger().log_test_case_step(f"Set ignore_password_expiry on '{TEST_USER}' from the System Controller")
    user_keywords.set_user_ignore_password_expiry(TEST_USER, True)
    validate_equals(user_keywords.get_user_ignore_password_expiry(TEST_USER), True, f"ignore_password_expiry is set on '{TEST_USER}'")

    get_logger().log_test_case_step(f"Observe {OBSERVED_AUDITS} complete audits of the subcloud")
    wait_audits(OBSERVED_AUDITS, "the observed audits to complete")

    get_logger().log_test_case_step("Verify the user is not sent again by the audit")
    validate_no_new_put_work(system_controller_ssh, region, user_id, baseline_count, f"Identity sync converged against {load} subcloud '{subcloud.get_name()}'")
