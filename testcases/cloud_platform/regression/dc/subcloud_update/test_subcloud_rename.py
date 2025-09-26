from typing import Tuple

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


def get_subcloud_name(ssh_connection: SSHConnection) -> str:
    """
    Retrieve the name of the healthy subcloud with the lowest ID.

    Args:
        ssh_connection (SSHConnection): Active SSH connection to the controller.

    Returns:
        str: The original subcloud name.
    """
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    lowest_subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    sc_name_original = lowest_subcloud.get_name()
    return sc_name_original


def dcmanager_subcloud_rename(ssh_connection: SSHConnection, sc_name_new: str) -> str:
    """
    Perform a successful subcloud rename.

    This function:
        - Retrieves the original subcloud name.
        - Unmanages the subcloud.
        - Renames it using dcmanager.
        - Returns the original subcloud name for teardown.

    Args:
        ssh_connection (SSHConnection): Active SSH connection to the controller.
        sc_name_new (str): The new name for the subcloud.

    Returns:
        str: The original subcloud name.
    """
    sc_name_original = get_subcloud_name(ssh_connection)
    dcm_sc_kw = DcManagerSubcloudManagerKeywords(ssh_connection)

    dcm_sc_kw.get_dcmanager_subcloud_unmanage(sc_name_original, 30)
    get_logger().log_info(f"Subcloud selected for rename: {sc_name_original}")

    DcManagerSubcloudUpdateKeywords(ssh_connection).dcmanager_subcloud_update(sc_name_original, "name", sc_name_new)
    get_logger().log_info(f"Subcloud {sc_name_original} renamed to {sc_name_new}")

    return sc_name_original


def dcmanager_subcloud_rename_negative(ssh_connection: SSHConnection, sc_name_new: str) -> Tuple[str, str]:
    """
    Attempt a subcloud rename expected to fail.

    This function:
        - Retrieves the original subcloud name.
        - Unmanages the subcloud.
        - Attempts rename with invalid/new name.
        - Returns error message and original subcloud name.

    Args:
        ssh_connection (SSHConnection): Active SSH connection to the controller.
        sc_name_new (str): The new (invalid or conflicting) name for the subcloud.

    Returns:
        Tuple[str, str]: (error_message, original subcloud name)
    """
    sc_name_original = get_subcloud_name(ssh_connection)
    dcm_sc_kw = DcManagerSubcloudManagerKeywords(ssh_connection)

    dcm_sc_kw.get_dcmanager_subcloud_unmanage(sc_name_original, 30)
    get_logger().log_info(f"Subcloud selected for rename: {sc_name_original}")

    error_message = DcManagerSubcloudUpdateKeywords(ssh_connection).dcmanager_subcloud_update_with_error(sc_name_original, "name", sc_name_new)
    return error_message, sc_name_original


