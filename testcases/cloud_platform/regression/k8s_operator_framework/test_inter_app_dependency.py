import pytest
from pytest import FixtureRequest

from config.configuration_manager import ConfigurationManager
from framework.exceptions.validation_failure_error import ValidationFailureError
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_not_none, validate_str_contains
from keywords.cloud_platform.sm.sm_keywords import SMKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_update_input import SystemApplicationUpdateInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_update_keywords import SystemApplicationUpdateKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.crictl.crictl_pull_image_keywords import CrictlPullImageKeywords
from keywords.crictl.crictl_rmi_images_keywords import CrictlRmiImagesKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.linux.date.date_keywords import DateKeywords
from keywords.ostree.ostree_keywords import OstreeKeywords

OSTREE_DIR = "/ostree/1/usr/local/share/applications/helm/"


def download_docker_images_to_local_registry(request: FixtureRequest, ssh_connection: SSHConnection, namespaces: list[str]) -> None:
    """
    Deploys images to the local registry for testcases in this suite.

    Args:
        request (FixtureRequest): pytest fixture.
        ssh_connection (SSHConnection): the SSH connection.
        namespaces (list[str]): namespaces names.
    """
    # Test image details
    IMAGE_NAME = "adminer"
    IMAGE_TAG = "4.8.1-standalone"
    IMAGE_ID = "2f7580903a1dd"
    MANIFEST_NAME = "container-tests"

    kubectl_create_ns_keyword = KubectlCreateNamespacesKeywords(ssh_connection)
    local_registry = ConfigurationManager.get_docker_config().get_local_registry()

    for namespace in namespaces:
        # Create namespace
        kubectl_create_ns_keyword.create_namespaces(namespace)
        # Create secret for local registry
        KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, "local-secret", namespace=namespace)

    # Sync image from manifest to local registry
    docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)
    docker_sync_keywords.sync_image_from_manifest(IMAGE_NAME, IMAGE_TAG, MANIFEST_NAME)

    # Pull to crictl
    local_registry_user = local_registry.get_user_name()
    local_registry_pwd = local_registry.get_password()
    local_registry_url = local_registry.get_registry_url()
    crictl_pull_keywords = CrictlPullImageKeywords(ssh_connection)
    crictl_pull_keywords.crictl_pull_image(f"{local_registry_user}:{local_registry_pwd}", f"{local_registry_url}/{IMAGE_NAME}:{IMAGE_TAG}")

    def teardown():
        kubectl_delete_ns_keyword = KubectlDeleteNamespaceKeywords(ssh_connection)
        for namespace in namespaces:
            kubectl_delete_ns_keyword.cleanup_namespace(namespace)
        docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)
        docker_sync_keywords.remove_image_from_manifest(IMAGE_NAME, IMAGE_TAG, MANIFEST_NAME)
        crictl_rmi_keywords = CrictlRmiImagesKeywords(ssh_connection)
        crictl_rmi_keywords.crictl_rmi_images(IMAGE_ID)

    request.addfinalizer(teardown)


def cleanup_app(app_name: str, ssh_connection: SSHConnection) -> None:
    """
    Remove/delete applications and files

    Args:
        app_name (str): Application name
        ssh_connection (SSHConnection): ssh connection object
    """
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    if system_app_list.is_app_present(app_name):
        get_logger().log_info(f"Removing {app_name} application")
        system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        if system_app_apply.is_applied_or_failed(app_name):
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(app_name)
            system_app_remove = SystemApplicationRemoveKeywords(ssh_connection)
            system_app_remove.system_application_remove(system_application_remove_input)

        system_application_delete_input = SystemApplicationDeleteInput()
        system_application_delete_input.set_app_name(app_name)
        system_application_delete_input.set_force_deletion(True)
        system_app_delete = SystemApplicationDeleteKeywords(ssh_connection)
        system_app_delete.get_system_application_delete(system_application_delete_input)

    file_keywords = FileKeywords(ssh_connection)
    file_keywords.delete_file(f"{OSTREE_DIR}{app_name}*")


