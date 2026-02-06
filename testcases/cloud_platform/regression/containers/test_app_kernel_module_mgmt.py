from base64 import b64encode

from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.docker.objects.docker_config import DockerConfig
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_none, validate_not_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.helm.kubectl_get_helm_keywords import KubectlGetHelmKeywords
from keywords.k8s.helm.kubectl_get_helm_release_keywords import KubectlGetHelmReleaseKeywords
from keywords.k8s.kube_cpusets.kube_cpusets_keywords import KubeCpusetsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "kernel-module-management"
NAMESPACE = "kernel-module-management"
CHART_NAME = "kernel-module-management"
CHART_PATH = "/usr/local/share/applications/helm/kernel-module-management-[0-9]*"

# Expected pod name patterns
KMM_EXPECTED_PODS = ["kmm-operator-controller", "kmm-operator-webhook"]


def setup_docker_registry_override(ssh_connection: SSHConnection, docker_config: DockerConfig) -> None:
    """Setup Docker registry credentials as helm override.

    KMM requires Docker registry credentials to pull and push kernel module images.
    This function configures the credentials as a Helm override for the KMM application.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        docker_config (DockerConfig): Docker configuration object.
    """
    get_logger().log_info("Setting up Docker registry credentials")

    # Check if docker.io credentials are configured
    docker_io_registry = docker_config.get_source_registries().get("docker.io")

    # Extract username and password from docker config
    username = docker_io_registry.get_user_name()
    password = docker_io_registry.get_password()

    # Create base64-encoded credentials in format "username:password"
    docker_credentials = b64encode(f"{username}:{password}".encode()).decode()

    # Create Docker config JSON with authentication for docker.io registry
    # Format: {"auths":{"https://index.docker.io/v1/":{"auth":"<base64_credentials>"}}}
    docker_config_json_content = f'{{"auths":{{"https://index.docker.io/v1/":{{"auth":"{docker_credentials}"}}}}}}'

    # Base64-encode the entire Docker config JSON for Kubernetes secret
    docker_config_json = b64encode(docker_config_json_content.encode()).decode()

    # Prepare replacement dictionary for Jinja2 template
    replacement_dict = {"docker_config_json": docker_config_json}

    # Generate YAML file from Jinja2 template with Docker credentials
    yaml_keywords = YamlKeywords(ssh_connection)
    override_file = yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/kmm-app-override.yaml.j2"), replacement_dict, "kmm-app-override.yaml", "/tmp")

    # Apply the helm override to the KMM application
    helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
    helm_override_keywords.update_helm_override(override_file, APP_NAME, CHART_NAME, NAMESPACE)

    # Clean up temporary override file from remote system
    get_logger().log_info("Removing temporary override file")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.delete_file(override_file)


