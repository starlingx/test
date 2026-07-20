"""Shared helper functions for k8s_operator_framework test suites."""

from pytest import FixtureRequest

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.sm.sm_keywords import SMKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
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
from keywords.ostree.ostree_keywords import OstreeKeywords

OSTREE_DIR = "/ostree/1/usr/local/share/applications/helm/"


def download_docker_images_to_local_registry(request: FixtureRequest, ssh_connection: SSHConnection, namespaces: list[str]) -> None:
    """Deploy images to the local registry for testcases in this suite.

    Args:
        request (FixtureRequest): pytest fixture.
        ssh_connection (SSHConnection): the SSH connection.
        namespaces (list[str]): namespaces names.
    """
    IMAGE_NAME = "adminer"
    IMAGE_TAG = "4.8.1-standalone"
    IMAGE_ID = "2f7580903a1dd"
    MANIFEST_NAME = "container-tests"

    kubectl_create_ns_keyword = KubectlCreateNamespacesKeywords(ssh_connection)
    local_registry = ConfigurationManager.get_docker_config().get_local_registry()

    for namespace in namespaces:
        kubectl_create_ns_keyword.create_namespaces(namespace)
        KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, "local-secret", namespace=namespace)

    docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)
    docker_sync_keywords.sync_image_from_manifest(IMAGE_NAME, IMAGE_TAG, MANIFEST_NAME)

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
    """Remove/delete applications and files.

    Args:
        app_name (str): Application name.
        ssh_connection (SSHConnection): ssh connection object.
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


def transfer_app_file_to_active_controller(app_name: str, app_version: str, ssh_connection: SSHConnection, resource_subdir: str = "on-demand-reapply") -> None:
    """Transfer app file to active controller.

    Args:
        app_name (str): Application name.
        app_version (str): Application version.
        ssh_connection (SSHConnection): ssh connection object.
        resource_subdir (str): Subdirectory under resources/cloud_platform/kubernetes-operator-framework/.
    """
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/kubernetes-operator-framework/{resource_subdir}/{app_name}-{app_version}.tgz"), f"/home/sysadmin/{app_name}-{app_version}.tgz")
    file_keywords.move_file(f"/home/sysadmin/{app_name}-{app_version}.tgz", f"{OSTREE_DIR}", sudo=True)


def refresh_ostree_and_sysinv(ssh_connection: SSHConnection) -> None:
    """Refresh OStree and sysinv after apps add/remove.

    Args:
        ssh_connection (SSHConnection): ssh connection object.
    """
    OstreeKeywords(ssh_connection).ostree_update()
    SMKeywords(ssh_connection).restart_sysinv()


def setup_input_object_and_upload(app_name: str, app_version: str, ssh_connection: SSHConnection) -> None:
    """Setup input object and upload app.

    Args:
        app_name (str): Application name.
        app_version (str): Application version.
        ssh_connection (SSHConnection): ssh connection object.
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
