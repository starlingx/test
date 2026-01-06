"""Test cases for deleting keystone users using openstack user delete command
and verifying the user is not able to delete with the valid message"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.openstack.openstack.user.openstack_user_curl_keywords import OpenstackUserCurlKeywords
from keywords.openstack.openstack.user.openstack_user_keywords import OpenstackUserListKeywords


@mark.p2
def test_openstack_delete_user_forbidden():
    """
    Test delete user via openstack CLI is forbidden.

    Test Steps:
    1. Get auth_info and connection to use for subsequent CLI calls
    2. Get list of all users
    3. Attempt to delete each user and verify forbidden message
    4. Verify that deletion is properly blocked with expected error message
    """
    get_logger().log_info("Get SSH connection to active controller...")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_info("Initialize OpenStack user keywords...")
    user_keywords = OpenstackUserListKeywords(ssh_connection)

    get_logger().log_info("Get list of all OpenStack users...")
    user_list_output = user_keywords.get_openstack_user_list()
    user_ids = user_list_output.get_user_ids()

    validate_not_equals(len(user_ids), 0, "Verify users found in the system")
    get_logger().log_info(f"Found {len(user_ids)} users to test deletion")

    get_logger().log_info("Attempt to delete users and verify forbidden message...")

    # Attempt to delete each user
    for user_id in user_ids:
        result = user_keywords.delete_user(user_id)
        get_logger().log_info(f"Delete user {user_id} result: {result}")
        expected_message = "You are forbidden to perform the requested action. This action is system-critical and cannot be executed- identity:delete_user. Please contact your administrator for further assistance. (HTTP 403)"

        validate_str_contains(result, expected_message, f"Verify forbidden message for user {user_id}")

    get_logger().log_info("All user deletion attempts were properly forbidden as expected")


@mark.p2
def test_openstack_delete_user_curl_forbidden():
    """
    Test delete user via curl is forbidden.

    Test Steps:
    1. Get auth_info and connection to use for subsequent curl calls
    2. Get list of all users
    3. Attempt to delete each user via curl and verify forbidden message
    4. Verify that curl deletion is properly blocked with expected error message
    """
    get_logger().log_info("Get SSH connection to active controller...")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_info("Initialize OpenStack user curl keywords...")
    user_curl_keywords = OpenstackUserCurlKeywords(ssh_connection)

    # Get user list using CLI keywords
    user_keywords = OpenstackUserListKeywords(ssh_connection)
    user_list_output = user_keywords.get_openstack_user_list()
    user_ids = user_list_output.get_user_ids()

    validate_not_equals(len(user_ids), 0, "Verify users found in the system")
    get_logger().log_info(f"Found {len(user_ids)} users to test curl deletion")

    get_logger().log_info("Attempt to delete users via curl and verify forbidden message...")

    # Attempt to delete each user via curl
    for user_id in user_ids:
        rc, output = user_curl_keywords.delete_user_via_curl(user_id)
        get_logger().log_info(f"Delete user {user_id} via curl result: RC={rc}, Output={output}")
        expected_message = "You are forbidden to perform the requested action. This action is system-critical and cannot be executed- identity:delete_user. Please contact your administrator for further assistance."

        validate_equals(rc, 0, f"Verify curl command succeeded for user {user_id}")
        validate_str_contains(output, expected_message, f"Verify forbidden message in curl response for user {user_id}")
        validate_str_contains(output, "403", f"Verify HTTP 403 status in curl response for user {user_id}")

    get_logger().log_info("All curl user deletion attempts were properly forbidden as expected")
