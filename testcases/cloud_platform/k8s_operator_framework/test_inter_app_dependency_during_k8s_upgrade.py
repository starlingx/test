"""
Test application dependency during kubernetes upgrade

Prerequisites
- Need to be run on simplex lab with n-1 kubernetes version

What validates
 - "apply" action tests: An app update triggers its dependent app to be automatically deployed. The main app is upgraded from 1.0-1 → 1.1-1 and the dependent app reaches applied status.
 - "error" action tests: When a required dependency is missing, the upgrade phase fails gracefully — the app rolls back to 1.0-1, and the progress message confirms the abort/recovery.
 - Pre-application-update tests: Start upgrade, download images, run pre-app-update, validate, abort. At the end the kubernetes version still the same.
 - Post-application-update tests: Full K8s upgrade cycle (networking, storage, control-plane, kubelet) before running post-app-update and validating. At the end the kubernetes is upgraded.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_equals, validate_not_none, validate_str_contains
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
from keywords.cloud_platform.system.healthquery.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_utils import build_control_plane_batches
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
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
    """Deploys images to the local registry for testcases in this suite.

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
        DockerSyncImagesKeywords(ssh_connection).remove_image_from_manifest(IMAGE_NAME, IMAGE_TAG, MANIFEST_NAME)
        CrictlRmiImagesKeywords(ssh_connection).crictl_rmi_images(IMAGE_ID)

    request.addfinalizer(teardown)


def cleanup_app(app_name: str, ssh_connection: SSHConnection) -> None:
    """Remove/delete applications and files.

    Args:
        app_name (str): Application name.
        ssh_connection (SSHConnection): SSH connection object.
    """
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    if system_app_list.is_app_present(app_name):
        get_logger().log_info(f"Removing {app_name} application")
        system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        if system_app_apply.is_applied_or_failed(app_name):
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(app_name)
            SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)

        system_application_delete_input = SystemApplicationDeleteInput()
        system_application_delete_input.set_app_name(app_name)
        system_application_delete_input.set_force_deletion(True)
        SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)

    FileKeywords(ssh_connection).delete_file(f"{OSTREE_DIR}{app_name}*")


def transfer_app_file_to_active_controller(app_name: str, app_version: str, ssh_connection: SSHConnection) -> None:
    """Transfer app file to active controller.

    Args:
        app_name (str): Application name.
        app_version (str): Application version.
        ssh_connection (SSHConnection): SSH connection object.
    """
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/kubernetes-operator-framework/inter_application_dependency/{app_name}-{app_version}.tgz"), f"/home/sysadmin/{app_name}-{app_version}.tgz")
    file_keywords.move_file(f"/home/sysadmin/{app_name}-{app_version}.tgz", f"{OSTREE_DIR}", sudo=True)


def refresh_ostree_and_sysinv(ssh_connection: SSHConnection) -> None:
    """Refresh OStree and sysinv after apps add/remove.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
    """
    OstreeKeywords(ssh_connection).ostree_update()
    SMKeywords(ssh_connection).restart_sysinv()


