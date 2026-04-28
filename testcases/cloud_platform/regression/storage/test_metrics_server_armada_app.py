from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
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
from keywords.files.file_keywords import FileKeywords
from keywords.linux.mount.mount_keywords import MountKeywords


def setup(request, active_ssh_connection):
    """Setup function to ensure metrics-server is applied before tests."""
    app_config = ConfigurationManager.get_app_config()
    metrics_server_name = app_config.get_metric_server_app_name()
    base_path = app_config.get_base_application_path()

    get_logger().log_setup_step("Checking ceph health.")
    ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
    if not app_list_keywords.is_app_present(metrics_server_name):
        get_logger().log_setup_step("Upload metrics-server app.")
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(metrics_server_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{metrics_server_name}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

    get_logger().log_setup_step("Apply metrics-server app.")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name)

    def cleanup():
        get_logger().log_teardown_step("Cleanup metrics-server app.")
        if app_list_keywords.is_app_present(metrics_server_name):
            app_show = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
            app_status = app_show.get_system_application_object().get_status()

            if app_status == "applied":
                get_logger().log_teardown_step("Remove metrics-server app.")
                system_application_remove_input = SystemApplicationRemoveInput()
                system_application_remove_input.set_app_name(metrics_server_name)
                SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

            get_logger().log_teardown_step("Delete metrics-server app.")
            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(metrics_server_name)
            SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)

        get_logger().log_teardown_step("Checking ceph health.")
        ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    request.addfinalizer(cleanup)
    return metrics_server_name


@mark.p2
def test_remove_apply_metrics_server_app(request):
    """
    Remove and apply the metrics-server application.
    Test Steps:
        - Run this command "system application-remove metrics-server"
        - The status of the application should change to uploaded
        - Run this command "system application-apply"
        - The metrics-server application was applied
    Args: None
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)
    get_logger().log_test_case_step("Remove metrics-server")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(metrics_server_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
    get_logger().log_test_case_step("Apply metrics-server")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name)


@mark.p2
def test_delete_metrics_server_app(request):
    """
    Delete platform-integ-apps application.
    Test Steps:
        - Run this command "system application-remove metrics_server-app"
        - The status of the application should change to uploaded
        - Run this command "system application-delete"
        - The platform-integ-apps application was deleted
    Args: None
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_app_name = setup(request, active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Test- Testdown: Upload metrics-server-app")
        app_config = ConfigurationManager.get_app_config()
        base_path = app_config.get_base_application_path()
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(metrics_server_app_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{metrics_server_app_name}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)
        get_logger().log_teardown_step("Apply metrics_server-app")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_app_name)

    request.addfinalizer(teardown)
    get_logger().log_test_case_step("Remove metrics_server-app")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(metrics_server_app_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
    get_logger().log_test_case_step("Delete metrics_server-app")
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(metrics_server_app_name)
    app_delete_response = SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(app_delete_response.rstrip(), "Application metrics-server deleted.", "Application deletion.")


@mark.p2
def test_abort_metrics_server_app(request: FixtureRequest):
    """
    Abort metrics-server application during apply process.

    Test Steps:
        - Remove the metrics-server application
        - Apply the metrics-server application (non-blocking)
        - Abort the metrics-server application during apply
        - Validate application status changed to apply-failed

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Check if application status is not applied and apply if needed")
        app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
        if app_list_keywords.is_app_present(metrics_server_name):
            system_applications = app_list_keywords.get_system_application_list()
            current_status = system_applications.get_application(metrics_server_name).get_status()
            if current_status != "applied":
                get_logger().log_teardown_step("Apply metrics-server")
                SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Remove metrics-server")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(metrics_server_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Apply metrics-server")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name, wait_for_applied=False)

    get_logger().log_test_case_step("Abort metrics-server")
    SystemApplicationAbortKeywords(active_ssh_connection).system_application_abort(app_name=metrics_server_name)

    get_logger().log_test_case_step("Validate application status changed to apply-failed")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(metrics_server_name, "apply-failed")


def _rollback_metrics_server(request, active_ssh_connection, metrics_server_name, tarball_path):
    """Rollback metrics-server to a previous version using the given tarball.

    Args:
        request (FixtureRequest): pytest request fixture for teardown registration
        active_ssh_connection: SSH connection to the active controller
        metrics_server_name (str): name of the metrics-server application
        tarball_path (str): local path to the rollback tarball
    """
    # Record current version before rollback
    get_logger().log_test_case_step("Record current metrics-server version")
    current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    current_version = current_app_info.get_system_application_object().get_version()

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")
        current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original metrics-server version")
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(metrics_server_name)
            SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(metrics_server_name)
            SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)

            get_logger().log_teardown_step("Copy original tarball to base application path")
            FileKeywords(active_ssh_connection).move_file(f"/home/sysadmin/metrics-server-{current_version}.tgz", app_config.get_base_application_path(), sudo=True)

            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(active_ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(metrics_server_name)
            system_application_upload_input.set_tar_file_path(f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name)

            get_logger().log_teardown_step("Delete tarball file from /home/sysadmin")
            FileKeywords(active_ssh_connection).delete_file(f"/home/sysadmin/{tarball_filename}")
        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")

    request.addfinalizer(teardown)

    # Transfer tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = tarball_path.split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(active_ssh_connection).upload_file(tarball_path, temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(active_ssh_connection).remount_read_write("/usr")

    # Copy metrics-server*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Move metrics-server*.tgz to /home/sysadmin")
    FileKeywords(active_ssh_connection).move_file(f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Move tarball to base application path")
    FileKeywords(active_ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    # Rollback metrics-server with tarball
    get_logger().log_test_case_step("Rollback metrics-server with tarball")
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(metrics_server_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(120)
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Verify the application version has changed (rollback)
    get_logger().log_test_case_step("Verify metrics-server version has changed after rollback")
    rollback_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")


@mark.p2
def test_rollback_metrics_server_app(request: FixtureRequest):
    """
    Rollback metrics-server application to N-1 version.

    Test Steps:
        - Setup metrics-server app
        - Rollback to N-1 version using configured tarball
        - Verify version changed

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)
    tarball_path = ConfigurationManager.get_app_config().get_metrics_server_app_tarball()
    _rollback_metrics_server(request, active_ssh_connection, metrics_server_name, tarball_path)


