"""Tests for platform.conf permission hardening.

Validates the fix that removes world-readable access from
``/etc/platform/platform.conf`` so an unprivileged local user can no longer
read sensitive values (such as the host UUID) that feed the sysinv-agent
``execute_command`` RPC.

Fixed state: mode 640, owner root, group sys_protected, no ``other`` read
bit. On an unpatched load the file is 644 and world-readable.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.platform_conf_permission_keywords import PlatformConfPermissionKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.linux.user.linux_user_keywords import LinuxUserKeywords

TEST_USER = "platformconftest"


@mark.p1
def test_platform_conf_not_world_readable():
    """platform.conf has 640 root:sys_protected permissions with no other-read.

    Test Steps:
        - Read permission metadata for /etc/platform/platform.conf
        - Verify mode is 640
        - Verify owner is root and group is sys_protected
        - Verify the file has no world (other) access
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    perm_keywords = PlatformConfPermissionKeywords(ssh_connection)

    get_logger().log_test_case_step("Reading platform.conf permission metadata")
    file_info = perm_keywords.get_platform_conf_file_info()

    get_logger().log_test_case_step("Verifying platform.conf mode is 640")
    validate_equals(
        file_info.get_permissions(),
        PlatformConfPermissionKeywords.EXPECTED_MODE,
        "platform.conf mode should be 640",
    )

    get_logger().log_test_case_step("Verifying platform.conf owner and group")
    validate_equals(
        file_info.get_owner(),
        PlatformConfPermissionKeywords.EXPECTED_OWNER,
        "platform.conf owner should be root",
    )
    validate_equals(
        file_info.get_group(),
        PlatformConfPermissionKeywords.EXPECTED_GROUP,
        "platform.conf group should be sys_protected",
    )

    get_logger().log_test_case_step("Verifying platform.conf is not world-readable")
    validate_equals(
        file_info.has_world_access(),
        False,
        "platform.conf should not have world (other) access",
    )


@mark.p1
def test_platform_conf_unreadable_by_unprivileged_user(request):
    """An unprivileged local user cannot read platform.conf.

    Test Steps:
        - Create a minimal local user (users group only, no sys_protected, no sudo)
        - Attempt to read /etc/platform/platform.conf as that user
        - Verify the read is denied

    Teardown:
        - Delete the test user
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    user_keywords = LinuxUserKeywords(ssh_connection)

    def cleanup_user():
        """Remove the unprivileged test user."""
        user_keywords.delete_user(TEST_USER)

    request.addfinalizer(cleanup_user)

    get_logger().log_test_case_step(f"Creating unprivileged local user '{TEST_USER}'")
    user_keywords.create_unprivileged_user(TEST_USER)

    get_logger().log_test_case_step("Verifying the user is NOT in the sys_protected group")
    is_member = user_keywords.is_user_in_group(TEST_USER, PlatformConfPermissionKeywords.EXPECTED_GROUP)
    validate_equals(
        is_member,
        False,
        "Test user must not be a member of sys_protected",
    )

    get_logger().log_test_case_step("Verifying unprivileged user cannot read platform.conf")
    can_read = user_keywords.can_user_read_file(TEST_USER, PlatformConfPermissionKeywords.PLATFORM_CONF_PATH)
    validate_equals(
        can_read,
        False,
        "Unprivileged user should not be able to read platform.conf",
    )
