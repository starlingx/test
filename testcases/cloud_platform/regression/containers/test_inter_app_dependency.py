from _pytest.fixtures import FixtureRequest

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_not_none, validate_str_contains
from keywords.cloud_platform.sm.sm_keywords import SMKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
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
# Test image details
IMAGE_NAME = "adminer"
IMAGE_TAG = "4.8.1-standalone"
IMAGE_ID = "2f7580903a1dd"
MANIFEST_NAME = "container-tests"


def download_docker_images_to_local_registry(ssh_connection: SSHConnection, namespaces: list[str]) -> None:
    """
    Deploys images to the local registry for testcases in this suite.

    Args:
        ssh_connection (SSHConnection): the SSH connection.
        namespaces (list[str]): namespaces names.

    """
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


def cleanup_app(app_name: str, ssh_connection: SSHConnection) -> None:
    """
    Remove/delete applications and files

    Args:
        app_name (str): Application name
        ssh_connection (SSHConnection): ssh connection object

    Returns: None

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


def test_check_apply_dependency_between_apps(request: FixtureRequest):
    """
    Test the apply action from functionality of support inter-application dependencies.
    Apply an application with a dependent app with action apply, should apply automatic this app

    Test Steps:
        Step 1: Copy applications files to active controller
        Step 2: Upload application with dependencies
        Step 3: Apply application with dependencies
        Step 4: Check the required application was applied
    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_name = "apply-dependency-between-apps"
    dependent_app_name = "common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    file_keywords = FileKeywords(ssh_connection)

    # Download docker images
    download_docker_images_to_local_registry(ssh_connection, namespaces=[dependent_app_name, app_name])

    def remove_docker_images():
        kubectl_delete_ns_keyword = KubectlDeleteNamespaceKeywords(ssh_connection)
        kubectl_delete_ns_keyword.cleanup_namespace(dependent_app_name)
        kubectl_delete_ns_keyword.cleanup_namespace(app_name)
        docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)
        docker_sync_keywords.remove_image_from_manifest(IMAGE_NAME, IMAGE_TAG, MANIFEST_NAME)
        crictl_rmi_keywords = CrictlRmiImagesKeywords(ssh_connection)
        crictl_rmi_keywords.crictl_rmi_images(IMAGE_ID)

    request.addfinalizer(remove_docker_images)

    # Step 1: Transfer the dashboard files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_name} and {dependent_app_name} to active controller")
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/containers/inter_application_dependency/{app_name}-{app_version}.tgz"), f"/home/sysadmin/{app_name}-{app_version}.tgz")
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/containers/inter_application_dependency/{dependent_app_name}-{app_version}.tgz"), f"/home/sysadmin/{dependent_app_name}-{app_version}.tgz")
    file_keywords.move_file(f"/home/sysadmin/{app_name}-{app_version}.tgz", f"{OSTREE_DIR}", sudo=True)
    file_keywords.move_file(f"/home/sysadmin/{dependent_app_name}-{app_version}.tgz", f"{OSTREE_DIR}", sudo=True)
    # Update ostree
    OstreeKeywords(ssh_connection).ostree_update()
    # Restart sysinv
    SMKeywords(ssh_connection).restart_sysinv()

    # Step 2: Upload application with dependencies
    start_date = DateKeywords(ssh_connection).get_current_date()
    start_time = DateKeywords(ssh_connection).get_current_time()
    start_date_time = f"{start_date} {start_time}"
    get_logger().log_test_case_step(f"Upload app {app_name}")
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    system_application_upload_input = SystemApplicationUploadInput()
    system_application_upload_input.set_app_name(app_name)
    system_application_upload_input.set_tar_file_path(f"{base_path}{app_name}-{app_version}.tgz")
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    upload_app_status = system_applications.get_application(app_name).get_status()
    validate_equals(upload_app_status, "uploaded", f"{app_name} upload status validation")
    upload_app_status = system_applications.get_application(app_name).get_progress()
    validate_str_contains(upload_app_status, f"this app depends on the following missing apps: {dependent_app_name} (compatible version(s): {app_version})", f"{app_name} progress validation")

    # Step 3: Apply application with dependencies
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        # Update ostree
        OstreeKeywords(ssh_connection).ostree_update()
        # Restart sysinv
        SMKeywords(ssh_connection).restart_sysinv()

    request.addfinalizer(remove_apps)

    # Check for logs in sysinv.log that the dependent application starts uploading
    end_date = DateKeywords(ssh_connection).get_current_date()
    end_time = DateKeywords(ssh_connection).get_current_time()
    end_date_time = f"{end_date} {end_time}"
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Dependent app {dependent_app_name} not found. Uploading new app'")
    validate_not_none(output, "Log appeared at sysinv.log")

    # Step 4: Check the dependent application was applied
    get_logger().log_test_case_step("Step 4: Check the dependent app is applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(dependent_app_name), True, f"The {dependent_app_name} application should be applied on the system")

    # Check for logs in sysinv.log that the dependent application is applied
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Application {dependent_app_name} ({app_version}) apply completed'")
    validate_not_none(output, "Log appeared at sysinv.log")