@mark.p2
def test_update_metrics_server_app(request: FixtureRequest):
    """
    Update metrics-server application from N-1 back to N.

    Test Steps:
        - Setup metrics-server app
        - Rollback to N-1, then upgrade back to current version
        - Verify version restored

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)
    tarball_path = ConfigurationManager.get_app_config().get_metrics_server_app_tarball()
    _update_metrics_server(request, active_ssh_connection, metrics_server_name, tarball_path)


def _update_metrics_server(request, active_ssh_connection, metrics_server_name, tarball_path):
    """Update metrics-server by rolling back then upgrading using the given tarball.

    Args:
        request (FixtureRequest): pytest request fixture for teardown registration
        active_ssh_connection: SSH connection to the active controller
        metrics_server_name (str): name of the metrics-server application
        tarball_path (str): local path to the rollback tarball
    """

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")
        current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original metrics-server version")
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(metrics_server_name)
            SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(metrics_server_name)
            SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)

            get_logger().log_teardown_step("Copy original tarball to base application path")
            FileKeywords(active_ssh_connection).move_file(f"/home/sysadmin/metrics-server-{current_version}.tgz", app_config.get_base_application_path(), sudo=True)

            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(active_ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(metrics_server_name)
            system_application_upload_input.set_tar_file_path(f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name)

            get_logger().log_teardown_step("Delete tarball file from /home/sysadmin")
            FileKeywords(active_ssh_connection).delete_file(f"/home/sysadmin/{tarball_filename}")
        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")

    request.addfinalizer(teardown)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current metrics-server version")
    current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    current_version = current_app_info.get_system_application_object().get_version()

    # Transfer tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = tarball_path.split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(active_ssh_connection).upload_file(tarball_path, temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(active_ssh_connection).remount_read_write("/usr")

    # Copy metrics-server*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Move metrics-server*.tgz to /home/sysadmin")
    FileKeywords(active_ssh_connection).move_file(f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Move tarball to base application path")
    FileKeywords(active_ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    # Rollback metrics-server with tarball
    get_logger().log_test_case_step("Rollback metrics-server with tarball")
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(metrics_server_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(120)
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Verify the application version has changed (rollback)
    get_logger().log_test_case_step("Verify metrics-server version has changed after rollback")
    rollback_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")

    # Remove tarball from application base path
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(active_ssh_connection).delete_file(f"{app_config.get_base_application_path()}{tarball_filename}")

    # Move tarball from /home/sysadmin to base application path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to base application path")
    FileKeywords(active_ssh_connection).move_file(f"/home/sysadmin/metrics-server-{current_version}.tgz", app_config.get_base_application_path(), sudo=True)

    # Update metrics-server with new tarball
    get_logger().log_test_case_step("Update metrics-server with new tarball")
    upgrade_tarball_path = f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz"
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(metrics_server_name)
    system_application_update_input.set_tar_file_path(upgrade_tarball_path)
    system_application_update_input.set_timeout_in_seconds(120)
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Check if the application was upgraded
    get_logger().log_test_case_step("Check if the application was upgraded")
    upgraded_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    upgraded_version = upgraded_app_info.get_system_application_object().get_version()
    validate_equals(upgraded_version, current_version, "Application version should match original version after upgrade")
    get_logger().log_info(f"Application status after upgrade: {upgraded_app_info.get_system_application_object()}")


@mark.p2
def test_rollback_metrics_server_app_n2(request: FixtureRequest):
    """
    Rollback metrics-server application to N-2 version.

    Test Steps:
        - Setup metrics-server app
        - Rollback to N-2 version using configured tarball
        - Verify version changed

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)
    tarball_path = ConfigurationManager.get_app_config().get_metrics_server_app_tarball_n2()
    _rollback_metrics_server(request, active_ssh_connection, metrics_server_name, tarball_path)


