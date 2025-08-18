"""
Test cases for dcmanager subcloud deploy upload functionality.

Notes:
    - A "deployed" version corresponds to the active load release.
    - An "unavailable" version corresponds to the inactive load release.
    - Both deployed and unavailable versions are considered valid release versions.
"""

from pytest import mark

from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords


@mark.p2
def test_subcloud_deploy_upload_with_deployed_release():
    """
    Test dcmanager subcloud deploy upload with deployed release version.

    Test Steps:
        - Get SSH connection to the active controller of the system controller
        - Retrieve the list of software releases
        - Identify a release that is in "deployed" state (active load release version)
        - Run "dcmanager subcloud deploy upload" with the deployed release version
        - Validate that the software version in the deploy show object matches the selected release version
    """
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Get deployed release version
    software_list_keywords = SoftwareListKeywords(ssh_connection)
    software_list_output = software_list_keywords.get_software_list()
    deployed_version = software_list_output.get_product_version_by_state("deployed")
    validate_not_equals(len(deployed_version), 0, "deployed releases found")

    # Execute deploy upload with deployed release version
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)
    deploy_show_obj = dcm_sc_deploy_kw.dcmanager_subcloud_deploy_upload(update_deploy_params=True, release_version=deployed_version[0]).get_dcmanager_subcloud_deploy_show_object()
    validate_equals(deployed_version[0], deploy_show_obj.get_software_version(), "version matched")


@mark.p2
def test_subcloud_deploy_upload_with_unavailable_release():
    """
    Test dcmanager subcloud deploy upload with unavailable release version.

    Test Steps:
        - Get SSH connection to the active controller of the system controller
        - Retrieve the list of software releases
        - Identify a release that is in "unavailable" state (inactive load release version)
        - Run "dcmanager subcloud deploy upload" with the unavailable release version
        - Validate that the software version in the deploy show object matches the selected release version
    """
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Get unavailable release version
    software_list_keywords = SoftwareListKeywords(ssh_connection)
    software_list_output = software_list_keywords.get_software_list()

    # Find a release that is not in "available" state
    unavailable_version = software_list_output.get_product_version_by_state("unavailable")
    validate_not_equals(len(unavailable_version), 0, "unavailable releases found")

    # Execute deploy upload with unavailable release version
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)
    deploy_show_obj = dcm_sc_deploy_kw.dcmanager_subcloud_deploy_upload(update_deploy_params=True, release_version=unavailable_version[0]).get_dcmanager_subcloud_deploy_show_object()
    validate_equals(unavailable_version[0], deploy_show_obj.get_software_version(), "version matched")


@mark.p2
def test_dcmanager_subcloud_deploy_upload_with_prestaging_images_active_load():
    """
    Test dcmanager subcloud deploy upload with prestaging images using active load release version.

    Test Steps:
        - Get SSH connection to the active controller of the system controller
        - Retrieve the list of software releases
        - Identify a release that is in "deployed" state (active load release version)
        - Run "dcmanager subcloud deploy upload" with prestaging images enabled using the deployed release version
        - Validate that prestaging images are present in the deploy show object.
        - Validate that the software version in the deploy show object matches the selected release version
    """
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Get deployed release version
    software_list_keywords = SoftwareListKeywords(ssh_connection)
    software_list_output = software_list_keywords.get_software_list()
    deployed_version = software_list_output.get_product_version_by_state("deployed")
    validate_not_equals(len(deployed_version), 0, "deployed releases found")

    # Execute deploy upload with prestaging images enabled and deployed release version
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)
    deploy_show_obj = dcm_sc_deploy_kw.dcmanager_subcloud_deploy_upload(prestaging_images=True, release_version=deployed_version[0]).get_dcmanager_subcloud_deploy_show_object()
    validate_not_equals(deploy_show_obj.get_prestage_images(), None, "Prestage images exist")
    validate_equals(deployed_version[0], deploy_show_obj.get_software_version(), "version matched")


@mark.p2
def test_dcmanager_subcloud_deploy_upload_with_prestaging_images_inactive_load():
    """
    Test dcmanager subcloud deploy upload with prestaging images using inactive load release version.

    Test Steps:
        - Get SSH connection to the active controller of the system controller
        - Retrieve the list of software releases
        - Identify a release that is in "unavailable" state (inactive load release version)
        - Run "dcmanager subcloud deploy upload" with prestaging images enabled using the unavailable release version
        - Validate that prestaging images are present in the deploy show object.
        - Validate that the software version in the deploy show object matches the selected release version
    """
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Get unavailable release version
    software_list_keywords = SoftwareListKeywords(ssh_connection)
    software_list_output = software_list_keywords.get_software_list()

    # Find a release that is not in "available" state
    unavailable_version = software_list_output.get_product_version_by_state("unavailable")
    validate_not_equals(len(unavailable_version), 0, "unavailable releases found")

    # Execute deploy upload with prestaging images enabled and unavailable release version
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)
    deploy_show_obj = dcm_sc_deploy_kw.dcmanager_subcloud_deploy_upload(prestaging_images=True, release_version=unavailable_version[0]).get_dcmanager_subcloud_deploy_show_object()
    validate_not_equals(deploy_show_obj.get_prestage_images(), None, "Prestage images exist")
    validate_equals(unavailable_version[0], deploy_show_obj.get_software_version(), "version matched")
