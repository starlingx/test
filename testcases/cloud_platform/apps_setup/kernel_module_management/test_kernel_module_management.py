from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.module.kubectl_delete_module_keywords import KubectlDeleteModuleKeywords
from keywords.k8s.module.kubectl_get_module_keywords import KubectlGetModuleKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.dmesg.dmesg_keywords import DmesgKeywords
from keywords.linux.lsmod.lsmod_keywords import LsmodKeywords
from testcases.cloud_platform.regression.containers.test_app_kernel_module_mgmt import (
    APP_NAME,
    KMM_EXPECTED_PODS,
    NAMESPACE,
    cleanup_kernel_module_management_environment,
    delete_module_and_configmap,
    generate_hello_world_configmap,
    generate_hello_world_module_all_nodes,
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
        - Apply module with prebuilt container image
        - Verify module loads
        - Verify dmesg message
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Uploading prebuilt module YAML")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)
    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/prebuilt_mod.yaml.j2"), {"kmm_container_image_registry": kof_config.get_kmm_container_image_registry()}, "prebuilt_mod_1.yaml", "/tmp")

    get_logger().log_test_case_step("Applying prebuilt module")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml("/tmp/prebuilt_mod_1.yaml")

    get_logger().log_test_case_step("Verifying module loads")
    lsmod_keywords = LsmodKeywords(ssh_connection)
    validate_equals_with_retry(lambda: lsmod_keywords.get_lsmod_output().has_module("hello_world_dmesg"), True, "hello_world_dmesg should be loaded", timeout=30, polling_sleep_time=2)

    get_logger().log_test_case_step("Verifying Hello, world! message in dmesg")
    DmesgKeywords(ssh_connection).verify_dmesg_contains("Hello, world!", lines=1)

    get_logger().log_test_case_step("Verifying module resource exists")
    validate_equals(KubectlGetModuleKeywords(ssh_connection).is_module_present("kmm-prebuilt", NAMESPACE), True, "kmm-prebuilt module should exist")


@mark.p2
def test_check_kernel_module_with_prebuilt_image():
    """Check kernel module with prebuilt image status.

    Steps:
        - Verify KMM application is applied
        - Verify prebuilt module is loaded
        - Verify dmesg message
        - Verify module resource exists
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verifying KMM application is applied")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(APP_NAME), True, f"{APP_NAME} should be present")
    app_status = system_applications.get_application(APP_NAME).get_status()
    validate_equals(app_status, SystemApplicationStatusEnum.APPLIED.value, f"{APP_NAME} should be applied")

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module is loaded")
    lsmod_keywords = LsmodKeywords(ssh_connection)
    lsmod_output = lsmod_keywords.get_lsmod_output()
    validate_equals(lsmod_output.has_module("hello_world_dmesg"), True, "hello_world_dmesg kernel module should be loaded")

    get_logger().log_test_case_step("Verifying Hello, world! message in dmesg")
    DmesgKeywords(ssh_connection).verify_dmesg_contains("Hello, world!", lines=1)

    get_logger().log_test_case_step("Verifying KMM module resource exists")
    module_keywords = KubectlGetModuleKeywords(ssh_connection)
    validate_equals(module_keywords.is_module_present("kmm-prebuilt", NAMESPACE), True, "kmm-prebuilt module should exist")


@mark.p2
def test_uninstall_kernel_module_with_prebuilt_image():
    """Uninstall kernel module with prebuilt image and KMM application.

    Steps:
        - Delete prebuilt module resource
        - Verify module unloads
        - Verify Goodbye message in dmesg
        - Cleanup kernel module YAML file
        - Remove and delete KMM application
        - Verify KMM application is removed
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Deleting prebuilt module resource")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    if system_applications.is_in_application_list(APP_NAME):
        KubectlDeleteModuleKeywords(ssh_connection).delete_module("kmm-prebuilt", NAMESPACE)

    get_logger().log_test_case_step("Verifying module unloads")
    lsmod_keywords = LsmodKeywords(ssh_connection)
    validate_equals_with_retry(lambda: lsmod_keywords.get_lsmod_output().has_module("hello_world_dmesg"), False, "hello_world_dmesg should be unloaded", timeout=30, polling_sleep_time=2)

    get_logger().log_test_case_step("Verifying Goodbye, world! message in dmesg")
    DmesgKeywords(ssh_connection).verify_dmesg_contains("Goodbye, world!", lines=1)

    get_logger().log_test_case_step("Cleaning up kernel module YAML file")
    FileKeywords(ssh_connection).delete_file("/tmp/prebuilt_mod_1.yaml")

    get_logger().log_test_case_step("Removing and deleting KMM application")
    cleanup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Verifying KMM application is removed")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(APP_NAME), False, f"{APP_NAME} should be removed")