def transfer_app_file_to_active_controller(app_name: str, app_version: str, ssh_connection: SSHConnection) -> None:
    """
    Transfer app file to active controller

    Args:
        app_name (str): Application name
        app_version (str): Application version
        ssh_connection (SSHConnection): ssh connection object
    """
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/kubernetes-operator-framework/inter_application_dependency/{app_name}-{app_version}.tgz"), f"/home/sysadmin/{app_name}-{app_version}.tgz")
    file_keywords.move_file(f"/home/sysadmin/{app_name}-{app_version}.tgz", f"{OSTREE_DIR}", sudo=True)


def refresh_ostree_and_sysinv(ssh_connection: SSHConnection) -> None:
    """
    Refresh OStree and sysinv after apps add/remove

    Args:
        ssh_connection (SSHConnection): ssh connection object
    """
    OstreeKeywords(ssh_connection).ostree_update()
    SMKeywords(ssh_connection).restart_sysinv()


def setup_input_object_and_upload(app_name: str, app_version: str, ssh_connection: SSHConnection) -> None:
    """
    Setup input object and upload app

    Args:
        app_name (str): Application name
        app_version (str): Application version
        ssh_connection (SSHConnection): ssh connection object
    """
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    system_application_upload_input = SystemApplicationUploadInput()
    system_application_upload_input.set_app_name(app_name)
    system_application_upload_input.set_tar_file_path(f"{base_path}{app_name}-{app_version}.tgz")
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    upload_app_status = system_applications.get_application(app_name).get_status()
    validate_equals(upload_app_status, "uploaded", f"{app_name} upload status validation")


def validate_app_progress_message(app_name: str, app_progress_msg: str, ssh_connection: SSHConnection) -> None:
    """
    Validate application progress message

    Args:
        app_name (str): Application name
        app_progress_msg (str): Application progress message
        ssh_connection (SSHConnection): ssh connection object
    """
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    upload_app_status = system_applications.get_application(app_name).get_progress()
    validate_str_contains(upload_app_status, app_progress_msg, f"{app_name} progress validation")


def test_check_apply_dependency_between_apps(request: FixtureRequest):
    """
    Test the apply behavior from functionality of support inter-application dependencies.
    Apply an application with a dependent app with action apply, should apply automatic this app

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application with dependency action "apply" can be uploaded and a missing app message appears in "system application-list"
        - Validate that the application with dependency action "apply" can be applied
        - Check the dependent application was uploaded and applied
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "apply-dependency-between-apps"
    dependent_app_name = "common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[dependent_app_name, app_name])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name} and {dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)
    validate_app_progress_message(app_name, f"this app depends on the following missing apps: {dependent_app_name} (compatible version(s): 1.0-\d+)", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the dependent application starts uploading
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Dependent app {dependent_app_name} not found. Uploading new app'")
    validate_not_none(output, "Log appeared at sysinv.log")

    # Check the dependent application was applied
    get_logger().log_test_case_step("Check the dependent app is applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(dependent_app_name), True, f"The {dependent_app_name} application should be applied on the system")

    # Check for logs in sysinv.log that the dependent application is applied
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Application {dependent_app_name} ({app_version}) apply completed'")
    validate_not_none(output, "Log appeared at sysinv.log")


def test_check_ignore_dependency_between_apps(request: FixtureRequest):
    """
    Test the ignore behavior from functionality of support inter-application dependencies.
    Apply an application with a dependent app with action ignore, should apply the app and do nothing with the dependent app

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application with dependency action "ignore" can be uploaded
        - Validate that the application with dependency action "ignore" can be applied
        - Check the dependent application is not present in the system
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "ignore-dependency-between-apps"
    dependent_app_name = "common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[dependent_app_name, app_name])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name} and {dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the application has a dependent app
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'App {app_name} has dependent apps:(?=.*{dependent_app_name})(?=.*1.0-\d+)(?=.*ignore).*'")
    validate_not_none(output, "Log appeared at sysinv.log")

    # Check the dependent application is not present in the system
    get_logger().log_test_case_step("Check the dependent app is not present")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(dependent_app_name), False, f"The {dependent_app_name} application should not be uploaded or applied on the system")


