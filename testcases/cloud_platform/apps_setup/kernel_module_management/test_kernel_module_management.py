from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.docker.images.docker_remove_images_keywords import DockerRemoveImagesKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.module.kubectl_delete_module_keywords import KubectlDeleteModuleKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from testcases.cloud_platform.regression.k8s_operator_framework.test_app_kernel_module_mgmt import (
    APP_NAME,
    KMM_EXPECTED_PODS,
    NAMESPACE,
    build_and_push_kmod_image,
    cleanup_kernel_module_management_environment,
    delete_module_and_configmap,
    generate_hello_world_configmap,
    generate_hello_world_module_all_nodes,
    generate_prebuilt_module,
    setup_kernel_module_management_environment,
    verify_dmesg_message,
    verify_kmm_module_exists,
    verify_module_loaded,
    verify_module_unloaded,
    wait_for_worker_pods_completed,
)


@mark.p2
def test_install_kernel_module_management_with_hello_world():
    """Install hello world kernel module on all nodes.

    Steps:
        - Setup KMM environment (upload, configure, apply)
        - Upload and apply hello world kernel module
        - Verify worker pods complete
        - Verify kernel module is loaded on all hosts
        - Verify dmesg contains Hello, world! message on all hosts
        - Verify KMM module resource exists
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Uploading hello world kernel module YAML files")
    module_name = "kmm-hello-world"
    generate_hello_world_configmap(ssh_connection, module_name)
    generate_hello_world_module_all_nodes(ssh_connection, module_name)

    get_logger().log_test_case_step("Applying hello world kernel module")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Verifying worker pods complete")
    wait_for_worker_pods_completed(ssh_connection)

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module is loaded and dmesg message on all hosts")
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = [host.get_host_name() for host in system_host_list.get_system_host_list().get_hosts()]

    for host in all_hosts:
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host)
        verify_module_loaded(host_ssh)
        verify_dmesg_message(host_ssh, "Hello, world!")

    get_logger().log_test_case_step("Verifying KMM module resource exists")
    verify_kmm_module_exists(ssh_connection, module_name)


@mark.p2
def test_check_kernel_module_management_and_hello_world_module():
    """Check KMM application and hello world module status.

    Steps:
        - Verify KMM application is applied
        - Verify KMM pods are running
        - Verify hello world kernel module is loaded on all hosts
        - Verify KMM module resource exists
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verifying KMM application is applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(APP_NAME), True, f"{APP_NAME} should be present")
    app_status = system_applications.get_application(APP_NAME).get_status()
    validate_equals(app_status, SystemApplicationStatusEnum.APPLIED.value, f"{APP_NAME} should be applied")

    get_logger().log_test_case_step("Verifying KMM pods are running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=30)

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module is loaded on all hosts")
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = [host.get_host_name() for host in system_host_list.get_system_host_list().get_hosts()]

    get_logger().log_test_case_step("Verifying KMM module resource exists")
    verify_kmm_module_exists(ssh_connection, "kmm-hello-world")
    for host in all_hosts:
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host)
        verify_module_loaded(host_ssh)


