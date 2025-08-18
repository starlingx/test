"""
Negative Test cases for dcmanager subcloud deploy upload functionality.

Notes:
    - A "deployed" version corresponds to the active load release.
    - An "unavailable" version corresponds to the inactive load release.
    - Both deployed and unavailable versions are considered valid release versions.
    - An "invalid" version, such as the second last major release, is considered an invalid release version and is used for negative testing.
"""

from pytest import mark

from framework.validation.validation import validate_not_equals, validate_str_contains
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass


@mark.p2
def test_subcloud_deploy_upload_with_invalid_release():
    """
    Negative testing: Test dcmanager subcloud deploy upload with unavailable release version.

    Test Steps:
        - Get SSH connection to the active controller of the system controller
        - Retrieve the second last major release version which is an invalid release version
        - Run "dcmanager subcloud deploy upload" using invalid release version
        - Validate that the upload fails with the expected error message

    Expected Results:
        - Error message should indicate the release version is invalid
    """
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)

    # Execute deploy upload with second last major release version which is an invalid version
    invalid_version = CloudPlatformVersionManagerClass().get_second_last_major_release().get_name()
    error_message = dcm_sc_deploy_kw.dcmanager_subcloud_deploy_upload_with_error(update_deploy_params=True, release_version=invalid_version)
    validate_str_contains(error_message, "invalid release version parameter", f"Error message for invalid release version: {invalid_version}")


@mark.p2
def test_subcloud_deploy_upload_without_mandatory_parameters_active_load():
    """
    Negative testing: Test dcmanager subcloud deploy upload without mandatory parameters using active load release.

    Test Steps:
        - Get SSH connection to the active controller of the system controller
        - Run "dcmanager subcloud deploy upload" without passing any mandatory parameter
        - Validate that the error message indicates mandatory arguments are required

    Expected Results:
        - Error message should indicate that mandatory parameters are required
    """
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Execute deploy upload without mandatory parameters
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)
    error_message = dcm_sc_deploy_kw.dcmanager_subcloud_deploy_upload_with_error()
    validate_str_contains(error_message, "argument --deploy_playbook--deploy_chart is required", "Error message for missing mandatory parameters")


@mark.p2
def test_subcloud_deploy_upload_without_mandatory_parameters_inactive_load():
    """
    Negative testing: Test dcmanager subcloud deploy upload without mandatory parameters using inactive load release.

    Test Steps:
        - Get SSH connection to the active controller of the system controller
        - Retrieve the list of software releases
        - Identify a release that is in "unavailable" state
        - Run "dcmanager subcloud deploy upload" for the inactive release without passing mandatory parameters
        - Validate that the error message indicates mandatory arguments are required

    Expected Results:
        - Error message should indicate that mandatory parameters are required
    """
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Get unavailable release version
    software_list_keywords = SoftwareListKeywords(ssh_connection)
    software_list_output = software_list_keywords.get_software_list()

    # Find a release that is not in "available" state
    unavailable_version = software_list_output.get_product_version_by_state("unavailable")
    validate_not_equals(len(unavailable_version), 0, "unavailable releases found")

    # Execute deploy upload without mandatory parameters using unavailable release version
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)
    error_message = dcm_sc_deploy_kw.dcmanager_subcloud_deploy_upload_with_error(release_version=unavailable_version[0])
    validate_str_contains(error_message, "argument --deploy_playbook--deploy_chart is required", "Error message for missing mandatory parameters")