@mark.p2
def test_update_metrics_server_app_n2(request: FixtureRequest):
    """
    Update metrics-server application from N-2 back to N.

    Test Steps:
        - Setup metrics-server app
        - Rollback to N-2, then upgrade back to current version
        - Verify version restored

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)
    tarball_path = ConfigurationManager.get_app_config().get_metrics_server_app_tarball_n2()
    _update_metrics_server(request, active_ssh_connection, metrics_server_name, tarball_path)


@mark.p2
def test_update_helm_chart_user_overrides_metrics_server(request: FixtureRequest):
    """
    Update helm chart user overrides for metrics-server application.

    Test Steps:
        - Show initial helm override properties and values
        - Set user_overrides replicaCount to 2
        - Verify the update was applied correctly

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)

    chart_name = metrics_server_name
    namespace = metrics_server_name

    def teardown():
        get_logger().log_teardown_step("Delete helm override")
        helm_override_keywords.delete_system_helm_override(metrics_server_name, chart_name, namespace)

        get_logger().log_teardown_step("Verify helm override was deleted")
        final_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
        final_user_overrides = final_override_show.get_helm_override_show().get_user_overrides()
        validate_equals(final_user_overrides, "None", "User overrides should be None after deletion")

    request.addfinalizer(teardown)

    # Show initial helm override properties and values
    get_logger().log_test_case_step("Show initial helm override properties and values")
    initial_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
    initial_user_overrides = initial_override_show.get_helm_override_show().get_user_overrides()
    get_logger().log_info(f"Initial user overrides: {initial_user_overrides}")

    # Set user_overrides replicaCount to 2
    get_logger().log_test_case_step("Set user_overrides replicaCount to 2")
    override_values = "replicaCount=2"
    helm_override_keywords.update_helm_override_via_set(override_values, metrics_server_name, chart_name, namespace)

    # Verify the update was applied correctly
    get_logger().log_test_case_step("Verify the update was applied correctly")
    updated_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
    updated_user_overrides = updated_override_show.get_helm_override_show().get_user_overrides()

    validate_str_contains(updated_user_overrides, 'replicaCount: "2"', 'User overrides should contain replicaCount: "2"')
    get_logger().log_info(f"Updated user overrides: {updated_user_overrides}")