def setup_input_object_and_upload(app_name: str, app_version: str, ssh_connection: SSHConnection) -> None:
    """Setup input object and upload app.

    Args:
        app_name (str): Application name.
        app_version (str): Application version.
        ssh_connection (SSHConnection): SSH connection object.
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


def start_kube_upgrade(ssh_connection: SSHConnection) -> str:
    """Start a Kubernetes upgrade and return the target version.

    Args:
        ssh_connection (SSHConnection): SSH connection object.

    Returns:
        str: The target Kubernetes version.
    """
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    SystemHealthQueryKeywords(ssh_connection).is_system_healthy_for_kube_upgrade()

    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_info(f"Starting Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), "upgrade-started", "Upgrade started")

    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "downloaded-images",
        timeout=600,
        failure_states=["downloading-images-failed"],
    )

    return target_version


def abort_and_delete_kube_upgrade(ssh_connection: SSHConnection) -> None:
    """Abort and delete the Kubernetes upgrade.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
    """
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)

    get_logger().log_info("Aborting Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=300)

    get_logger().log_info("Deleting Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()


def run_full_kube_upgrade(ssh_connection: SSHConnection) -> None:
    """Run the full Kubernetes upgrade flow from networking through completion.

    Executes networking, storage, cordon, control-plane, kubelet,
    uncordon, and complete steps. Assumes pre-application-update
    has already been run.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
    """
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)

    # Run networking upgrade
    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-networking",
        timeout=600,
        failure_states=["upgrading-networking-failed"],
    )

    # Run storage upgrade
    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-storage",
        timeout=600,
        failure_states=["upgrading-storage-failed"],
    )

    # Host cordon
    host = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    get_logger().log_test_case_step("Host cordon")
    kube_upgrade_keywords.kube_host_cordon(host)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "cordon-complete",
        timeout=600,
        failure_states=["cordon-failed"],
    )

    # Control-plane and kubelet upgrade
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    available_kube_versions = kube_version_list.get_version_by_state("available")
    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)

    all_versions = available_kube_versions + [active_kube_version]
    batches = build_control_plane_batches(active_kube_version, target_version, all_versions)
    get_logger().log_info(f"Control-plane upgrade batches: {batches}")

    for batch_num, batch in enumerate(batches, 1):
        for version in batch:
            get_logger().log_test_case_step(f"Upgrade control-plane to {version} (batch {batch_num}/{len(batches)})")
            kube_host_upgrade_keywords.kube_host_upgrade_control_plane(host)
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
                "upgraded-first-master",
                timeout=600,
                failure_states=["upgrading-first-master-failed"],
            )

        get_logger().log_test_case_step(f"Upgrade kubelet (batch {batch_num}/{len(batches)})")
        kube_host_upgrade_keywords.kube_host_upgrade_kubelet(host)
        kube_host_upgrade_list_keywords.wait_for_host_upgrade_status(
            host,
            "upgraded-kubelet",
            timeout=600,
            failure_statuses=["upgrading-kubelets-failed"],
        )

    # Host uncordon
    get_logger().log_test_case_step("Host uncordon")
    kube_upgrade_keywords.kube_host_uncordon(host)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "uncordon-complete",
        timeout=600,
        failure_states=["uncordon-failed"],
    )

    # Complete the upgrade
    get_logger().log_test_case_step("Complete Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_complete()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-complete", timeout=300)


@mark.lab_is_simplex
def test_inter_app_dependency_updated_during_kube_pre_application_update(request: FixtureRequest) -> None:
    """Test that inter-app dependency is updated during kube pre-application-update.

    Upload and apply an application with a dependent app (action apply), then start
    a Kubernetes upgrade. After the pre-application-update step, verify the application
    was updated to version 1.1-1 and the dependency app is also applied.
    Finally abort and delete the Kubernetes upgrade.

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Upload and apply the application with dependency action "apply"
        - Start Kubernetes upgrade and download images
        - Run pre-application-update
        - Validate the application was updated to version 1.1-1
        - Check the dependent application is applied
        - Abort and delete the Kubernetes upgrade

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_updated_version = "1.1-1"
    app_name = "apply-dependency-between-apps-pre"
    dependent_app_name = "common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[dependent_app_name, app_name])

    # Transfer app files to active controller
    get_logger().log_test_case_step(f"Copy apps {app_name} and {dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(app_name, app_updated_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload and apply the application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def teardown():
        get_logger().log_teardown_step("Abort and delete kubernetes upgrade if needed")
        try:
            abort_and_delete_kube_upgrade(ssh_connection)
        except Exception:
            get_logger().log_info("No kubernetes upgrade to clean up")
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(teardown)

    # Start Kubernetes upgrade
    get_logger().log_test_case_step("Start Kubernetes upgrade")
    start_kube_upgrade(ssh_connection)

    # Run pre-application-update
    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updated-apps",
        timeout=600,
        failure_states=["pre-updating-apps-failed"],
    )

    # Validate the application was updated to version 1.1-1
    get_logger().log_test_case_step(f"Validate {app_name} was updated to version {app_updated_version}")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    app_object = system_applications.get_application(app_name)
    validate_equals(app_object.get_version(), app_updated_version, f"{app_name} version validation after pre-application-update")
    validate_equals(app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{app_name} status validation after pre-application-update")

    # Check the dependent application was applied after the update
    get_logger().log_test_case_step("Check the dependent app is applied")
    validate_equals(system_applications.is_in_application_list(dependent_app_name), True, f"The {dependent_app_name} application should be applied on the system")
    dependent_app_object = system_applications.get_application(dependent_app_name)
    validate_equals(dependent_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{dependent_app_name} status validation after pre-application-update")

    # Abort and delete the Kubernetes upgrade
    get_logger().log_test_case_step("Abort and delete Kubernetes upgrade")
    abort_and_delete_kube_upgrade(ssh_connection)


@mark.lab_is_simplex
def test_inter_app_dependency_updated_during_kube_post_application_update(request: FixtureRequest) -> None:
    """Test that inter-app dependency is updated during kube post-application-update.

    Upload and apply an application with a dependent app (action apply), then start
    a Kubernetes upgrade. After the post-application-update step, verify the application
    was updated to version 1.1-1 and the dependency app is also applied.
    Finally abort and delete the Kubernetes upgrade.

    Test Steps:
        - Download docker image required by the app
        - Copy applications files to active controller
        - Upload and apply the application with dependency action "apply"
        - Start Kubernetes upgrade and download images
        - Run pre-application-update
        - Run upgrade networking
        - Run upgrade storage
        - Upgrade control-plane and kubelet per host
        - Run upgrade complete
        - Run post-application-update
        - Validate the application was updated to version 1.1-1
        - Check the dependent application is applied
        - Abort and delete the Kubernetes upgrade

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_updated_version = "1.1-1"
    app_name = "apply-dependency-between-apps-post"
    dependent_app_name = "common-dependency-app"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[dependent_app_name, app_name])

    # Transfer app files to active controller
    get_logger().log_test_case_step(f"Copy apps {app_name} and {dependent_app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(app_name, app_updated_version, ssh_connection)
    transfer_app_file_to_active_controller(dependent_app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload and apply the application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def teardown():
        get_logger().log_teardown_step("Abort and delete kubernetes upgrade if needed")
        try:
            abort_and_delete_kube_upgrade(ssh_connection)
        except Exception:
            get_logger().log_info("No kubernetes upgrade to clean up")
        cleanup_app(app_name, ssh_connection)
        cleanup_app(dependent_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(teardown)

    # Start Kubernetes upgrade
    get_logger().log_test_case_step("Start Kubernetes upgrade")
    start_kube_upgrade(ssh_connection)

    # Run pre-application-update
    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updated-apps",
        timeout=600,
        failure_states=["pre-updating-apps-failed"],
    )

    # Run full upgrade flow (networking, storage, cordon, control-plane, kubelet, uncordon, complete)
    run_full_kube_upgrade(ssh_connection)

    # Run post-application-update
    get_logger().log_test_case_step("Run post-application-update")
    kube_upgrade_keywords.kube_post_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "post-updated-apps",
        timeout=600,
        failure_states=["post-updating-apps-failed"],
    )

    # Validate the application was updated to version 1.1-1
    get_logger().log_test_case_step(f"Validate {app_name} was updated to version {app_updated_version}")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    app_object = system_applications.get_application(app_name)
    validate_equals(app_object.get_version(), app_updated_version, f"{app_name} version validation after post-application-update")
    validate_equals(app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{app_name} status validation after post-application-update")

    # Check the dependent application was applied after the update
    get_logger().log_test_case_step("Check the dependent app is applied")
    validate_equals(system_applications.is_in_application_list(dependent_app_name), True, f"The {dependent_app_name} application should be applied on the system")
    dependent_app_object = system_applications.get_application(dependent_app_name)
    validate_equals(dependent_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{dependent_app_name} status validation after post-application-update")

    # Delete the Kubernetes upgrade
    get_logger().log_test_case_step("Delete Kubernetes upgrade")
    KubeUpgradeKeywords(ssh_connection).kube_upgrade_delete()


@mark.lab_is_simplex
def test_inter_app_dependency_error_during_kube_pre_application_update(request: FixtureRequest) -> None:
    """Test that inter-app dependency with error action fails during kube pre-application-update.

    Upload and apply an application with a dependent app (action error), then start
    a Kubernetes upgrade. After the pre-application-update step, verify the upgrade
    fails because the dependent app is not present.
    Finally abort and delete the Kubernetes upgrade.

    Test Steps:
        - Download docker image required by the app
        - Copy application files to active controller
        - Upload and apply the application with dependency action "error"
        - Start Kubernetes upgrade and download images
        - Run pre-application-update
        - Validate the upgrade state is pre-updating-apps-failed
        - Validate the application version remains 1.0-1 and status is applied
        - Validate the progress message indicates update was aborted and recovered
        - Abort and delete the Kubernetes upgrade

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_updated_version = "1.1-1"
    app_name = "error-dependency-between-apps-pre"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer app files to active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(app_name, app_updated_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload and apply the application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def teardown():
        get_logger().log_teardown_step("Abort and delete kubernetes upgrade if needed")
        try:
            abort_and_delete_kube_upgrade(ssh_connection)
        except Exception:
            get_logger().log_info("No kubernetes upgrade to clean up")
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(teardown)

    # Start Kubernetes upgrade
    get_logger().log_test_case_step("Start Kubernetes upgrade")
    start_kube_upgrade(ssh_connection)

    # Run pre-application-update
    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updating-apps-failed",
        timeout=600,
    )

    # Validate the application version remains the original and status is applied
    get_logger().log_test_case_step(f"Validate {app_name} remains at version {app_version} and is applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    app_object = system_applications.get_application(app_name)
    validate_equals(app_object.get_version(), app_version, f"{app_name} version should remain {app_version}")
    validate_equals(app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{app_name} should still be in applied state")
    expected_progress = f"Application update from version {app_version} to version {app_updated_version} aborted. Application recover to version {app_version} completed. Failed to apply dependent apps. Check sysinv logs for details."
    validate_str_contains(app_object.get_progress(), expected_progress, f"{app_name} progress message validation")

    # Abort and delete the Kubernetes upgrade
    get_logger().log_test_case_step("Abort and delete Kubernetes upgrade")
    abort_and_delete_kube_upgrade(ssh_connection)


@mark.lab_is_simplex
def test_inter_app_dependency_error_during_kube_post_application_update(request: FixtureRequest) -> None:
    """Test that inter-app dependency with error action fails during kube post-application-update.

    Upload and apply an application with a dependent app (action error), then start
    a Kubernetes upgrade. After the post-application-update step, verify the upgrade
    fails because the dependent app is not present.
    Finally abort and delete the Kubernetes upgrade.

    Test Steps:
        - Download docker image required by the app
        - Copy application files to active controller
        - Upload and apply the application with dependency action "error"
        - Start Kubernetes upgrade and download images
        - Run pre-application-update
        - Run upgrade networking
        - Run upgrade storage
        - Upgrade control-plane and kubelet per host
        - Run upgrade complete
        - Run post-application-update
        - Validate the upgrade state is post-updating-apps-failed
        - Validate the application version remains 1.0-1 and status is applied
        - Validate the progress message indicates update was aborted and recovered
        - Abort and delete the Kubernetes upgrade

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown
    """
    app_version = "1.0-1"
    app_updated_version = "1.1-1"
    app_name = "error-dependency-between-apps-post"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer app files to active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    transfer_app_file_to_active_controller(app_name, app_updated_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload and apply the application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    def teardown():
        get_logger().log_teardown_step("Abort and delete kubernetes upgrade if needed")
        try:
            abort_and_delete_kube_upgrade(ssh_connection)
        except Exception:
            get_logger().log_info("No kubernetes upgrade to clean up")
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(teardown)

    # Start Kubernetes upgrade
    get_logger().log_test_case_step("Start Kubernetes upgrade")
    start_kube_upgrade(ssh_connection)

    # Run pre-application-update
    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updated-apps",
        timeout=600,
        failure_states=["pre-updating-apps-failed"],
    )

    # Run full upgrade flow (networking, storage, cordon, control-plane, kubelet, uncordon, complete)
    run_full_kube_upgrade(ssh_connection)

    # Run post-application-update
    get_logger().log_test_case_step("Run post-application-update")
    kube_upgrade_keywords.kube_post_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "post-updating-apps-failed",
        timeout=600,
    )

    # Validate the application version remains the original and status is applied
    get_logger().log_test_case_step(f"Validate {app_name} remains at version {app_version} and is applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    app_object = system_applications.get_application(app_name)
    validate_equals(app_object.get_version(), app_version, f"{app_name} version should remain {app_version}")
    validate_equals(app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{app_name} should still be in applied state")
    expected_progress = f"Application update from version {app_version} to version {app_updated_version} aborted. Application recover to version {app_version} completed. Failed to apply dependent apps. Check sysinv logs for details."
    validate_str_contains(app_object.get_progress(), expected_progress, f"{app_name} progress message validation")

    # Abort and delete the Kubernetes upgrade
    get_logger().log_test_case_step("Abort and delete Kubernetes upgrade")
    abort_and_delete_kube_upgrade(ssh_connection)
