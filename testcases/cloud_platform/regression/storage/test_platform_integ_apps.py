import re
from typing import List

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_update_input import SystemApplicationUpdateInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_abort_keywords import SystemApplicationAbortKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.application.system_application_update_keywords import SystemApplicationUpdateKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.continuous_write.kubectl_continuous_write_keywords import KubectlContinuousWriteKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.mount.mount_keywords import MountKeywords


def setup(request, active_ssh_connection):
    """Setup function to ensure platform-integ-apps is applied before tests."""
    app_config = ConfigurationManager.get_app_config()
    platform_integ_apps_name = app_config.get_platform_integ_apps_app_name()
    get_logger().log_setup_step("Checking ceph health.")
    ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)
    get_logger().log_setup_step("Check app platform-integ-apps is applied.")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(platform_integ_apps_name, "applied")

    def cleanup():
        if not SystemApplicationListKeywords(active_ssh_connection).is_app_present(platform_integ_apps_name):
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)
        get_logger().log_teardown_step("Checking ceph health.")
        ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
        ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    request.addfinalizer(cleanup)
    return platform_integ_apps_name


def verify_provisioner(ssh_connection: SSHConnection, pod_names: List[str], expected_status: str, namespace: str) -> None:
    """Function to verify if the rbd provisioner pods are running"""
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(
        expected_status=expected_status,
        pod_names=pod_names,
        namespace=namespace,
        timeout=300,
    )


