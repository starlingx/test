"""
Validate the behavior of platform applications with dependencies uploaded and applied before and after platform upgrade

Description
- test_upload_apps_with_dependencies - upload all platform app with dependency
- test_apps_with_dependencies_uploaded_after_platform_upgrade - check the status of platform app with dependency uploaded
- test_upload_and_apply_apps_with_dependencies - upload and apply all platform app with dependency
- test_apps_with_dependencies_applied_after_platform_upgrade - check the status of platform app with dependency applied
- test_remove_apps_with_dependencies - remove platform app with dependency

Validate uploaded apps
 - Run test_upload_apps_with_dependencies. Perform platform upgrade. Run test_apps_with_dependencies_uploaded_after_platform_upgrade to validate the uploaded apps.
  Run test_remove_apps_with_dependencies to delete the apps

Validate applied apps
 - Run test_upload_and_apply_apps_with_dependencies. Perform platform upgrade. Run test_apps_with_dependencies_applied_after_platform_upgrade to validate the uploaded apps.
 Run test_remove_apps_with_dependencies to delete the apps
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords

APPS_BASE_PATH = "/usr/local/share/applications/helm/"

APPS_WITH_DEPENDENCIES = [
    "node-feature-discovery",
    "intel-device-plugins-operator",
    "kubernetes-power-manager",
    "openbao",
    "oran-o2",
    "vault",
]


@mark.p2
def test_upload_apps_with_dependencies() -> None:
    """Test uploading all platform apps that have inter-app dependencies.

    This test validates that each application with declared dependent_apps
    in its metadata can be uploaded successfully and reaches 'uploaded' status
    with progress 'completed'.

    Test Steps:
        - Get SSH connection to active controller
        - For each app with dependencies:
            - Delete the app if already present
            - Upload the app tarball
            - Verify application status is 'uploaded'
            - Verify application progress is 'completed'
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)
    delete_keywords = SystemApplicationDeleteKeywords(ssh_connection)
    upload_keywords = SystemApplicationUploadKeywords(ssh_connection)
    show_keywords = SystemApplicationShowKeywords(ssh_connection)

    for app_name in APPS_WITH_DEPENDENCIES:
        get_logger().log_test_case_step(f"Remove existing {app_name} if present")
        if app_list_keywords.is_app_present(app_name):
            delete_input = SystemApplicationDeleteInput()
            delete_input.set_app_name(app_name)
            delete_input.set_force_deletion(True)
            delete_keywords.get_system_application_delete(delete_input)

        get_logger().log_test_case_step(f"Upload {app_name}")
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(app_name)
        upload_input.set_tar_file_path(f"{APPS_BASE_PATH}{app_name}*.tgz")
        upload_keywords.system_application_upload(upload_input)

        get_logger().log_test_case_step(f"Verify {app_name} status is 'uploaded'")
        app_list_keywords.validate_app_status(app_name, "uploaded")

        get_logger().log_test_case_step(f"Verify {app_name} progress is 'completed'")
        show_keywords.validate_app_progress_contains(app_name, "completed")