def test_check_warn_dependency_between_apps(request: FixtureRequest):
    """
    Test the warn behavior from functionality of support inter-application dependencies.
    Apply an application with a dependent app with action warn, should apply the app and do nothing with the dependent app

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application with dependency action "warn" can be uploaded and a missing app message appears in "system application-list"
        - Validate that the application with dependency action "warn" can be applied
        - Check the dependent application is not present in the system
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "warn-dependency-between-apps"
    dependent_app_name = "common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[dependent_app_name, app_name])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name} and {dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)
    validate_app_progress_message(app_name, f"this app depends on the following missing apps: {dependent_app_name} (compatible version(s): 1.0-\d+)", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the application has a dependent app
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'App {app_name} has dependent apps:(?=.*{dependent_app_name})(?=.*1.0-\d+)(?=.*warn).*'")
    validate_not_none(output, "Log appeared at sysinv.log")

    # Check the dependent application is not present in the system
    get_logger().log_test_case_step("Check the dependent app is not present")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(dependent_app_name), False, f"The {dependent_app_name} application should not be uploaded or applied on the system")


def test_check_default_dependency_between_apps(request: FixtureRequest):
    """
    Test the default behavior from functionality of support inter-application dependencies.
    Upload an application with a dependent app without any action should fail

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application with dependency but without action should fail to upload
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "default-dependency-between-apps"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name}")
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    system_application_upload_input = SystemApplicationUploadInput()
    system_application_upload_input.set_app_name(app_name)
    system_application_upload_input.set_tar_file_path(f"{base_path}{app_name}-{app_version}.tgz")
    with pytest.raises(AssertionError):
        SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the application failed to upload
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"Extracting tarfile for /usr/local/share/applications/helm/{app_name}-{app_version}.tgz failed: metadata validation failed. Invalid metadata.yaml: action expected values are ['warn', 'ignore', 'error', 'apply'].")
    validate_not_none(output, "Log appeared at sysinv.log")