@mark.p2
def test_uninstall_kernel_module_management_and_hello_world_module():
    """Uninstall hello world module and KMM application.

    Steps:
        - Delete hello world kernel module resource
        - Delete hello world configmap resource
        - Verify kernel modules are unloaded from all hosts
        - Cleanup kernel module YAML files
        - Remove and delete KMM application
        - Verify KMM application is removed
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verifying KMM application is present")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(APP_NAME), True, f"{APP_NAME} should be uploaded/applied")

    get_logger().log_test_case_step("Deleting hello world kernel module and configmap resources")
    module_name = "kmm-hello-world"
    delete_module_and_configmap(ssh_connection, module_name, ignore_not_found=True)

    get_logger().log_test_case_step("Verifying kernel modules are unloaded and Goodbye message on all hosts")
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = [host.get_host_name() for host in system_host_list.get_system_host_list().get_hosts()]

    for host in all_hosts:
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host)
        verify_module_unloaded(host_ssh)
        verify_dmesg_message(host_ssh, "Goodbye, world!")

    get_logger().log_test_case_step("Cleaning up kernel module YAML files")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.delete_file("/tmp/hello_world_cm.yaml")
    file_keywords.delete_file("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Removing and deleting KMM application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p2
def test_install_kernel_module_with_prebuilt_image():
    """Install KMM and setup kernel module with prebuilt image.

    Steps:
        - Setup KMM environment
        - Build and push kmod image to registry
        - Generate and apply module with prebuilt container image
        - Verify module resource exists
        - Verify module loads on all hosts
        - Verify dmesg message on all hosts
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Building and pushing kmod image to registry")
    build_and_push_kmod_image(ssh_connection)

    get_logger().log_test_case_step("Generating and applying prebuilt module YAML")
    generate_prebuilt_module(ssh_connection)
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml("/tmp/prebuilt_mod.yaml")

    get_logger().log_test_case_step("Verifying module resource exists")
    verify_kmm_module_exists(ssh_connection, "kmm-prebuilt")

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module is loaded and dmesg message on all hosts")
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = [host.get_host_name() for host in system_host_list.get_system_host_list().get_hosts()]

    for host in all_hosts:
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host)
        verify_module_loaded(host_ssh)
        verify_dmesg_message(host_ssh, "Hello, world!")


@mark.p2
def test_check_kernel_module_with_prebuilt_image():
    """Check kernel module with prebuilt image status.

    Steps:
        - Verify KMM application is applied
        - Verify KMM pods are running
        - Verify prebuilt module is loaded on all hosts
        - Verify dmesg message on all hosts
        - Verify module resource exists
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verifying KMM application is applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(APP_NAME), True, f"{APP_NAME} should be present")
    app_status = system_applications.get_application(APP_NAME).get_status()
    validate_equals(app_status, SystemApplicationStatusEnum.APPLIED.value, f"{APP_NAME} should be applied")

    get_logger().log_test_case_step("Verifying KMM pods are running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=30)

    get_logger().log_test_case_step("Verifying KMM module resource exists")
    verify_kmm_module_exists(ssh_connection, "kmm-prebuilt")

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module is loaded and dmesg message on all hosts")
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = [host.get_host_name() for host in system_host_list.get_system_host_list().get_hosts()]

    for host in all_hosts:
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host)
        verify_module_loaded(host_ssh)
        verify_dmesg_message(host_ssh, "Hello, world!")


@mark.p2
def test_uninstall_kernel_module_with_prebuilt_image():
    """Uninstall kernel module with prebuilt image and KMM application.

    Steps:
        - Delete prebuilt module resource
        - Verify module unloads on all hosts
        - Verify Goodbye message in dmesg on all hosts
        - Cleanup kernel module YAML file
        - Remove and delete KMM application
        - Verify KMM application is removed
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Deleting prebuilt module resource")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    if system_applications.is_in_application_list(APP_NAME):
        KubectlDeleteModuleKeywords(ssh_connection).delete_module("kmm-prebuilt", NAMESPACE)

    get_logger().log_test_case_step("Verifying module unloads and Goodbye message on all hosts")
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = [host.get_host_name() for host in system_host_list.get_system_host_list().get_hosts()]

    for host in all_hosts:
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host)
        verify_module_unloaded(host_ssh)
        verify_dmesg_message(host_ssh, "Goodbye, world!")

    get_logger().log_test_case_step("Cleaning up kernel module YAML file")
    FileKeywords(ssh_connection).delete_file("/tmp/prebuilt_mod.yaml")

    get_logger().log_test_case_step("Removing prebuilt kmod docker images")
    kof_config = ConfigurationManager.get_kof_config()
    registry = kof_config.get_kmm_container_image_registry()
    docker_remove = DockerRemoveImagesKeywords(ssh_connection)
    for tag in ["amd64-hw", "rt-amd64-hw"]:
        docker_remove.remove_docker_image(f"{registry}:{tag}")

    get_logger().log_test_case_step("Removing and deleting KMM application")
    cleanup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Verifying KMM application is removed")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(APP_NAME), False, f"{APP_NAME} should be removed")