def setup_kernel_module_management_environment(ssh_connection: SSHConnection, docker_config: DockerConfig = None) -> None:
    """Setup kernel module management application.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        docker_config (DockerConfig): Docker configuration object (optional).
    """
    get_logger().log_info(f"Uploading {APP_NAME} application")
    ls_keywords = LsKeywords(ssh_connection)
    actual_chart = ls_keywords.get_first_matching_file(CHART_PATH)
    upload_input = SystemApplicationUploadInput()
    upload_input.set_tar_file_path(actual_chart)
    upload_input.set_app_name(APP_NAME)
    system_app_upload = SystemApplicationUploadKeywords(ssh_connection)
    system_app_upload.system_application_upload(upload_input)

    # KMM requires a docker registry to manage the Kernel Module Images that it builds.
    # KMM will use this registry to pull images from and push images to.
    # This registry may be an external registry, or it may be registry.local:9001
    get_logger().log_info("Configuring Docker registry credentials for KMM")
    setup_docker_registry_override(ssh_connection, docker_config)

    get_logger().log_info(f"Applying {APP_NAME} application")
    system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
    system_app_apply.system_application_apply(APP_NAME)

    # Verify all kernel module management pods are running
    get_logger().log_info("Verifying kernel module management pods are running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=30)


def verify_kernel_module_management_helm_deployed(ssh_connection: SSHConnection) -> None:
    """Verify kernel module management helm chart is deployed.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Verifying kernel module management helm chart is deployed")
    kubectl_helm_release = KubectlGetHelmReleaseKeywords(ssh_connection)
    kubectl_helm_release.validate_helm_release_exists(True, APP_NAME, NAMESPACE, f"{APP_NAME} helm release should exist")


def verify_kernel_module_management_helm_removed(ssh_connection: SSHConnection) -> None:
    """Verify kernel module management helm chart is removed.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Verifying kernel module management helm chart is removed")
    kubectl_helm_release = KubectlGetHelmReleaseKeywords(ssh_connection)
    kubectl_helm_release.validate_helm_release_exists(False, APP_NAME, NAMESPACE, f"{APP_NAME} helm release should not exist")


def verify_kernel_module_management_helmchart_deployed(ssh_connection: SSHConnection) -> None:
    """Verify kernel module management helmchart is deployed.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Verifying kernel module management helmchart is deployed")
    kubectl_helmchart = KubectlGetHelmKeywords(ssh_connection)
    chart = kubectl_helmchart.get_helmchart_by_name(f"{NAMESPACE}-{APP_NAME}", NAMESPACE)
    validate_not_none(chart, f"{APP_NAME} helmchart should exist")


def verify_kernel_module_management_helmchart_removed(ssh_connection: SSHConnection) -> None:
    """Verify that kernel-module-manager entry is removed from HelmChart list.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Verifying kernel-module-manager HelmChart is removed")
    kubectl_helmchart = KubectlGetHelmKeywords(ssh_connection)
    chart = kubectl_helmchart.get_helmchart_by_name(f"{NAMESPACE}-{APP_NAME}", NAMESPACE)
    validate_none(chart, "kernel-module-manager HelmChart should be removed")


def cleanup_kernel_module_management_environment(ssh_connection: SSHConnection) -> None:
    """Clean up kernel module management test resources.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Cleaning up kernel module management test resources")

    system_app_list = SystemApplicationListKeywords(ssh_connection)
    if system_app_list.is_app_present(APP_NAME):
        get_logger().log_info(f"Removing {APP_NAME} application")
        if system_app_list.is_applied_or_applyfailed_or_removefailed(APP_NAME):
            remove_input = SystemApplicationRemoveInput()
            remove_input.set_app_name(APP_NAME)
            system_app_remove = SystemApplicationRemoveKeywords(ssh_connection)
            system_app_remove.system_application_remove(remove_input)

        delete_input = SystemApplicationDeleteInput()
        delete_input.set_app_name(APP_NAME)
        delete_input.set_force_deletion(True)
        system_app_delete = SystemApplicationDeleteKeywords(ssh_connection)
        system_app_delete.get_system_application_delete(delete_input)


@mark.p1
def test_kernel_module_management_upload_apply_delete(request):
    """Test kernel module management application upload, apply and delete.

    Steps:
        - Cleanup kernel module management application
        - Upload kernel module management application
        - Apply the application
        - Verify helm release and helmchart are deployed
        - Reapply the application
        - Verify kernel module management pods are running after reapply
        - Remove and delete the application
        - Verify helm release and helmchart are removed
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Removing kernel module management application if not already removed")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    docker_config = ConfigurationManager.get_docker_config()
    setup_kernel_module_management_environment(ssh_connection, docker_config)

    get_logger().log_test_case_step("Verifying kernel module management helm release is deployed")
    verify_kernel_module_management_helm_deployed(ssh_connection)

    get_logger().log_test_case_step("Verifying kernel module management helmchart is deployed")
    verify_kernel_module_management_helmchart_deployed(ssh_connection)

    get_logger().log_test_case_step(f"Reapplying {APP_NAME} application")
    system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
    system_app_apply.system_application_apply(APP_NAME)

    get_logger().log_test_case_step("Verifying kernel module management pods are running after reapply")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=30)

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Verifying kernel module management helm release is removed")
    verify_kernel_module_management_helm_removed(ssh_connection)

    get_logger().log_test_case_step("Verifying kernel module management helmchart is removed")
    verify_kernel_module_management_helmchart_removed(ssh_connection)


@mark.p1
def test_kernel_module_management_label_override(request):
    """Test applying isApplication label override to kernel module management.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Upload label override YAML file to controller
        - Apply helm override to set isApplication label on KMM pods
        - Reapply application with label override
        - Verify pods are running
        - Verify KMM pods are running on application cores
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    docker_config = ConfigurationManager.get_docker_config()
    setup_kernel_module_management_environment(ssh_connection, docker_config)

    get_logger().log_test_case_step("Applying isApplication label override")
    # Upload the label override YAML file to the controller
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/kmm-app-label-override.yaml"), "/tmp/kmm-app-label-override.yaml", overwrite=False)
    # Apply the helm override to set isApplication label on KMM pods
    helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
    helm_override_keywords.update_helm_override("/tmp/kmm-app-label-override.yaml", APP_NAME, CHART_NAME, NAMESPACE, reuse_values=True)

    get_logger().log_test_case_step("Reapplying application with label override")
    system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
    system_app_apply.system_application_apply(APP_NAME)

    get_logger().log_test_case_step("Verifying pods are running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=30)

    get_logger().log_test_case_step("Verifying KMM pods are running on application cores")
    # Get active controller hostname
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    # Retrieve application cores configured on the host
    cpu_list = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(active_controller)
    app_cores = [cpu.get_log_core() for cpu in cpu_list.get_system_host_cpu_objects(assigned_function="Application")]

    get_logger().log_debug(f"Application cores for {active_controller}: {app_cores}")
    # Get exact pod names from running pods
    all_pods = kubectl_pods.get_pods(namespace=NAMESPACE).get_pods()
    pod_names = [pod.get_name() for pod in all_pods]
    # Get SSH connection to the host where pods are running
    host_ssh = LabConnectionKeywords().get_ssh_for_hostname(active_controller)
    # Verify pods are using application cores via kube-cpusets
    KubeCpusetsKeywords(host_ssh).verify_pods_running_on_specific_cores(pod_names, app_cores)