@mark.p2
def test_remove_apply_platform_integ_app(request):
    """
    Remove and apply the platform-integ-apps  application.
    Test Steps:
        - Run this command "system application-remove platform-integ-apps"
        - The status of the application should change to uploaded
        - Run this command "system application-apply"
        - The platform-integ-apps application was applied
    Args: None
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)
    get_logger().log_test_case_step("Remove platform-integ-apps")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(platform_integ_apps_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
    get_logger().log_test_case_step("Apply platform-integ-apps")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)


@mark.p2
def test_delete_platform_integ_app(request):
    """
    Delete platform-integ-apps application.
    Test Steps:
        - Run this command "system application-remove platform-integ-apps"
        - The status of the application should change to uploaded
        - Run this command "system application-delete"
        - The platform-integ-apps application was deleted
    Args: None
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Test- Testdown: Upload platform-integ-apps")
        app_config = ConfigurationManager.get_app_config()
        base_path = app_config.get_base_application_path()
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(platform_integ_apps_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{platform_integ_apps_name}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)
        get_logger().log_teardown_step("Apply platform-integ-apps")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)

    request.addfinalizer(teardown)
    get_logger().log_test_case_step("Remove platform-integ-apps")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(platform_integ_apps_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
    get_logger().log_test_case_step("Delete platform-integ-apps")
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(platform_integ_apps_name)
    app_delete_response = SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(app_delete_response.rstrip(), "Application platform-integ-apps deleted.", "Application deletion.")


@mark.p2
def test_abort_platform_integ_app(request: FixtureRequest):
    """
    Abort platform-integ-apps application during apply process.

    Test Steps:
        - Run this command "system application-remove platform-integ-apps"
        - The status of the application should change to uploaded
        - Run this command "system application-apply"
        - Run this command "system application-abort platform-integ-apps"

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Check if application status is not applied and apply if needed")
        app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
        if app_list_keywords.is_app_present(platform_integ_apps_name):
            system_applications = app_list_keywords.get_system_application_list()
            current_status = system_applications.get_application(platform_integ_apps_name).get_status()
            if current_status != "applied":
                get_logger().log_teardown_step("Apply platform-integ-apps")
                SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Remove platform-integ-apps")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(platform_integ_apps_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Apply platform-integ-apps")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name, wait_for_applied=False)

    get_logger().log_test_case_step("Abort platform-integ-apps")
    SystemApplicationAbortKeywords(active_ssh_connection).system_application_abort(app_name=platform_integ_apps_name)

    get_logger().log_test_case_step("Validate application status changed to apply-failed")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(platform_integ_apps_name, "apply-failed")


@mark.p2
def test_rollback_platform_integ_app(request: FixtureRequest):
    """
    Rollback platform-integ-apps application to a previous version.

    Test Steps:
        - Record current version of platform-integ-apps
        - Transfer tarball from local machine to /home/sysadmin
        - Mount /usr with read-write permissions
        - Copy tarball to /usr/local/share/applications/helm/
        - Execute system application-update with tarball filename
        - Verify the platform-integ-apps version has changed (rollback)

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current platform-integ-apps version")
    current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
    current_version = current_app_info.get_system_application_object().get_version()

    # Validate tarball version differs from installed version
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_platform_integ_app_tarball().split("/")[-1]
    tarball_version = re.search(r"platform-integ-apps-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Tarball version must differ from installed version")

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        # An update/rollback that is interrupted (e.g. aborted) leaves the app in the
        # transient 'recovering' state, and sysinv rejects abort/remove/apply while
        # recovering. Wait for the app to settle into a terminal state before acting.
        get_logger().log_teardown_step("Wait for platform-integ-apps to leave transient state")
        SystemApplicationListKeywords(active_ssh_connection).validate_app_status_in_list(platform_integ_apps_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original platform-integ-apps version")
            # Remove the rolled back version. platform-integ-apps is a platform-managed
            # storage app, so a non-forced remove can be rejected by the CLI (rc=1). Force
            # the removal and allow enough time for the ceph/rbd resources to be torn down
            # so teardown is reliable.
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(platform_integ_apps_name)
            system_application_remove_input.set_force_removal(True)
            system_application_remove_input.set_timeout_in_seconds(300)
            SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

            # Delete the rolled back version
            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(platform_integ_apps_name)
            SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)

            # Copy original tarball from /home/sysadmin to base_application_path
            get_logger().log_teardown_step("Copy original tarball to base application path")
            FileKeywords(active_ssh_connection).move_file("/home/sysadmin/platform-integ-app*.tgz", app_config.get_base_application_path(), sudo=True)

            # Move rollback tarball from base_application_path to /home/sysadmin
            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(active_ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

            # Upload original version
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(platform_integ_apps_name)
            system_application_upload_input.set_tar_file_path(f"{app_config.get_base_application_path()}platform-integ-app*.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

            # Apply original version
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)

            # Delete tarball file from /home/sysadmin
            get_logger().log_teardown_step("Delete tarball file from /home/sysadmin")
            FileKeywords(active_ssh_connection).delete_file(f"/home/sysadmin/{tarball_filename}")
        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")

    request.addfinalizer(teardown)

    # Transfer tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_platform_integ_app_tarball().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(active_ssh_connection).upload_file(app_config.get_platform_integ_app_tarball(), temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(active_ssh_connection).remount_read_write("/usr")

    # Copy platform_integ_app*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Move platform_integ_app*.tgz to /home/sysadmin")
    FileKeywords(active_ssh_connection).move_file(f"{app_config.get_base_application_path()}platform-integ-app*.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Move tarball to base application path")
    FileKeywords(active_ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    # Rollback platform-integ-apps with tarball
    get_logger().log_test_case_step("Rollback platform-integ-apps with tarball")
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(platform_integ_apps_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(120)
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Verify the application version has changed (rollback)
    get_logger().log_test_case_step("Verify platform-integ-apps version has changed after rollback")
    rollback_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")


@mark.p2
def test_update_platform_integ_app(request: FixtureRequest):
    """
    Update platform-integ-apps application.

    Test Steps:
        - Roll back the platform-integ-apps
        - Remove tarball from application base path
        - Copy tarball from /home/sysadmin to application base path
        - Check if the application was upgraded

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        # An update/rollback that is interrupted (e.g. aborted) leaves the app in the
        # transient 'recovering' state, and sysinv rejects abort/remove/apply while
        # recovering. Wait for the app to settle into a terminal state before acting.
        get_logger().log_teardown_step("Wait for platform-integ-apps to leave transient state")
        SystemApplicationListKeywords(active_ssh_connection).validate_app_status_in_list(platform_integ_apps_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original platform-integ-apps version")

            # platform-integ-apps is a platform-managed storage app with dependents, so a
            # non-forced remove is rejected by the CLI (rc=1). Force the removal and allow
            # enough time for the ceph/rbd resources to be torn down so teardown is reliable.
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(platform_integ_apps_name)
            system_application_remove_input.set_force_removal(True)
            system_application_remove_input.set_timeout_in_seconds(300)
            SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

            # Delete the rolled back version
            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(platform_integ_apps_name)
            SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)

            # Copy original tarball from /home/sysadmin to base_application_path
            get_logger().log_teardown_step("Move original tarball to base application path")
            FileKeywords(active_ssh_connection).move_file("/home/sysadmin/platform-integ-app*.tgz", app_config.get_base_application_path(), sudo=True)

            # Move rollback tarball from base_application_path to /home/sysadmin
            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(active_ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

            # Upload original version
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(platform_integ_apps_name)
            system_application_upload_input.set_tar_file_path(f"{app_config.get_base_application_path()}platform-integ-app*.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

            # Apply original version
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)

            # Delete tarball file from /home/sysadmin
            get_logger().log_teardown_step("Delete tarball file from /home/sysadmin")
            FileKeywords(active_ssh_connection).delete_file(f"/home/sysadmin/{tarball_filename}")
        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")

    request.addfinalizer(teardown)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current platform-integ-apps version")
    current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
    current_version = current_app_info.get_system_application_object().get_version()

    # Validate tarball version differs from installed version
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_platform_integ_app_tarball().split("/")[-1]
    tarball_version = re.search(r"platform-integ-apps-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Tarball version must differ from installed version")

    # Transfer tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_platform_integ_app_tarball().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(active_ssh_connection).upload_file(app_config.get_platform_integ_app_tarball(), temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(active_ssh_connection).remount_read_write("/usr")

    # Copy platform_integ_app*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Move platform_integ_app*.tgz to /home/sysadmin")
    FileKeywords(active_ssh_connection).move_file(f"{app_config.get_base_application_path()}platform-integ-app*.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Move tarball to base application path")
    FileKeywords(active_ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    # Rollback platform-integ-apps with tarball
    get_logger().log_test_case_step("Rollback platform-integ-apps with tarball")
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(platform_integ_apps_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(220)
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Verify the application version has changed (rollback)
    get_logger().log_test_case_step("Verify platform-integ-apps version has changed after rollback")
    rollback_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")

    # Remove tarball from application base path
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(active_ssh_connection).delete_file(f"{app_config.get_base_application_path()}{tarball_filename}")

    # Move tarball from /home/sysadmin to base application path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to base application path")
    FileKeywords(active_ssh_connection).move_file("/home/sysadmin/platform-integ-app*.tgz", app_config.get_base_application_path(), sudo=True)

    # Update platform-integ-apps with new tarball
    get_logger().log_test_case_step("Update platform-integ-apps with new tarball")
    upgrade_tarball_path = f"{app_config.get_base_application_path()}platform-integ-app*.tgz"
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(platform_integ_apps_name)
    system_application_update_input.set_tar_file_path(upgrade_tarball_path)
    system_application_update_input.set_timeout_in_seconds(120)
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Check if the application was upgraded
    get_logger().log_test_case_step("Check if the application was upgraded")
    upgraded_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
    upgraded_version = upgraded_app_info.get_system_application_object().get_version()
    validate_equals(upgraded_version, current_version, "Application version should match original version after upgrade")
    get_logger().log_info(f"Application status after upgrade: {upgraded_app_info.get_system_application_object()}")


@mark.p2
def test_update_helm_chart_user_overrides_platform_integ_app(request: FixtureRequest):
    """
    Update helm chart user overrides for platform-integ-apps application.

    Test Steps:
        - Show initial helm override properties and values
        - Set user_overrides default debug to true
        - Verify the update was applied correctly
        - Clean up by deleting the helm override

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)

    chart_name = "ceph-pools-audit"
    namespace = "kube-system"

    def teardown():
        get_logger().log_teardown_step("Delete helm override")
        helm_override_keywords.delete_system_helm_override(platform_integ_apps_name, chart_name, namespace)

        get_logger().log_teardown_step("Verify helm override was deleted")
        final_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
        final_user_overrides = final_override_show.get_helm_override_show().get_user_overrides()
        validate_equals(final_user_overrides, "None", "User overrides should be None after deletion")

    request.addfinalizer(teardown)

    # Show initial helm override properties and values
    get_logger().log_test_case_step("Show initial helm override properties and values")
    initial_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
    initial_user_overrides = initial_override_show.get_helm_override_show().get_user_overrides()
    get_logger().log_info(f"Initial user overrides: {initial_user_overrides}")

    # Set user_overrides default debug to true
    get_logger().log_test_case_step("Set user_overrides default debug to true")
    override_values = "conf.kube-system.DEFAULT.DEBUG=true"
    helm_override_keywords.update_helm_override_via_set(override_values, platform_integ_apps_name, chart_name, namespace)

    # Verify the update was applied correctly
    get_logger().log_test_case_step("Verify the update was applied correctly")
    updated_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
    updated_user_overrides = updated_override_show.get_helm_override_show().get_user_overrides()

    validate_str_contains(updated_user_overrides, "DEBUG: true", "User overrides should contain DEBUG: true")
    validate_str_contains(updated_user_overrides, "kube-system", "User overrides should contain kube-system namespace")
    get_logger().log_info(f"Updated user overrides: {updated_user_overrides}")


@mark.p2
def test_delete_helm_chart_user_overrides_platform_integ_app(request: FixtureRequest):
    """
    Delete helm chart user overrides for platform-integ-apps application.

    Test Steps:
        - Show initial helm override properties and values
        - Set user_overrides default debug to true
        - Delete the user-overrides configuration
        - Verify the delete was successful

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)

    chart_name = "ceph-pools-audit"
    namespace = "kube-system"

    def teardown():
        get_logger().log_teardown_step("Check and delete helm override if needed")
        current_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
        current_user_overrides = current_override_show.get_helm_override_show().get_user_overrides()
        if current_user_overrides != "None":
            helm_override_keywords.delete_system_helm_override(platform_integ_apps_name, chart_name, namespace)

    request.addfinalizer(teardown)

    # Show initial helm override properties and values
    get_logger().log_test_case_step("Show initial helm override properties and values")
    initial_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
    get_logger().log_info(f"Initial user overrides: {initial_override_show.get_helm_override_show().get_user_overrides()}")

    # Set user_overrides default debug to true
    get_logger().log_test_case_step("Set user_overrides default debug to true")
    override_values = "conf.kube-system.DEFAULT.DEBUG=true"
    helm_override_keywords.update_helm_override_via_set(override_values, platform_integ_apps_name, chart_name, namespace)

    # Delete the user-overrides configuration
    get_logger().log_test_case_step("Delete the user-overrides configuration")
    helm_override_keywords.delete_system_helm_override(platform_integ_apps_name, chart_name, namespace)

    # Verify the delete was successful
    get_logger().log_test_case_step("Verify the delete was successful")
    final_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
    final_user_overrides = final_override_show.get_helm_override_show().get_user_overrides()
    validate_equals(final_user_overrides, "None", "User overrides should be None after deletion")
    get_logger().log_info(f"Final user overrides: {final_user_overrides}")


@mark.p2
def test_modify_helm_chart_attribute_platform_integ_app(request: FixtureRequest):
    """
    Modify helm chart attribute for platform-integ-apps application.

    Test Steps:
        - Show initial helm override properties and values
        - Set the enabled parameter to true
        - Verify it was enabled
        - Set the enabled parameter to false
        - Verify it was disabled

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)
    helm_attribute_keywords = SystemHelmChartAttributeModifyKeywords(active_ssh_connection)

    chart_name = "ceph-pools-audit"
    namespace = "kube-system"

    def teardown():
        get_logger().log_teardown_step("Check and set enabled attribute to false if needed")
        current_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
        current_attributes = current_override_show.get_helm_override_show().get_attributes()
        if "enabled: true" in str(current_attributes):
            helm_attribute_keywords.helm_chart_attribute_modify_enabled("false", platform_integ_apps_name, chart_name, namespace)

    request.addfinalizer(teardown)

    # Show initial helm override properties and values
    get_logger().log_test_case_step("Show initial helm override properties and values")
    initial_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
    initial_attributes = initial_override_show.get_helm_override_show().get_attributes()
    get_logger().log_info(f"Initial attributes: {initial_attributes}")

    # Set the enabled parameter to true
    get_logger().log_test_case_step("Set the enabled parameter to true")
    helm_attribute_keywords.helm_chart_attribute_modify_enabled("true", platform_integ_apps_name, chart_name, namespace)

    # Verify it was enabled
    get_logger().log_test_case_step("Verify it was enabled")
    enabled_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
    enabled_attributes = enabled_override_show.get_helm_override_show().get_attributes()
    validate_str_contains(str(enabled_attributes), "enabled: true", "Attributes should contain enabled: true")
    get_logger().log_info(f"Enabled attributes: {enabled_attributes}")

    # Set the enabled parameter to false
    get_logger().log_test_case_step("Set the enabled parameter to false")
    helm_attribute_keywords.helm_chart_attribute_modify_enabled("false", platform_integ_apps_name, chart_name, namespace)

    # Verify it was disabled
    get_logger().log_test_case_step("Verify it was disabled")
    disabled_override_show = helm_override_keywords.get_system_helm_override_show(platform_integ_apps_name, chart_name, namespace)
    disabled_attributes = disabled_override_show.get_helm_override_show().get_attributes()
    validate_str_contains(str(disabled_attributes), "enabled: false", "Attributes should contain enabled: false")
    get_logger().log_info(f"Disabled attributes: {disabled_attributes}")


@mark.p2
@mark.lab_has_ceph
def test_disable_and_re_enable_rbd_provisioner_platform_integ_app(request: FixtureRequest):
    """
    Modify helm chart attribute rbd provisioner to false and verify the rbd pods

    Test Steps:
        - Make sure that platform-integ-apps is applied
        - Verify if platform-integ-apps rbd provisioner pods are running
        - Create a PVC and wait for it to be bound to RBD storageClass
        - Create a Pod with continuous writing to the bound PVC
        - Check if the continous writing Pod is working
        - Set the rbd provisioner to false
        - Apply the platform-integ-apps
        - Check if the rbd provisioner Pods disappeared
        - Set the rbd provisioner to true
        - Apply the platform-integ-apps
        - Verify if platform-integ-apps rbd provisioner pods are running
        - Verify if the Pod/PVC keep working properly (Bound/Running)

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(active_ssh_connection)
    platform_integ_apps_name = setup(request, active_ssh_connection)

    continuous_write_keywords = KubectlContinuousWriteKeywords(active_ssh_connection)
    namespace = "kube-system"
    rbd_pod_names = ["rbd-provisioner"]
    storage_type = "rbd"
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Check if application status is not applied and apply if needed")
        app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
        if app_list_keywords.is_app_present(platform_integ_apps_name):
            system_applications = app_list_keywords.get_system_application_list()
            current_status = system_applications.get_application(platform_integ_apps_name).get_status()
            if current_status != "applied":
                get_logger().log_teardown_step("Apply platform-integ-apps")
                SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)

        get_logger().log_teardown_step("Set the rbd provisioner to true")
        SystemHelmChartAttributeModifyKeywords(active_ssh_connection).helm_chart_attribute_modify_enabled(
            enabled_value="true",
            app_name="platform-integ-apps",
            chart_name="rbd-provisioner",
            namespace=namespace,
        )

        get_logger().log_teardown_step("Apply the platform-integ-apps")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)
        get_logger().log_teardown_step("Verify if platform-integ-apps rbd provisioner pods are running")
        verify_provisioner(active_ssh_connection, rbd_pod_names, "Running", namespace)

        get_logger().log_teardown_step("Verify if the Pod/PVC keep working properly (Bound/Running)")
        kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")

        counts_before = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=0)
        get_logger().log_info(f"{pod_name} write-cycle count before: {counts_before}")

        kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")
        count_after = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=counts_before)
        validate_not_equals(counts_before, count_after, "Making sure counts before and after are not equal (pod is writing)")
        get_logger().log_info(f"{pod_name} write-cycle count after: {count_after}")
        continuous_write_keywords.cleanup_continuous_write_pod(pod_name, pvc_name, force=True)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Remove platform-integ-apps")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(platform_integ_apps_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Apply platform-integ-apps")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name, wait_for_applied=False)
    app_status_list = ["applied"]
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status_in_list(platform_integ_apps_name, app_status_list, timeout=600, polling_sleep_time=20)

    get_logger().log_test_case_step("Verify if platform-integ-apps rbd provisioner pods are running")
    verify_provisioner(active_ssh_connection, rbd_pod_names, "Running", namespace)
    get_logger().log_test_case_step("Create a PVC and wait for it to be bound to RBD storageClass")

    active_controller = system_host_list_keywords.get_active_controller()
    active_host_name = active_controller.get_host_name()
    pod_name, pvc_name = continuous_write_keywords.start_continuous_write_pod(storage_type, node_name=active_host_name)

    get_logger().log_test_case_step(f"Verify {pod_name} is Running")
    kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")

    counts_before = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=0)
    get_logger().log_info(f"{pod_name} write-cycle count before: {counts_before}")
    kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")
    get_logger().log_test_case_step(f"Verify {pod_name} kept writing after.")
    count_after = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=counts_before)
    validate_not_equals(counts_before, count_after, "Making sure counts before and after are not equal (pod is writing)")
    get_logger().log_info(f"{pod_name} write-cycle count after: {count_after}")

    get_logger().log_test_case_step("Set the rbd provisioner to false")

    SystemHelmChartAttributeModifyKeywords(active_ssh_connection).helm_chart_attribute_modify_enabled(
        enabled_value="false",
        app_name="platform-integ-apps",
        chart_name="rbd-provisioner",
        namespace=namespace,
    )

    get_logger().log_test_case_step("Apply the platform-integ-apps")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name, wait_for_applied=False)
    app_status_list = ["applied"]
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status_in_list(platform_integ_apps_name, app_status_list, timeout=600, polling_sleep_time=20)

    get_logger().log_test_case_step("Check if the rbd provisioner Pods disappeared")
    pods = KubectlGetPodsKeywords(active_ssh_connection).get_pods(namespace=namespace)
    rbd_pods = pods.get_pods_start_with("rbd-provisioner")
    validate_equals(len(rbd_pods), 0, "rbd-provisioner pods should be gone after disable + apply")

    counts_before = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=0)
    get_logger().log_test_case_step(f"Verify {pod_name} kept writing after:")

    kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")
    count_after = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=counts_before)
    validate_not_equals(counts_before, count_after, "Making sure counts before and after are not equal (pod is writing)")
    get_logger().log_info(f"{pod_name} write-cycle count after: {count_after}")


@mark.p2
@mark.lab_has_ceph
def test_disable_and_re_enable_cephfs_provisioner_platform_integ_app(request: FixtureRequest):
    """
    Modify helm chart attribute cephfs provisioner to false and verify the cephfs pods

    Test Steps:
        - Make sure that platform-integ-apps is applied
        - Verify if platform-integ-apps cephfs provisioner pods are running
        - Create a PVC and wait for it to be bound to CEPHFS storageClass
        - Create a Pod with continuous writing to the bound PVC
        - Check if the continous writing Pod is working
        - Set the cephfs provisioner to false
        - Apply the platform-integ-apps
        - Check if the cephfs provisioner Pods disappeared
        - Set the cephfs provisioner to true
        - Apply the platform-integ-apps
        - Verify if platform-integ-apps cephfs provisioner pods are running
        - Verify if the Pod/PVC keep working properly (Bound/Running)

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(active_ssh_connection)
    platform_integ_apps_name = setup(request, active_ssh_connection)

    continuous_write_keywords = KubectlContinuousWriteKeywords(active_ssh_connection)
    namespace = "kube-system"
    cephfs_pod_names = ["cephfs-provisioner"]
    storage_type = "cephfs"
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Check if application status is not applied and apply if needed")
        app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
        if app_list_keywords.is_app_present(platform_integ_apps_name):
            system_applications = app_list_keywords.get_system_application_list()
            current_status = system_applications.get_application(platform_integ_apps_name).get_status()
            if current_status != "applied":
                get_logger().log_teardown_step("Apply platform-integ-apps")
                SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)

        get_logger().log_teardown_step("Set the cephfs provisioner to true")
        SystemHelmChartAttributeModifyKeywords(active_ssh_connection).helm_chart_attribute_modify_enabled(enabled_value="true", app_name="platform-integ-apps", chart_name="cephfs-provisioner", namespace=namespace)

        get_logger().log_teardown_step("Apply the platform-integ-apps")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)
        get_logger().log_teardown_step("Verify if platform-integ-apps cephfs provisioner pods are running")
        verify_provisioner(active_ssh_connection, cephfs_pod_names, "Running", namespace)

        get_logger().log_teardown_step("Verify if the Pod/PVC keep working properly (Bound/Running)")
        kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")

        counts_before = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=0)
        get_logger().log_info(f"{pod_name} write-cycle count before: {counts_before}")

        kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")
        count_after = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=counts_before)
        get_logger().log_info(f"{pod_name} write-cycle count after: {count_after}")
        validate_not_equals(counts_before, count_after, "Making sure counts before and after are not equal (pod is writing)")
        continuous_write_keywords.cleanup_continuous_write_pod(pod_name, pvc_name, force=True)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Remove platform-integ-apps")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(platform_integ_apps_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Apply platform-integ-apps")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name, wait_for_applied=False)
    app_status_list = ["applied"]
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status_in_list(platform_integ_apps_name, app_status_list, timeout=600, polling_sleep_time=20)

    get_logger().log_test_case_step("Verify if platform-integ-apps cephfs provisioner pods are running")
    verify_provisioner(active_ssh_connection, cephfs_pod_names, "Running", namespace)
    get_logger().log_test_case_step("Create a PVC and wait for it to be bound to CEPHFS storageClass")

    active_controller = system_host_list_keywords.get_active_controller()
    active_host_name = active_controller.get_host_name()
    pod_name, pvc_name = continuous_write_keywords.start_continuous_write_pod(storage_type, node_name=active_host_name)

    get_logger().log_test_case_step(f"Verify {pod_name} is Running")
    kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")

    counts_before = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=0)
    get_logger().log_info(f"{pod_name} write-cycle count before: {counts_before}")

    kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")
    count_after = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=counts_before)

    validate_not_equals(counts_before, count_after, "Making sure counts before and after are not equal (pod is writing)")
    get_logger().log_info(f"{pod_name} write-cycle count after: {count_after}")
    get_logger().log_test_case_step("Set the cephfs provisioner to false")

    SystemHelmChartAttributeModifyKeywords(active_ssh_connection).helm_chart_attribute_modify_enabled(
        enabled_value="false",
        app_name="platform-integ-apps",
        chart_name="cephfs-provisioner",
        namespace=namespace,
    )

    get_logger().log_test_case_step("Apply the platform-integ-apps")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name, wait_for_applied=False)
    app_status_list = ["applied"]
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status_in_list(platform_integ_apps_name, app_status_list, timeout=600, polling_sleep_time=20)

    get_logger().log_test_case_step("Check if the cephfs provisioner Pods disappeared")
    pods = KubectlGetPodsKeywords(active_ssh_connection).get_pods(namespace=namespace)
    cephfs_pods = pods.get_pods_start_with("cephfs-provisioner")
    validate_equals(len(cephfs_pods), 0, "cephfs-provisioner pods should be gone after disable + apply")

    counts_before = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=0)
    kubectl_get_pods_keywords.wait_for_pod_status(pod_name, "Running")
    count_after = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=counts_before)
    validate_not_equals(counts_before, count_after, "Making sure counts before and after are not equal (pod is writing)")
    get_logger().log_info(f"{pod_name} write-cycle count after: {count_after}")
