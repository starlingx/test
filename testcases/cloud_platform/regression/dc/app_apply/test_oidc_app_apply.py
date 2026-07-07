from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords


def ensure_oidc_app_installed(subcloud_ssh: SSHConnection) -> bool:
    """Ensure OIDC app is installed on subcloud. Install if not present.

    Args:
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.

    Returns:
        bool: True if app was already installed, False if newly installed.
    """
    app_name = "oidc-auth-apps"
    app_path = "/usr/local/share/applications/helm/"

    app_list_keywords = SystemApplicationListKeywords(subcloud_ssh)
    app_list = app_list_keywords.get_system_application_list()

    if app_list.application_exists(app_name):
        app = app_list.get_application(app_name)
        if app.get_status() == "applied":
            get_logger().log_info(f"OIDC app {app_name} is already installed and applied")
            return True

    get_logger().log_info(f"Installing OIDC app {app_name} on subcloud")

    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name(app_name)
    upload_input.set_force(True)
    upload_input.set_tar_file_path(app_path + app_name + "*")

    upload_output = SystemApplicationUploadKeywords(subcloud_ssh).system_application_upload(upload_input)
    app_object = upload_output.get_system_application_object()
    validate_equals(app_object.get_status(), "uploaded", f"OIDC app {app_name} should be uploaded")

    apply_output = SystemApplicationApplyKeywords(subcloud_ssh).system_application_apply(app_name, 3600, 30)
    app_object = apply_output.get_system_application_object()
    validate_equals(app_object.get_status(), "applied", f"OIDC app {app_name} should be applied")

    return False


def validate_oidc_app_installed(subcloud_ssh: SSHConnection) -> None:
    """Validate that OIDC app is installed and applied on subcloud.

    Args:
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.
    """
    app_name = "oidc-auth-apps"

    app_list_keywords = SystemApplicationListKeywords(subcloud_ssh)
    app_list = app_list_keywords.get_system_application_list()

    validate_equals(app_list.is_application_in_output(app_name), True, f"OIDC app {app_name} should be present")

    app = app_list.get_application_by_name(app_name)
    validate_equals(app.get_status(), "applied", f"OIDC app {app_name} should be applied")

    get_logger().log_info(f"OIDC app {app_name} validation successful")


@mark.p2
@mark.lab_has_subcloud
def test_oidc_app_applied_on_subcloud(request):
    """
    Verify OIDC app is installed and applied on a subcloud.

    This test ensures the oidc-auth-apps application is uploaded and applied
    on a subcloud. If not present, it installs it. Can be used as a standalone
    validation or as a pipeline step after rehoming to confirm app persistence.

    If no matching subcloud is found on the primary system controller and a
    secondary system controller is configured, the test falls back to the
    secondary. This supports post-rehoming pipeline scenarios where subclouds
    may have moved to the peer cloud.

    Prerequisites:
        - At least one subcloud must be online.

    Setup:
        - Find an online subcloud (with fallback to secondary SC)

    Test Steps:
        1. Find an online subcloud
        2. Ensure OIDC app is installed and applied on the subcloud
        3. Validate OIDC app status is applied

    Teardown:
        - None
    """
    _, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        present_in_config=True,
    )

    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Ensure OIDC app is installed and applied
    get_logger().log_info(f"Ensuring OIDC app is installed on subcloud {subcloud_name}")
    ensure_oidc_app_installed(subcloud_ssh)

    # Validate OIDC app is applied
    get_logger().log_info(f"Validating OIDC app is applied on subcloud {subcloud_name}")
    validate_oidc_app_installed(subcloud_ssh)