@mark.p0
@mark.lab_has_subcloud
def test_subcloud_rename(request):
    """
    Verify subcloud rename

    Test Steps:
        - Log onto the active controller
        - Get the original subcloud name
        - Rename subcloud
        - Manage the renamed subcloud
        - Validate that the subcloud has the new name
        - Validate that the subcloud returns to "in-sync" state
        - Reset subcloud name back to original
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    dcm_sc_kw = DcManagerSubcloudManagerKeywords(ssh_connection)

    sc_name_new = "testsubcloudrenames"
    sc_name_original = dcmanager_subcloud_rename(ssh_connection, sc_name_new)

    # Manage renamed subcloud
    dcm_sc_kw.get_dcmanager_subcloud_manage(sc_name_new, 30)

    # Validate rename
    obj_subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(sc_name_new)
    validate_equals(obj_subcloud.get_name(), sc_name_new, "Validate that the name has been changed")

    # Validate in-sync
    dcm_sc_list_kw.validate_subcloud_sync_status(sc_name_new, "in-sync")

    # Teardown to reset subcloud name
    def teardown():
        dcmanager_subcloud_rename(ssh_connection, sc_name_original)
        dcm_sc_kw.get_dcmanager_subcloud_manage(sc_name_original, 300)
        dcm_sc_list_kw.validate_subcloud_sync_status(sc_name_original, "in-sync")

    request.addfinalizer(teardown)


@mark.p0
@mark.lab_has_subcloud
def test_subcloud_rename_negative_same_subcloud_name(request) -> None:
    """
    Verify that renaming a subcloud to its existing name fails with the correct error.

    Test Steps:
        - Log onto the active controller
        - Get the current subcloud name
        - Attempt to rename the subcloud with the same name
        - Validate that the error message indicates renaming to the same name is not allowed
        - Ensure subcloud is managed again after the test
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    sc_name_new = get_subcloud_name(ssh_connection)

    # Attempt invalid rename (same name)
    error_message, sc_name_original = dcmanager_subcloud_rename_negative(ssh_connection, sc_name_new)

    # Validate error message
    validate_str_contains(error_message, "same as the current subcloud", f"Subcloud rename should not allow a name that is the same as the current name {sc_name_new}")

    def teardown():
        dcm_sc_kw = DcManagerSubcloudManagerKeywords(ssh_connection)
        dcm_sc_kw.get_dcmanager_subcloud_manage(sc_name_original, timeout=60)
        dcm_sc_list_kw.validate_subcloud_sync_status(sc_name_original, "in-sync")

    request.addfinalizer(teardown)


@mark.p0
@mark.lab_has_min_2_subclouds
def test_dcmanager_subcloud_rename_negative_existing_subcloud_name(request) -> None:
    """
    Verify that attempting to rename a subcloud to the name of another existing subcloud fails.

    Test Steps:
        - Log into the active controller.
        - Retrieve the name of the subcloud to be renamed.
        - Identify a different healthy subcloud to use its name for the rename attempt.
        - Attempt to rename the original subcloud using the existing name of another subcloud.
        - Validate that the error message indicates that the name is already in use.
        - Ensure the original subcloud is managed and in-sync after the test.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    sc_name = get_subcloud_name(ssh_connection)
    sc_name_new = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_different_healthy_subcloud(sc_name).get_name()

    # Attempt invalid rename (existing subcloud name)
    error_message, sc_name_original = dcmanager_subcloud_rename_negative(ssh_connection, sc_name_new)

    # Validate error message
    validate_str_contains(error_message, "already exist", f"Subcloud name should not be the same as another existing subcloud {sc_name_new}")

    def teardown():
        dcm_sc_kw = DcManagerSubcloudManagerKeywords(ssh_connection)
        dcm_sc_kw.get_dcmanager_subcloud_manage(sc_name_original, timeout=60)
        dcm_sc_list_kw.validate_subcloud_sync_status(sc_name_original, "in-sync")

    request.addfinalizer(teardown)


@mark.p0
@mark.lab_has_subcloud
def test_dcmanager_subcloud_rename_negative_invalid_name(request) -> None:
    """
    Verify that renaming a subcloud with an invalid name fails.

    Test Steps:
        - Log onto the active controller
        - Attempt to rename a subcloud with an invalid name
        - Validate that the error message indicates the name is invalid
        - Ensure subcloud is managed again after the test
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    sc_name_new = "Subcloud"  # Invalid name because subcloud names should not consist of uppercase letters

    # Attempt invalid rename
    error_message, sc_name_original = dcmanager_subcloud_rename_negative(ssh_connection, sc_name_new)

    # Validate expected error message
    validate_str_contains(error_message, "must consist of lowercase alphanumeric characters", f"Error message for invalid subcloud name: {sc_name_new}")

    def teardown():
        dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
        dcm_sc_kw = DcManagerSubcloudManagerKeywords(ssh_connection)
        dcm_sc_kw.get_dcmanager_subcloud_manage(sc_name_original, timeout=60)
        dcm_sc_list_kw.validate_subcloud_sync_status(sc_name_original, "in-sync")

    request.addfinalizer(teardown)