def test_error_apply_dependency_between_apps(request: FixtureRequest):
    """
    Test the error behavior from functionality of support inter-application dependencies.
    Apply an application with a dependent app with action error, should fail apply and after the dependent app is applied it should be ok to apply

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application with dependency action "error" can be uploaded
        - Validate that the application with dependency action "error" can not be applied without dependent app
        - Upload and apply the dependent app
        - Validate that the application with dependency action "error" can be applied with dependent app applied
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "error-dependency-between-apps"
    dependent_app_name = "common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[dependent_app_name, app_name])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name} and {dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)
    validate_app_progress_message(app_name, f"this app depends on the following missing apps: {dependent_app_name} (compatible version(s): 1.0-\d+)", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    with pytest.raises(ValidationFailureError):
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_str_contains(system_applications.get_application(app_name).get_progress(), f"This app depends on the following missing apps: {dependent_app_name} (compatible version(s): 1.0-\d+)", f"{app_name} progress validation. Please install them and try to apply again.")
    validate_equals(system_applications.get_application(app_name).get_status(), SystemApplicationStatusEnum.APPLY_FAILED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the application failed to apply
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'App {app_name} has dependent apps:(?=.*{dependent_app_name})(?=.*1.0-\d+)(?=.*error).*'")
    validate_not_none(output, "Log appeared at sysinv.log")

    # Upload the dependent application
    get_logger().log_test_case_step(f"Upload app {dependent_app_name}")
    setup_input_object_and_upload(dependent_app_name, app_version, ssh_connection)

    # Apply the dependent application
    get_logger().log_test_case_step(f"Apply app {dependent_app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(dependent_app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), dependent_app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")


def test_check_multiple_app_apply_dependency_between_apps(request: FixtureRequest):
    """
    Test the apply behavior from functionality of support inter-application dependencies.
    Apply an application with a multiple dependent apps with action apply, should apply automatic the apps

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application with multiple dependency action "apply" can be uploaded and a missing apps message appears in "system application-list"
        - Validate that the application with multiple dependency action "apply" can be applied
        - Check the dependent applications were uploaded and applied
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "multiple-app-dependency"
    dependent_app_name = "common-dependency-app"
    other_dependent_app_name = "other-common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[other_dependent_app_name, dependent_app_name, app_name])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name}, {dependent_app_name} and {other_dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(other_dependent_app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)
    validate_app_progress_message(app_name, f"this app depends on the following missing apps: {dependent_app_name} (compatible version(s): 1.0-\d+), {other_dependent_app_name} (compatible version(s): 1.0-\d+)", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        cleanup_app(other_dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the dependent applications starts uploading
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Dependent app {dependent_app_name} not found. Uploading new app'")
    validate_not_none(output, "Log appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Dependent app {other_dependent_app_name} not found. Uploading new app'")
    validate_not_none(output, "Log appeared at sysinv.log")

    # Check the multiple dependent applications were applied
    get_logger().log_test_case_step("Check the dependent app is applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(dependent_app_name), True, f"The {dependent_app_name} application should be applied on the system")
    validate_equals(system_applications.is_in_application_list(other_dependent_app_name), True, f"The {other_dependent_app_name} application should be applied on the system")

    # Check for logs in sysinv.log that the dependent applications were applied
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Application {dependent_app_name} ({app_version}) apply completed'")
    validate_not_none(output, "Log appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Application {other_dependent_app_name} ({app_version}) apply completed'")
    validate_not_none(output, "Log appeared at sysinv.log")


def test_check_multiple_app_error_dependency_between_apps(request: FixtureRequest):
    """
    Test the error behavior from functionality of support inter-application dependencies.
    Apply an application with a multiple dependent apps, one with action error and the other one with action apply, should fail to apply the app

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application with multiple dependency action can be uploaded and a missing apps message appears in "system application-list"
        - Validate that the application with multiple dependency action can not be applied, due to missing app with action error
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "multiple-app-dependency-error"
    dependent_app_name = "common-dependency-app"
    other_dependent_app_name = "other-common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[other_dependent_app_name, dependent_app_name, app_name])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name}, {dependent_app_name} and {other_dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(other_dependent_app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)
    validate_app_progress_message(app_name, f"this app depends on the following missing apps: {dependent_app_name} (compatible version(s): 1.0-\d+), {other_dependent_app_name} (compatible version(s): 1.0-\d+)", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    with pytest.raises(ValidationFailureError):
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_str_contains(system_applications.get_application(app_name).get_progress(), f"This app depends on the following missing apps: {dependent_app_name} (compatible version(s): 1.0-\d+)", f"{app_name} progress validation. Please install them and try to apply again.")
    validate_equals(system_applications.get_application(app_name).get_status(), SystemApplicationStatusEnum.APPLY_FAILED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        cleanup_app(other_dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)


def test_check_exact_version_apply_dependency_between_apps(request: FixtureRequest):
    """
    Test the apply behavior from functionality of support inter-application dependencies.
    Apply an application with a dependent app with action apply expecting an exact version of the app, should apply automatic this app

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application with dependency action "apply" can be uploaded and a missing app message appears in "system application-list"
        - Validate that the application with dependency action "apply" can be applied
        - Check the dependent application was uploaded and applied
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "apply-exact-dependency-between-apps"
    dependent_app_version = "1.1-1"
    dependent_app_name = "common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[dependent_app_name, app_name])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name} and {dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, dependent_app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)
    validate_app_progress_message(app_name, f"this app depends on the following missing apps: {dependent_app_name} (compatible version(s): {dependent_app_version})", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the dependent application starts uploading
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Dependent app {dependent_app_name} not found. Uploading new app'")
    validate_not_none(output, "Log appeared at sysinv.log")

    # Check the dependent application was applied
    get_logger().log_test_case_step("Check the dependent app is applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(dependent_app_name), True, f"The {dependent_app_name} application should be applied on the system")

    # Check for logs in sysinv.log that the dependent application is applied
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Application {dependent_app_name} ({dependent_app_version}) apply completed'")
    validate_not_none(output, "Log appeared at sysinv.log")


def test_check_exact_version_non_existent_apply_dependency_between_apps(request: FixtureRequest):
    """
    Test the apply behavior from functionality of support inter-application dependencies.
    Apply an application with a dependent app with action apply expecting a non exist version of the app, should fail apply the app

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application with dependency action "apply" can be uploaded and a missing app message appears in "system application-list"
        - Validate that the application with dependency action "apply" and a non-exist version fail to be applied because missing app with compatible version
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "apply-dependency-between-apps-with-incorrect-version"
    non_exist_app_version = "2.1-1"
    dependent_app_name = "common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[dependent_app_name, app_name])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name} and {dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Step 2: Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)
    validate_app_progress_message(app_name, f"this app depends on the following missing apps: {dependent_app_name} (compatible version(s): {non_exist_app_version})", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    with pytest.raises(ValidationFailureError):
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_str_contains(system_applications.get_application(app_name).get_progress(), "Failed to apply dependent apps. Check sysinv logs for details.", f"{app_name} progress validation. Please install them and try to apply again.")
    validate_equals(system_applications.get_application(app_name).get_status(), SystemApplicationStatusEnum.APPLY_FAILED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the dependent application was not found
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'No application bundle with name {dependent_app_name} and version {non_exist_app_version} found.'")
    validate_not_none(output, "Log appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f'\'Failed to upload or apply dependent applications. Upload failed: [{{"name": "{dependent_app_name}", "version": "{non_exist_app_version}"}}]\'')
    validate_not_none(output, "Log appeared at sysinv.log")


def test_check_app_dependency_manual_app_update_scenario(request: FixtureRequest):
    """
    Test the apply behavior with app manual update dependencies from functionality of support inter-application dependencies.
    Upload and apply app A with no dependencies. Manual update app A to a new version containing dependency of app B action apply

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application A can be uploaded and applied without any dependencies message
        - Validate that the application A can be updated to a new version that contains dependency of application B with action "apply"
        - Check the application A was updated and applied
        - Check the dependent application B was uploaded and applied
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_version_update = "1.0-3"
    app_name_a = "app-1"
    app_name_b = "app-2"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name_a, app_name_b])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name_a} versions ({app_version} and {app_version_update}) and {app_name_b} to active controller")
    transfer_app_file_to_active_controller(app_name_a, app_version, ssh_connection)
    transfer_app_file_to_active_controller(app_name_a, app_version_update, ssh_connection)
    transfer_app_file_to_active_controller(app_name_b, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name_a}")
    setup_input_object_and_upload(app_name_a, app_version, ssh_connection)

    # Apply application
    get_logger().log_test_case_step(f"Apply app {app_name_a}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name_a)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name_a, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    # Update application with dependencies on new version
    get_logger().log_test_case_step(f"Update {app_name_a} with new tarball containing dependency of {app_name_b}")
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(app_name_a)
    system_application_update_input.set_tar_file_path(f"{base_path}{app_name_a}-{app_version_update}.tgz")
    SystemApplicationUpdateKeywords(ssh_connection).system_application_update(system_application_update_input)

    def remove_apps():
        cleanup_app(app_name_a, ssh_connection)
        cleanup_app(app_name_b, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the dependent application starts uploading
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Dependent app {app_name_b} not found. Uploading new app'")
    validate_not_none(output, "Log appeared at sysinv.log")

    # Check the dependent application and updated application were applied
    get_logger().log_test_case_step("Check the apps were applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(app_name_a), True, f"The {app_name_a} application should be applied on the system")
    validate_app_progress_message(app_name_a, f"Application update from version {app_version} to version {app_version_update} completed.", ssh_connection)
    validate_equals(system_applications.is_in_application_list(app_name_b), True, f"The {app_name_b} application should be applied on the system")

    # Check for logs in sysinv.log that the dependent application is applied
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Application {app_name_b} ({app_version}) apply completed'")
    validate_not_none(output, "Log appeared at sysinv.log")


def test_check_dependency_in_three_apps_scenario(request: FixtureRequest):
    """
    Test the apply behavior with three apps dependencies from functionality of support inter-application dependencies.

    App C has dependency of App B with action apply
    App B has dependency of App A with action apply
    App A has no dependency

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application C with dependency of application B with action "apply" can be uploaded and a missing app message appears in "system application-list"
        - Validate that the application B with dependency of application A with action "apply" can be uploaded and a missing app message appears in "system application-list"
        - Validate that the application C can be applied
        - Check the dependent application A was uploaded and applied
        - Check the dependent application B was applied
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name_a = "app-a"
    app_name_b = "app-b"
    app_name_c = "app-c"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name_a, app_name_b, app_name_c])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name_a}, {app_name_b} and {app_name_c} to active controller")
    transfer_app_file_to_active_controller(app_name_a, app_version, ssh_connection)
    transfer_app_file_to_active_controller(app_name_b, app_version, ssh_connection)
    transfer_app_file_to_active_controller(app_name_c, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload applications with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name_c}")
    setup_input_object_and_upload(app_name_c, app_version, ssh_connection)
    validate_app_progress_message(app_name_c, f"this app depends on the following missing apps: {app_name_b} (compatible version(s): 1.0-\d+)", ssh_connection)

    get_logger().log_test_case_step(f"Upload app {app_name_b}")
    setup_input_object_and_upload(app_name_b, app_version, ssh_connection)
    validate_app_progress_message(app_name_b, f"this app depends on the following missing apps: {app_name_a} (compatible version(s): 1.0-\d+)", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name_c}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name_c)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name_c, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name_a, ssh_connection)
        cleanup_app(app_name_b, ssh_connection)
        cleanup_app(app_name_c, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check all apps were applied
    get_logger().log_test_case_step("Check all apps are applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(app_name_b), True, f"The {app_name_b} application should be applied on the system")
    validate_equals(system_applications.is_in_application_list(app_name_a), True, f"The {app_name_a} application should be applied on the system")

    # Check for logs in sysinv.log
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Application {app_name_c} ({app_version}) upload completed. This app has dependent apps missing: {app_name_b} (compatible version(s): {app_version}). Please install the missing apps first before starting the apply process.'")
    validate_not_none(output, "Log appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Application {app_name_b} ({app_version}) upload completed. This app has dependent apps missing: {app_name_a} (compatible version(s): 1.0-\d+). Please install the missing apps first before starting the apply process.'")
    validate_not_none(output, "Log appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Dependent app {app_name_b} is already uploaded. Skipping upload'")
    validate_not_none(output, "Log appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Dependent app {app_name_a} not found. Uploading new app'")
    validate_not_none(output, "Log appeared at sysinv.log")


def test_check_direct_circular_dependency_between_apps(request: FixtureRequest):
    """
    Test the apply behavior with apps with direct circular dependencies from functionality of support inter-application dependencies.

    App A has dependency of App B with action apply
    App B has dependency of App A with action apply

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application B with dependency of application A with action "apply" can be uploaded and a missing app message appears in "system application-list"
        - Validate that the application B fail to be applied due to circular dependency detected
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version_a = "1.0-2"
    app_name_a = "app-circular-direct-1"
    app_version_b = "1.0-1"
    app_name_b = "app-circular-direct-2"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name_a, app_name_b])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name_a} and {app_name_b} to active controller")
    transfer_app_file_to_active_controller(app_name_a, app_version_a, ssh_connection)
    transfer_app_file_to_active_controller(app_name_b, app_version_b, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name_b}")
    setup_input_object_and_upload(app_name_b, app_version_b, ssh_connection)
    validate_app_progress_message(app_name_b, f"this app depends on the following missing apps: {app_name_a} (compatible version(s): {app_version_a})", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name_b}")
    with pytest.raises(ValidationFailureError):
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name_b)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_str_contains(system_applications.get_application(app_name_b).get_progress(), "Circular dependency detected.", f"{app_name_b} progress validation. Please install them and try to apply again.")
    validate_equals(system_applications.get_application(app_name_b).get_status(), SystemApplicationStatusEnum.APPLY_FAILED.value, "Application status validation")

    # Verifies the app is not present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(app_name_a), False, f"The {app_name_a} application should not be already uploaded/applied on the system")

    def remove_apps():
        cleanup_app(app_name_a, ssh_connection)
        cleanup_app(app_name_b, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the application failed to apply
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"Deployment of application {app_name_b} ({app_version_b}) failed: Circular dependency detected.")
    validate_not_none(output, "Log appeared at sysinv.log")


def test_check_indirect_circular_dependency_between_apps(request: FixtureRequest):
    """
    Test the apply behavior with three apps dependencies from functionality of support inter-application dependencies.

    App C has dependency of App A with action apply
    App B has dependency of App A with action apply
    App A has dependency of App B with action apply

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Validate that the application C with dependency of application A with action "apply" can be uploaded and a missing app message appears in "system application-list"
        - Validate that the application C fail to be applied due to circular dependency detected

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name_a = "app-circular-indirect-1"
    app_name_b = "app-circular-indirect-2"
    app_name_c = "app-circular-indirect-3"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name_a, app_name_b, app_name_c])

    # Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name_a}, {app_name_b} and {app_name_c} to active controller")
    transfer_app_file_to_active_controller(app_name_a, app_version, ssh_connection)
    transfer_app_file_to_active_controller(app_name_b, app_version, ssh_connection)
    transfer_app_file_to_active_controller(app_name_c, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application with dependencies
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Upload app {app_name_c}")
    setup_input_object_and_upload(app_name_c, app_version, ssh_connection)
    validate_app_progress_message(app_name_c, f"this app depends on the following missing apps: {app_name_a} (compatible version(s): 1.0-2)", ssh_connection)

    # Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name_c}")
    with pytest.raises(ValidationFailureError):
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name_c)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_str_contains(system_applications.get_application(app_name_c).get_progress(), "Circular dependency detected.", f"{app_name_c} progress validation. Please install them and try to apply again.")
    validate_equals(system_applications.get_application(app_name_c).get_status(), SystemApplicationStatusEnum.APPLY_FAILED.value, "Application status validation")

    # Verifies the dependents apps are not present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(app_name_a), False, f"The {app_name_a} application should not be already uploaded/applied on the system")
    validate_equals(system_applications.is_in_application_list(app_name_b), False, f"The {app_name_b} application should not be already uploaded/applied on the system")

    def remove_apps():
        cleanup_app(app_name_a, ssh_connection)
        cleanup_app(app_name_b, ssh_connection)
        cleanup_app(app_name_c, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the application failed to apply
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    file_keywords = FileKeywords(ssh_connection)
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"Deployment of application {app_name_b} ({app_version}) failed: Circular dependency detected.")
    validate_not_none(output, "Log appeared at sysinv.log")


def test_apps_dependency_class_support_critical(request: FixtureRequest):
    """
    This test validates support of field class "critical" on application metadata. Classes allow the Application
    Framework to figure out in which order automatic operations, such as reapplies and updates, should be performed.

    Test Steps:
        - Download docker image required by the app
        - Copy application file to active controller
        - Validate that the application can be uploaded
        - Validate that the application with class critical can be applied successfully
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "app-critical-class"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer the dashboard file to the active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    # Apply application
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)