@mark.p2
def test_apps_with_dependencies_uploaded_after_platform_upgrade() -> None:
    """Test that apps with dependencies have 'uploaded' status after platform upgrade.

    This test validates that each application with declared dependent_apps
    in its metadata is present and has 'uploaded' status after a platform upgrade.

    Test Steps:
        - Get SSH connection to active controller
        - For each app with dependencies:
            - Verify the app is present
            - Verify application status is 'uploaded'
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)

    for app_name in APPS_WITH_DEPENDENCIES:
        get_logger().log_test_case_step(f"Verify {app_name} is present and uploaded after platform upgrade")
        system_applications = app_list_keywords.get_system_application_list()
        validate_equals(system_applications.is_in_application_list(app_name), True, f"{app_name} should be present after platform upgrade")
        app_status = system_applications.get_application(app_name).get_status()
        validate_equals(app_status, "uploaded", f"{app_name} should have 'uploaded' status after platform upgrade")


@mark.p2
def test_upload_and_apply_apps_with_dependencies() -> None:
    """Test uploading and applying all platform apps that have inter-app dependencies.

    This test validates that each application with declared dependent_apps
    in its metadata can be uploaded and applied successfully.

    Test Steps:
        - Get SSH connection to active controller
        - For each app with dependencies:
            - Delete the app if already present
            - Upload the app tarball
            - Verify application status is 'uploaded'
            - Verify application progress is 'completed'
            - Apply the app
            - Verify application status is 'applied'
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)
    delete_keywords = SystemApplicationDeleteKeywords(ssh_connection)
    upload_keywords = SystemApplicationUploadKeywords(ssh_connection)
    show_keywords = SystemApplicationShowKeywords(ssh_connection)
    apply_keywords = SystemApplicationApplyKeywords(ssh_connection)

    for app_name in APPS_WITH_DEPENDENCIES:
        get_logger().log_test_case_step(f"Remove existing {app_name} if present")
        if app_list_keywords.is_app_present(app_name):
            delete_input = SystemApplicationDeleteInput()
            delete_input.set_app_name(app_name)
            delete_input.set_force_deletion(True)
            delete_keywords.get_system_application_delete(delete_input)

        get_logger().log_test_case_step(f"Upload {app_name}")
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(app_name)
        upload_input.set_tar_file_path(f"{APPS_BASE_PATH}{app_name}*.tgz")
        upload_keywords.system_application_upload(upload_input)

        get_logger().log_test_case_step(f"Verify {app_name} status is 'uploaded'")
        app_list_keywords.validate_app_status(app_name, "uploaded")

        get_logger().log_test_case_step(f"Verify {app_name} progress is 'completed'")
        show_keywords.validate_app_progress_contains(app_name, "completed")

        get_logger().log_test_case_step(f"Apply {app_name}")
        apply_keywords.system_application_apply(app_name)

        get_logger().log_test_case_step(f"Verify {app_name} status is 'applied'")
        app_list_keywords.validate_app_status(app_name, "applied")


@mark.p2
def test_apps_with_dependencies_applied_after_platform_upgrade() -> None:
    """Test that apps with dependencies have 'applied' status after platform upgrade.

    This test validates that each application with declared dependent_apps
    in its metadata is present and has 'applied' status after a platform upgrade.

    Test Steps:
        - Get SSH connection to active controller
        - For each app with dependencies:
            - Verify the app is present
            - Verify application status is 'applied'
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)

    for app_name in APPS_WITH_DEPENDENCIES:
        get_logger().log_test_case_step(f"Verify {app_name} is present and applied after platform upgrade")
        system_applications = app_list_keywords.get_system_application_list()
        validate_equals(system_applications.is_in_application_list(app_name), True, f"{app_name} should be present after platform upgrade")
        app_status = system_applications.get_application(app_name).get_status()
        validate_equals(app_status, "applied", f"{app_name} should have 'applied' status after platform upgrade")


@mark.p2
def test_remove_apps_with_dependencies() -> None:
    """Test removing all platform apps that have inter-app dependencies.

    This test removes and deletes each application that declares dependent_apps
    in its metadata, if present on the system.

    Test Steps:
        - Get SSH connection to active controller
        - For each app with dependencies:
            - Remove and delete the app if present
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)
    remove_keywords = SystemApplicationRemoveKeywords(ssh_connection)

    for app_name in APPS_WITH_DEPENDENCIES:
        get_logger().log_test_case_step(f"Remove {app_name} if present")
        if app_list_keywords.is_app_present(app_name):
            remove_keywords.cleanup_app_if_present(app_name, force_removal=True, force_deletion=True)
        else:
            get_logger().log_info(f"{app_name} not present, skipping")