@mark.p2
def test_delete_helm_chart_user_overrides_metrics_server(request: FixtureRequest):
    """
    Delete helm chart user overrides for metrics-server application.

    Test Steps:
        - Show initial helm override properties and values
        - Set user_overrides replicaCount to 2
        - Delete the user-overrides configuration
        - Verify the delete was successful

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)

    chart_name = metrics_server_name
    namespace = metrics_server_name

    def teardown():
        get_logger().log_teardown_step("Check and delete helm override if needed")
        current_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
        current_user_overrides = current_override_show.get_helm_override_show().get_user_overrides()
        if current_user_overrides != "None":
            helm_override_keywords.delete_system_helm_override(metrics_server_name, chart_name, namespace)

    request.addfinalizer(teardown)

    # Show initial helm override properties and values
    get_logger().log_test_case_step("Show initial helm override properties and values")
    initial_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
    get_logger().log_info(f"Initial user overrides: {initial_override_show.get_helm_override_show().get_user_overrides()}")

    # Set user_overrides replicaCount to 2
    get_logger().log_test_case_step("Set user_overrides replicaCount to 2")
    override_values = "replicaCount=2"
    helm_override_keywords.update_helm_override_via_set(override_values, metrics_server_name, chart_name, namespace)

    # Delete the user-overrides configuration
    get_logger().log_test_case_step("Delete the user-overrides configuration")
    helm_override_keywords.delete_system_helm_override(metrics_server_name, chart_name, namespace)

    # Verify the delete was successful
    get_logger().log_test_case_step("Verify the delete was successful")
    final_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
    final_user_overrides = final_override_show.get_helm_override_show().get_user_overrides()
    validate_equals(final_user_overrides, "None", "User overrides should be None after deletion")
    get_logger().log_info(f"Final user overrides: {final_user_overrides}")


@mark.p2
def test_modify_helm_chart_attribute_metrics_server(request: FixtureRequest):
    """
    Modify helm chart attribute for metrics-server application.

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
    metrics_server_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)
    helm_attribute_keywords = SystemHelmChartAttributeModifyKeywords(active_ssh_connection)

    chart_name = metrics_server_name
    namespace = metrics_server_name

    def teardown():
        get_logger().log_teardown_step("Check and set enabled attribute to false if needed")
        current_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
        current_attributes = current_override_show.get_helm_override_show().get_attributes()
        if "enabled: true" in str(current_attributes):
            helm_attribute_keywords.helm_chart_attribute_modify_enabled("false", metrics_server_name, chart_name, namespace)

    request.addfinalizer(teardown)

    # Show initial helm override properties and values
    get_logger().log_test_case_step("Show initial helm override properties and values")
    initial_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
    initial_attributes = initial_override_show.get_helm_override_show().get_attributes()
    get_logger().log_info(f"Initial attributes: {initial_attributes}")

    # Set the enabled parameter to true
    get_logger().log_test_case_step("Set the enabled parameter to true")
    helm_attribute_keywords.helm_chart_attribute_modify_enabled("true", metrics_server_name, chart_name, namespace)

    # Verify it was enabled
    get_logger().log_test_case_step("Verify it was enabled")
    enabled_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
    enabled_attributes = enabled_override_show.get_helm_override_show().get_attributes()
    validate_str_contains(str(enabled_attributes), "enabled: true", "Attributes should contain enabled: true")
    get_logger().log_info(f"Enabled attributes: {enabled_attributes}")

    # Set the enabled parameter to false
    get_logger().log_test_case_step("Set the enabled parameter to false")
    helm_attribute_keywords.helm_chart_attribute_modify_enabled("false", metrics_server_name, chart_name, namespace)

    # Verify it was disabled
    get_logger().log_test_case_step("Verify it was disabled")
    disabled_override_show = helm_override_keywords.get_system_helm_override_show(metrics_server_name, chart_name, namespace)
    disabled_attributes = disabled_override_show.get_helm_override_show().get_attributes()
    validate_str_contains(str(disabled_attributes), "enabled: false", "Attributes should contain enabled: false")
    get_logger().log_info(f"Disabled attributes: {disabled_attributes}")