def test_apps_dependency_class_support_discovery(request: FixtureRequest):
    """
    This test validates support of field class "discovery" on application metadata. Classes allow the Application
    Framework to figure out in which order automatic operations, such as reapplies and updates, should be performed.

    Test Steps:
        - Download docker image required by the app
        - Copy application file to active controller
        - Validate that the application can be uploaded
        - Validate that the application with class discovery can be applied successfully
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "app-discovery-class"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer the dashboard file to the active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    # Apply application
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)


def test_apps_dependency_class_support_optional(request: FixtureRequest):
    """
    This test validates support of field class "optional" on application metadata. Classes allow the Application
    Framework to figure out in which order automatic operations, such as reapplies and updates, should be performed.

    Test Steps:
        - Download docker image required by the app
        - Copy application file to active controller
        - Validate that the application can be uploaded
        - Validate that the application with class optional can be applied successfully
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "app-optional-class"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer the dashboard file to the active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    # Apply application
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)


def test_apps_dependency_class_support_reporting(request: FixtureRequest):
    """
    This test validates support of field class "reporting" on application metadata. Classes allow the Application
    Framework to figure out in which order automatic operations, such as reapplies and updates, should be performed.

    Test Steps:
        - Download docker image required by the app
        - Copy application file to active controller
        - Validate that the application can be uploaded
        - Validate that the application with class reporting can be applied successfully
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "app-reporting-class"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer the dashboard file to the active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    # Apply application
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)


def test_apps_dependency_class_support_storage(request: FixtureRequest):
    """
    This test validates support of field class "storage" on application metadata. Classes allow the Application
    Framework to figure out in which order automatic operations, such as reapplies and updates, should be performed.

    Test Steps:
        - Download docker image required by the app
        - Copy application file to active controller
        - Validate that the application can be uploaded
        - Validate that the application with class storage can be applied successfully
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "app-storage-class"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer the dashboard file to the active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    # Apply application
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)
