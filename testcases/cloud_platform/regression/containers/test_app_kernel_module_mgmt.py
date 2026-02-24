from base64 import b64encode
from random import choice

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_none, validate_not_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.configmap.kubectl_delete_configmap_keywords import KubectlDeleteConfigmapKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.helm.kubectl_get_helm_keywords import KubectlGetHelmKeywords
from keywords.k8s.helm.kubectl_get_helm_release_keywords import KubectlGetHelmReleaseKeywords
from keywords.k8s.kube_cpusets.kube_cpusets_keywords import KubeCpusetsKeywords
from keywords.k8s.module.kubectl_delete_module_keywords import KubectlDeleteModuleKeywords
from keywords.k8s.module.kubectl_get_module_keywords import KubectlGetModuleKeywords
from keywords.k8s.module.kubectl_patch_module_keywords import KubectlPatchModuleKeywords
from keywords.k8s.node.kubectl_label_node_keywords import KubectlLabelNodeKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.dmesg.dmesg_keywords import DmesgKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.linux.ls.ls_keywords import LsKeywords
from keywords.linux.lsmod.lsmod_keywords import LsmodKeywords

APP_NAME = "kernel-module-management"
NAMESPACE = "kernel-module-management"
CHART_NAME = "kernel-module-management"
CHART_PATH = "/usr/local/share/applications/helm/kernel-module-management-[0-9]*"

# Expected pod name patterns
KMM_EXPECTED_PODS = ["kmm-operator-controller", "kmm-operator-webhook"]


# ConfigMap generation functions
def generate_hello_world_configmap(ssh_connection: SSHConnection, module_name: str = "kmm-hello-world") -> None:
    """Generate hello world ConfigMap with KMM builder image from config.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name for the module and configmap.

    """
    get_logger().log_info(f"Generating ConfigMap for module: {module_name}")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)
    replacement_dict = {"kmm_builder_image": kof_config.get_kmm_builder_image(), "module_name": module_name}
    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/hello_world_cm.yaml.j2"), replacement_dict, "hello_world_cm.yaml", "/tmp")


def generate_multiple_hello_world_configmaps(ssh_connection: SSHConnection, module_names: list[str]) -> None:
    """Generate multiple hello world ConfigMaps using single template.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_names (list[str]): List of module names for generating configmaps.

    """
    get_logger().log_info(f"Generating multiple ConfigMaps for modules: {module_names}")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)
    replacement_dict = {"kmm_builder_image": kof_config.get_kmm_builder_image(), "module_name_1": module_names[0], "module_name_2": module_names[1]}

    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/multiple_hello_world_cm.yaml.j2"), replacement_dict, "hello_world_cm.yaml", "/tmp")


# Module generation functions
def generate_hello_world_module_all_nodes(ssh_connection: SSHConnection, module_name: str = "kmm-hello-world") -> None:
    """Generate hello world Module for all nodes with KMM container image from config.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name for the module.

    """
    get_logger().log_info(f"Generating Module for all nodes: {module_name}")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)

    replacement_dict = {
        "kmm_container_image_registry": kof_config.get_kmm_container_image_registry(),
        "module_name": module_name,
    }

    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/hello_world_mod_all_nodes.yaml.j2"), replacement_dict, "hello_world_mod.yaml", "/tmp")


def generate_hello_world_module_with_target_host(ssh_connection: SSHConnection, module_name: str = "kmm-hello-world", target_host: str = None) -> None:
    """Generate hello world Module with specific target host.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name for the module.
        target_host (str): Hostname to pin the module to via node selector.

    """
    get_logger().log_info(f"Generating Module for target host {target_host}: {module_name}")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)

    replacement_dict = {
        "kmm_container_image_registry": kof_config.get_kmm_container_image_registry(),
        "module_name": module_name,
    }

    replacement_dict["target_host"] = target_host

    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/hello_world_mod.yaml.j2"), replacement_dict, "hello_world_mod.yaml", "/tmp")


def generate_hello_world_module_with_selector(ssh_connection: SSHConnection, module_name: str = "kmm-hello-world") -> None:
    """Generate hello world Module with test-hardware selector.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name for the module.

    """
    get_logger().log_info(f"Generating Module with hardware selector: {module_name}")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)

    replacement_dict = {
        "kmm_container_image_registry": kof_config.get_kmm_container_image_registry(),
        "module_name": module_name,
    }

    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/hello_world_mod_selector.yaml.j2"), replacement_dict, "hello_world_mod_selector.yaml", "/tmp")


def generate_multiple_hello_world_modules(ssh_connection: SSHConnection, module_names: list[str]) -> None:
    """Generate multiple hello world Modules using single template.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_names (list[str]): List of module names for generating modules.

    """
    get_logger().log_info(f"Generating multiple hello world modules: {module_names}")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)

    replacement_dict = {"image_directory": kof_config.get_kmm_container_image_registry(), "module_name_1": module_names[0], "module_name_2": module_names[1]}

    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/multiple_hello_world_mod.yaml.j2"), replacement_dict, "hello_world_mod.yaml", "/tmp")


def generate_prebuilt_module(ssh_connection: SSHConnection, module_name: str = "kmm-prebuilt") -> None:
    """Generate prebuilt module YAML with KMM container image from config.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name for the module.

    """
    get_logger().log_info(f"Generating prebuilt module: {module_name}")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)
    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/prebuilt_mod.yaml.j2"), {"kmm_container_image_registry": kof_config.get_kmm_container_image_registry()}, "prebuilt_mod.yaml", "/tmp")


def generate_versioned_module(ssh_connection: SSHConnection, module_name: str, version: str, target_host: str, output_filename: str = "hello_world_mod_versioned.yaml") -> None:
    """Generate versioned module YAML for ordered upgrade testing.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name for the module.
        version (str): Version string for the module.
        target_host (str): Hostname to target with node selector.
        output_filename (str): Output YAML filename.

    """
    get_logger().log_info(f"Generating versioned module {module_name} v{version} for {target_host}")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)
    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/hello_world_mod_versioned.yaml.j2"), {"module_name": module_name, "kmm_container_image_registry": kof_config.get_kmm_container_image_registry(), "version": version, "target_host": target_host}, output_filename, "/tmp")


# Utility functions
def get_kmm_worker_pod_names(ssh_connection: SSHConnection, module_names: list[str], host_list: list[str] = None) -> list[str]:
    """Generate KMM worker pod names for given modules and hosts.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_names (list[str]): List of module names.
        host_list (list[str], optional): List of host names. If None, uses all hosts in the system.

    Returns:
        list[str]: List of worker pod names in format 'kmm-worker-{host}-{module}'.

    """
    get_logger().log_info(f"Generating worker pod names for modules: {module_names}")

    # Use provided host list or get all hosts from system
    if host_list is None:
        system_host_list = SystemHostListKeywords(ssh_connection)
        host_list = [host.get_host_name() for host in system_host_list.get_system_host_list().get_hosts()]
        get_logger().log_debug(f"Using all system hosts: {host_list}")
    else:
        get_logger().log_debug(f"Using provided host list: {host_list}")

    # Generate pod names for all host-module combinations
    pod_names = [f"kmm-worker-{host}-{module}" for host in host_list for module in module_names]

    get_logger().log_debug(f"Generated {len(pod_names)} worker pod names: {pod_names}")
    return pod_names


def wait_for_worker_pods_completed(ssh_connection: SSHConnection, pod_names: list[str] = None, timeout: int = 180) -> None:
    """Wait for KMM worker pods to complete.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        pod_names (list[str]): List of pod names to wait for. Defaults to ["kmm-worker"].
        timeout (int): Timeout in seconds.

    """
    if pod_names is None:
        pod_names = ["kmm-worker"]

    get_logger().log_info(f"Waiting for worker pods to complete: {pod_names}")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Completed", pod_names=pod_names, namespace=NAMESPACE, poll_interval=0, timeout=timeout)


def delete_module_and_configmap(ssh_connection: SSHConnection, module_name: str, ignore_not_found: bool = False) -> None:
    """Delete KMM module and its configmap.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name of the module to delete.
        ignore_not_found (bool): If True, ignore resources that don't exist.

    """
    get_logger().log_info(f"Deleting module and configmap: {module_name}")
    KubectlDeleteModuleKeywords(ssh_connection).delete_module(module_name, NAMESPACE, ignore_not_found=ignore_not_found)
    KubectlDeleteConfigmapKeywords(ssh_connection).delete_configmap(f"{module_name}-cm", NAMESPACE, ignore_not_found=ignore_not_found)


def cleanup_test_resources(ssh_connection: SSHConnection, module_name: str) -> None:
    """Clean up test resources including module, configmap, and YAML files.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name of the module to clean up.

    """
    get_logger().log_info(f"Cleaning up test resources for module: {module_name}")

    # Check if KMM app is still present before trying to delete module resources
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    if system_app_list.is_app_present(APP_NAME):
        delete_module_and_configmap(ssh_connection, module_name, ignore_not_found=True)
    else:
        get_logger().log_info(f"KMM application not present, skipping module/configmap deletion for {module_name}")

    # Clean up generated YAML files
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.delete_file("/tmp/hello_world_cm.yaml")
    file_keywords.delete_file("/tmp/hello_world_mod.yaml")


def cleanup_test_resources_with_labels(ssh_connection: SSHConnection, module_name: str) -> None:
    """Clean up test resources including node labels.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name of the module to clean up.

    """
    get_logger().log_info(f"Cleaning up test resources with labels for module: {module_name}")

    # Check if KMM app is still present before trying to delete module resources
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    if system_app_list.is_app_present(APP_NAME):
        # Clean up module and configmap resources only if KMM app exists
        delete_module_and_configmap(ssh_connection, module_name, ignore_not_found=True)

    # Remove test-hardware labels from all nodes
    label_keywords = KubectlLabelNodeKeywords(ssh_connection)
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = system_host_list.get_system_host_list().get_hosts()
    for host in all_hosts:
        label_keywords.remove_label(host.get_host_name(), "test-hardware")

    # Clean up selector-specific files
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.delete_file("/tmp/hello_world_mod_selector.yaml")


# KMM environment management functions
def verify_module_loaded(ssh_connection: SSHConnection, module_name: str = "hello_world_dmesg") -> None:
    """Verify kernel module is loaded via lsmod.

    Args:
        ssh_connection (SSHConnection): SSH connection to check module on.
        module_name (str): Name of the kernel module to check.

    """
    get_logger().log_info(f"Verifying module {module_name} is loaded")
    lsmod_keywords = LsmodKeywords(ssh_connection)
    validate_equals_with_retry(lambda: lsmod_keywords.get_lsmod_output().has_module(module_name), True, f"{module_name} should be loaded", timeout=120, polling_sleep_time=2)


def verify_module_unloaded(ssh_connection: SSHConnection, module_name: str = "hello_world_dmesg") -> None:
    """Verify kernel module is unloaded via lsmod.

    Args:
        ssh_connection (SSHConnection): SSH connection to check module on.
        module_name (str): Name of the kernel module to check.

    """
    get_logger().log_info(f"Verifying module {module_name} is unloaded")
    lsmod_keywords = LsmodKeywords(ssh_connection)
    validate_equals_with_retry(lambda: lsmod_keywords.get_lsmod_output().has_module(module_name), False, f"{module_name} should be unloaded", timeout=30, polling_sleep_time=2)


def verify_dmesg_message(ssh_connection: SSHConnection, message: str) -> None:
    """Verify message appears in dmesg output.

    Args:
        ssh_connection (SSHConnection): SSH connection to check dmesg on.
        message (str): Message to verify in dmesg.

    """
    get_logger().log_info(f"Verifying dmesg contains: {message}")
    dmesg_keywords = DmesgKeywords(ssh_connection)
    dmesg_keywords.verify_dmesg_contains(message, lines=1)


def verify_kmm_module_exists(ssh_connection: SSHConnection, module_name: str) -> None:
    """Verify KMM module resource exists.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name of the KMM module to check.

    """
    get_logger().log_info(f"Verifying KMM module resource exists: {module_name}")
    module_keywords = KubectlGetModuleKeywords(ssh_connection)
    validate_equals(module_keywords.is_module_present(module_name, NAMESPACE), True, f"{module_name} module should exist")


def patch_module_version(ssh_connection: SSHConnection, module_name: str, version: str) -> None:
    """Patch module to upgrade to new version.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        module_name (str): Name of the module to patch.
        version (str): New version string.

    """
    get_logger().log_info(f"Patching module {module_name} to version {version}")
    kof_config = ConfigurationManager.get_kof_config()
    yaml_keywords = YamlKeywords(ssh_connection)

    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/module_upgrade_patch.yaml.j2"), {"version": version, "kmm_container_image_registry": kof_config.get_kmm_container_image_registry()}, "module_upgrade_patch.yaml", "/tmp", copy_to_remote=False)
    patch_data = yaml_keywords.load_yaml(f"{ConfigurationManager.get_logger_config().get_test_case_resources_log_location()}/module_upgrade_patch.yaml")

    patch_keywords = KubectlPatchModuleKeywords(ssh_connection)
    patch_keywords.patch_module(module_name, NAMESPACE, patch_data, patch_type="merge")


def setup_docker_registry_override(ssh_connection: SSHConnection) -> None:
    """Setup Docker registry credentials as helm override.

    KMM requires Docker registry credentials to pull and push kernel module images.
    This function configures the credentials as a Helm override for the KMM application.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Setting up Docker registry credentials for KMM")

    # Extract username and password from keyring
    keyring_keywords = KeyringKeywords(ssh_connection)
    username = "sysinv"
    password = keyring_keywords.get_keyring("sysinv", "services")

    # Create base64-encoded credentials in format "username:password"
    docker_credentials = b64encode(f"{username}:{password}".encode()).decode()

    # Create Docker config JSON with authentication for registry.local:9001
    docker_config_json_content = f'{{"auths":{{"https://registry.local:9001":{{"auth":"{docker_credentials}"}}}}}}'

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


def setup_kernel_module_management_environment(ssh_connection: SSHConnection) -> None:
    """Setup kernel module management application.

    Uploads, configures, and applies the KMM application with Docker registry credentials.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info(f"Setting up {APP_NAME} environment")

    # Upload KMM application chart
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
    setup_docker_registry_override(ssh_connection)

    # Apply the KMM application
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


def verify_pods_on_application_cores(ssh_connection: SSHConnection, namespace: str) -> None:
    """Verify pods are running on application cores across all hosts.

    This function verifies that pods in the specified namespace are scheduled
    and running on the application cores of each host in the system.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        namespace (str): Kubernetes namespace containing the pods.
    """
    # Get all pods in the namespace
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    all_pods = kubectl_pods.get_pods(namespace=namespace)

    # Get all hosts in the system
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = [host.get_host_name() for host in system_host_list.get_system_host_list().get_hosts()]

    # Verify pods on each host are using application cores
    for host in all_hosts:
        # Get pods running on this host
        pods = all_pods.get_pods_on_node(host)
        pod_names = [pod.get_name() for pod in pods]

        # Skip hosts with no pods
        if not pod_names:
            get_logger().log_info(f"No pods on host {host}, skipping")
            continue

        get_logger().log_info(f"Checking pods on host {host}: {pod_names}")

        # Get application cores configured on this host
        cpu_list = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(host)
        app_cores = [cpu.get_log_core() for cpu in cpu_list.get_system_host_cpu_objects(assigned_function="Application")]

        # Get SSH connection to this host
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host)

        # Verify pods are running on application cores
        KubeCpusetsKeywords(host_ssh).verify_pods_running_on_specific_cores(pod_names, app_cores)


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
    setup_kernel_module_management_environment(ssh_connection)

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
    setup_kernel_module_management_environment(ssh_connection)

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
    verify_pods_on_application_cores(ssh_connection, NAMESPACE)

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p1
def test_kernel_module_and_config_map_load_and_build(request):
    """Test kernel module hello world build and load.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Upload to lab hello world kernel module ConfigMap and Module YAML files
        - Apply hello world kernel module resources
        - Wait for worker pod to complete module build and load
        - Verify KMM Module resource exists
        - Verify module load message appears in dmesg
        - Verify hello_world_dmesg kernel module is loaded via lsmod
        - Delete Module resource to trigger unload
        - Delete ConfigMap resource
        - Verify module unload message appears in dmesg
        - Verify kernel module is no longer loaded
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    module_name = "kmm-test-build"

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Cleaning up test resources")
        cleanup_test_resources(ssh_connection, module_name)
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Uploading hello world kernel module YAML files")
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    generate_hello_world_configmap(ssh_connection, module_name)
    generate_hello_world_module_with_target_host(ssh_connection, module_name, active_controller)

    get_logger().log_test_case_step("Applying hello world kernel module")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Verifying worker pod completes")
    wait_for_worker_pods_completed(ssh_connection)

    get_logger().log_test_case_step("Verifying KMM module resource exists")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step("Verifying module load message in dmesg")
    verify_dmesg_message(ssh_connection, "Hello, world!")

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module is loaded")
    verify_module_loaded(ssh_connection)

    get_logger().log_test_case_step("Deleting kernel module and configmap resources")
    delete_module_and_configmap(ssh_connection, module_name)

    get_logger().log_test_case_step("Verifying kernel module is no longer loaded")
    verify_module_unloaded(ssh_connection)

    get_logger().log_test_case_step("Verifying module unload message in dmesg")
    verify_dmesg_message(ssh_connection, "Goodbye, world!")

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p1
def test_kernel_module_hello_world_controller_reboot(request):
    """Test kernel module hello world persistence after controller reboot.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Generate hello world kernel module ConfigMap and Module YAML files
        - Apply hello world kernel module resources
        - Wait for worker pod to complete module build and load
        - Verify hello_world_dmesg kernel module is loaded via lsmod
        - Verify Hello, world! message appears in dmesg output
        - Verify KMM Module resource exists via kubectl get modules
        - Reboot active controller and wait for host to come back online
        - Verify KMM application is in applied state after reboot
        - Verify KMM pods are running after reboot
        - Verify hello_world_dmesg kernel module is still loaded after reboot
        - Verify Hello, world! message still appears in dmesg after reboot
        - Delete Module and ConfigMap resources in teardown
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    module_name = "kmm-test-reboot"

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Cleaning up test resources")
        cleanup_test_resources(ssh_connection, module_name)
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Getting active controller hostname")
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Uploading hello world kernel module YAML files")
    generate_hello_world_configmap(ssh_connection, module_name)
    generate_hello_world_module_with_target_host(ssh_connection, module_name, active_controller)

    get_logger().log_test_case_step("Applying hello world kernel module")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Verifying worker pod completes")
    wait_for_worker_pods_completed(ssh_connection)

    get_logger().log_test_case_step("Running lsmod | grep hello to verify module is loaded")
    verify_module_loaded(ssh_connection)

    get_logger().log_test_case_step("Running dmesg and checking for Hello, world! message")
    verify_dmesg_message(ssh_connection, "Hello, world!")

    get_logger().log_test_case_step("Checking modules via kubectl get modules.kmm.sigs.x-k8s.io")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step(f"Rebooting controller {active_controller}")
    system_host_list = SystemHostListKeywords(ssh_connection)
    pre_uptime = system_host_list.get_uptime(active_controller)
    ssh_connection.send_as_sudo("reboot -f")
    system_host_reboot = SystemHostRebootKeywords(ssh_connection)
    reboot_success = system_host_reboot.wait_for_force_reboot(active_controller, pre_uptime)
    validate_equals(reboot_success, True, "Controller should reboot successfully")

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after reboot")
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    system_app_list.validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Verifying KMM pods are running after reboot")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=120)

    get_logger().log_test_case_step(f"Verifying hello_world_dmesg kernel module is still loaded on {active_controller} after reboot")
    target_host_ssh = LabConnectionKeywords().get_ssh_for_hostname(active_controller)
    verify_module_loaded(target_host_ssh)

    get_logger().log_test_case_step(f"Verifying Hello, world! message still in dmesg on {active_controller} after reboot")
    verify_dmesg_message(target_host_ssh, "Hello, world!")

    get_logger().log_test_case_step("Verifying KMM module resource still exists after reboot")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step("Deleting kernel module and configmap resources")
    delete_module_and_configmap(ssh_connection, module_name)

    get_logger().log_test_case_step("Verifying kernel module is no longer loaded")
    verify_module_unloaded(target_host_ssh)

    get_logger().log_test_case_step("Verifying module unload message in dmesg")
    verify_dmesg_message(target_host_ssh, "Goodbye, world!")

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p1
@mark.lab_has_standby_controller
def test_kernel_module_hello_world_swact(request):
    """Test kernel module hello world persistence after controller swact.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Upload hello world kernel module ConfigMap and Module YAML files
        - Apply hello world kernel module resources
        - Wait for worker pod to complete module build and load
        - Verify hello_world_dmesg kernel module is loaded via lsmod
        - Verify Hello, world! message appears in dmesg output
        - Verify KMM Module resource exists via kubectl get modules
        - Perform controller swact
        - Verify hello_world_dmesg kernel module is still loaded after swact
        - Verify KMM Module resource still exists after swact
        - Perform controller swact back to original active controller
        - Delete Module and ConfigMap resources
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    module_name = "kmm-test-swact"

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Cleaning up test resources")
        cleanup_test_resources(ssh_connection, module_name)
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Getting active controller hostname")
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Uploading hello world kernel module YAML files")
    generate_hello_world_configmap(ssh_connection, module_name)
    generate_hello_world_module_with_target_host(ssh_connection, module_name, active_controller)

    get_logger().log_test_case_step("Applying hello world kernel module")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Verifying worker pod completes")
    wait_for_worker_pods_completed(ssh_connection)

    get_logger().log_test_case_step(f"Running lsmod on {active_controller} to verify module is loaded")
    target_host_ssh = LabConnectionKeywords().get_ssh_for_hostname(active_controller)
    verify_module_loaded(target_host_ssh)

    get_logger().log_test_case_step(f"Running dmesg on {active_controller} and checking for Hello, world! message")
    verify_dmesg_message(target_host_ssh, "Hello, world!")

    get_logger().log_test_case_step("Checking modules via kubectl get modules.kmm.sigs.x-k8s.io")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step("Performing controller swact")
    system_host_swact = SystemHostSwactKeywords(ssh_connection)
    swact_success = system_host_swact.host_swact()
    validate_equals(swact_success, True, "Controller swact should complete successfully")

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after swact")
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    system_app_list.validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Verifying KMM pods are running after swact")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=120)

    get_logger().log_test_case_step(f"Verifying hello_world_dmesg kernel module is still loaded on {active_controller} after swact")
    target_host_ssh = LabConnectionKeywords().get_ssh_for_hostname(active_controller)
    verify_module_loaded(target_host_ssh)

    get_logger().log_test_case_step("Verifying KMM module resource still exists after swact")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step("Deleting kernel module and configmap resources")
    delete_module_and_configmap(ssh_connection, module_name)

    get_logger().log_test_case_step("Verifying kernel module is no longer loaded")
    verify_module_unloaded(target_host_ssh)

    get_logger().log_test_case_step("Verifying module unload message in dmesg")
    verify_dmesg_message(target_host_ssh, "Goodbye, world!")

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Performing controller swact back to original active controller")
    swact_back_success = system_host_swact.host_swact()
    validate_equals(swact_back_success, True, "Controller swact back should complete successfully")


@mark.p1
@mark.lab_has_standby_controller
def test_kernel_module_hello_world_lock_unlock(request):
    """Test kernel module hello world persistence after controller lock/unlock.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Select non-active host for module deployment
        - Upload hello world kernel module ConfigMap and Module YAML files
        - Apply hello world kernel module resources on selected host
        - Wait for worker pod to complete module build and load
        - Verify hello_world_dmesg kernel module is loaded on target host via lsmod
        - Verify Hello, world! message appears in dmesg output on target host
        - Verify KMM Module resource exists via kubectl get modules
        - Lock and unlock the host where module is deployed
        - Verify KMM app is in applied state and all the KMM pods are running
        - Verify hello_world_dmesg kernel module is still loaded on target host after unlock
        - Verify KMM Module resource still exists after unlock
        - Delete Module and ConfigMap resources
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    module_name = "kmm-test-lock"

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Cleaning up test resources")
        cleanup_test_resources(ssh_connection, module_name)
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Getting random non-active host")
    system_host_list = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list.get_active_controller().get_host_name()
    all_hosts = system_host_list.get_system_host_list().get_hosts()
    non_active_hosts = [host.get_host_name() for host in all_hosts if host.get_host_name() != active_controller]

    target_host = choice(non_active_hosts)
    get_logger().log_info(f"Selected random target host: {target_host}")

    get_logger().log_test_case_step(f"Uploading hello world kernel module YAML files for {target_host}")
    generate_hello_world_configmap(ssh_connection, module_name)
    generate_hello_world_module_with_target_host(ssh_connection, module_name, target_host)

    get_logger().log_test_case_step("Applying hello world kernel module")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Verifying worker pod completes")
    wait_for_worker_pods_completed(ssh_connection)

    get_logger().log_test_case_step(f"Running lsmod on {target_host} to verify module is loaded")
    target_host_ssh = LabConnectionKeywords().get_ssh_for_hostname(target_host)
    verify_module_loaded(target_host_ssh)

    get_logger().log_test_case_step(f"Running dmesg on {target_host} and checking for Hello, world! message")
    verify_dmesg_message(target_host_ssh, "Hello, world!")

    get_logger().log_test_case_step("Checking modules via kubectl get modules.kmm.sigs.x-k8s.io")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step(f"Locking controller {target_host}")
    system_host_lock = SystemHostLockKeywords(ssh_connection)
    lock_success = system_host_lock.lock_host(target_host)
    validate_equals(lock_success, True, "Controller should lock successfully")

    get_logger().log_test_case_step(f"Unlocking controller {target_host}")
    unlock_success = system_host_lock.unlock_host(target_host)
    validate_equals(unlock_success, True, "Controller should unlock successfully")

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after unlock")
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    system_app_list.validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Verifying KMM pods are running after unlock")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=120)

    get_logger().log_test_case_step(f"Verifying hello_world_dmesg kernel module is still loaded on {target_host} after unlock")
    verify_module_loaded(target_host_ssh)

    get_logger().log_test_case_step("Verifying KMM module resource still exists after unlock")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step("Deleting kernel module and configmap resources")
    delete_module_and_configmap(ssh_connection, module_name)

    get_logger().log_test_case_step("Verifying kernel module is no longer loaded")
    verify_module_unloaded(target_host_ssh)

    get_logger().log_test_case_step("Verifying module unload message in dmesg")
    verify_dmesg_message(target_host_ssh, "Goodbye, world!")

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p1
@mark.lab_is_simplex
def test_kernel_module_hello_world_lock_unlock_simplex(request):
    """Test kernel module hello world persistence after controller lock/unlock on simplex.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Upload hello world kernel module ConfigMap and Module YAML files
        - Apply hello world kernel module resources
        - Wait for worker pod to complete module build and load
        - Verify hello_world_dmesg kernel module is loaded via lsmod
        - Verify Hello, world! message appears in dmesg output
        - Verify KMM Module resource exists via kubectl get modules
        - Lock and unlock the active controller
        - Verify KMM app is in applied state and all the KMM pods are running
        - Verify hello_world_dmesg kernel module is still loaded after unlock
        - Verify Hello, world! message still appears in dmesg after unlock
        - Verify KMM Module resource still exists after unlock
        - Delete Module and ConfigMap resources
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    module_name = "kmm-test-simplex"

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Cleaning up test resources")
        cleanup_test_resources(ssh_connection, module_name)
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Getting active controller hostname")
    system_host_list = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list.get_active_controller().get_host_name()

    get_logger().log_test_case_step("Uploading hello world kernel module YAML files")
    generate_hello_world_configmap(ssh_connection, module_name)
    generate_hello_world_module_with_target_host(ssh_connection, module_name, active_controller)

    get_logger().log_test_case_step("Applying hello world kernel module")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Verifying worker pod completes")
    wait_for_worker_pods_completed(ssh_connection)

    get_logger().log_test_case_step("Running lsmod | grep hello to verify module is loaded")
    verify_module_loaded(ssh_connection)

    get_logger().log_test_case_step("Running dmesg and checking for Hello, world! message")
    verify_dmesg_message(ssh_connection, "Hello, world!")

    get_logger().log_test_case_step("Checking modules via kubectl get modules.kmm.sigs.x-k8s.io")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step(f"Locking controller {active_controller}")
    system_host_lock = SystemHostLockKeywords(ssh_connection)
    lock_success = system_host_lock.lock_host(active_controller)
    validate_equals(lock_success, True, "Controller should lock successfully")

    get_logger().log_test_case_step(f"Unlocking controller {active_controller}")
    unlock_success = system_host_lock.unlock_host(active_controller)
    validate_equals(unlock_success, True, "Controller should unlock successfully")

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after unlock")
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    system_app_list.validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_info("Verifying kernel module management pods are running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=30)

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module is still loaded after unlock")
    verify_module_loaded(ssh_connection)

    get_logger().log_test_case_step("Verifying Hello, world! message still in dmesg after unlock")
    verify_dmesg_message(ssh_connection, "Hello, world!")

    get_logger().log_test_case_step("Verifying KMM module resource still exists after unlock")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step("Deleting kernel module and configmap resources")
    delete_module_and_configmap(ssh_connection, module_name)

    get_logger().log_test_case_step("Verifying kernel module is no longer loaded")
    verify_module_unloaded(ssh_connection)

    get_logger().log_test_case_step("Verifying module unload message in dmesg")
    verify_dmesg_message(ssh_connection, "Goodbye, world!")

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.lab_has_standby_controller
def test_kernel_module_node_selector(request):
    """Test kernel module loads only on nodes matching selector.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Get all nodes
        - Label first node with test-hardware=absent
        - Label remaining nodes with test-hardware=present
        - Upload and apply kernel module with node selector test-hardware=present
        - Verify module loads on all present nodes
        - Verify module does not load on absent node
        - Change label on absent node to test-hardware=present
        - Verify worker pod completes on previously absent node
        - Verify module now loads on previously absent node
        - Delete Module and ConfigMap resources
        - Verify module unloads from all nodes
        - Remove labels from nodes
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    module_name = "kmm-selector"

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Cleaning up test resources with labels")
        cleanup_test_resources_with_labels(ssh_connection, module_name)
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Getting all nodes")
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = system_host_list.get_system_host_list().get_hosts()

    get_logger().log_test_case_step("Labeling first node with test-hardware=absent, others with test-hardware=present")
    label_keywords = KubectlLabelNodeKeywords(ssh_connection)
    absent_node = all_hosts[0].get_host_name()
    label_keywords.label_node(absent_node, "test-hardware", "absent")
    present_nodes = [host.get_host_name() for host in all_hosts[1:]]
    for node in present_nodes:
        label_keywords.label_node(node, "test-hardware", "present")

    get_logger().log_test_case_step("Uploading hello world kernel module YAML files")
    generate_hello_world_configmap(ssh_connection, module_name)
    generate_hello_world_module_with_selector(ssh_connection, module_name)

    get_logger().log_test_case_step("Applying hello world kernel module with node selector")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod_selector.yaml")

    get_logger().log_test_case_step("Verifying worker pod completes")
    pod_names = get_kmm_worker_pod_names(ssh_connection, [module_name], present_nodes)
    wait_for_worker_pods_completed(ssh_connection, pod_names)

    get_logger().log_test_case_step("Verifying KMM module resource exists")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step(f"Verifying module loaded on present nodes {present_nodes}")
    for present_node in present_nodes:
        present_node_ssh = LabConnectionKeywords().get_ssh_for_hostname(present_node)
        verify_module_loaded(present_node_ssh)
        verify_dmesg_message(present_node_ssh, "Hello, world!")

    get_logger().log_test_case_step(f"Verifying module not loaded on absent node {absent_node}")
    absent_node_ssh = LabConnectionKeywords().get_ssh_for_hostname(absent_node)
    verify_module_unloaded(absent_node_ssh)

    get_logger().log_test_case_step(f"Changing label on {absent_node} from absent to present")
    label_keywords.label_node(absent_node, "test-hardware", "present")

    get_logger().log_test_case_step(f"Verifying worker pod completes on {absent_node}")
    pod_names = get_kmm_worker_pod_names(ssh_connection, [module_name], [absent_node])
    wait_for_worker_pods_completed(ssh_connection, pod_names)

    get_logger().log_test_case_step(f"Verifying module now loaded on {absent_node}")
    verify_module_loaded(absent_node_ssh)
    verify_dmesg_message(absent_node_ssh, "Hello, world!")

    get_logger().log_test_case_step("Deleting kernel module and configmap resources")
    delete_module_and_configmap(ssh_connection, module_name)

    get_logger().log_test_case_step("Verifying kernel module is no longer loaded on any nodes")
    all_node_names = [host.get_host_name() for host in all_hosts]
    for node in all_node_names:
        node_ssh = LabConnectionKeywords().get_ssh_for_hostname(node)
        verify_module_unloaded(node_ssh)
        verify_dmesg_message(node_ssh, "Goodbye, world!")

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p1
def test_multiple_module_management(request):
    """Test KMM can manage multiple kernel modules simultaneously on all hosts.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Generate 2 ConfigMaps (kmm-multi-1-cm, kmm-multi-2-cm) for kernel module builds
        - Generate 2 Module CRs (kmm-multi-1, kmm-multi-2) targeting all hosts
        - Apply ConfigMaps and Module resources to cluster
        - Wait for KMM worker pods to complete building and loading modules on all hosts
        - Verify hello_world_dmesg kernel module is loaded on every host
        - Verify Hello, world! message appears in dmesg on every host
        - Verify both Module CRs exist in Kubernetes
        - Delete first module (kmm-multi-1) and verify second module remains loaded (isolation test)
        - Verify kmm-multi-1 Module CR is deleted
        - Verify kmm-multi-2 Module CR still exists
        - Delete second module (kmm-multi-2)
        - Verify both Module CRs are deleted
        - Verify hello_world_dmesg kernel module unloads from all hosts
        - Verify Goodbye, world! message appears in dmesg on all hosts
        - Delete ConfigMap resources
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Deleting kernel module resources")
        # Check if KMM app is still present before trying to delete module resources
        system_app_list = SystemApplicationListKeywords(ssh_connection)
        if system_app_list.is_app_present(APP_NAME):
            delete_module_and_configmap(ssh_connection, "kmm-multi-1", ignore_not_found=True)
            delete_module_and_configmap(ssh_connection, "kmm-multi-2", ignore_not_found=True)

        get_logger().log_teardown_step("Cleaning up kernel module YAML files")
        FileKeywords(ssh_connection).delete_file("/tmp/hello_world_cm.yaml")
        FileKeywords(ssh_connection).delete_file("/tmp/hello_world_mod.yaml")
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Generating 2 ConfigMaps and 2 Modules for multi-module test")
    generate_multiple_hello_world_configmaps(ssh_connection, ["kmm-multi-1", "kmm-multi-2"])
    generate_multiple_hello_world_modules(ssh_connection, ["kmm-multi-1", "kmm-multi-2"])

    get_logger().log_test_case_step("Getting all hosts and generating expected worker pod names")
    system_host_list = SystemHostListKeywords(ssh_connection)
    all_hosts = [host.get_host_name() for host in system_host_list.get_system_host_list().get_hosts()]
    get_logger().log_info(f"Hosts in cluster: {all_hosts}")
    pod_names = get_kmm_worker_pod_names(ssh_connection, ["kmm-multi-1", "kmm-multi-2"])

    get_logger().log_test_case_step("Applying ConfigMaps and Module resources to cluster")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Waiting for KMM worker pods to complete building and loading modules on all hosts")
    wait_for_worker_pods_completed(ssh_connection, pod_names)

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module loaded on all hosts")
    for host in all_hosts:
        get_logger().log_info(f"Verifying module loaded on {host}")
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host)
        verify_module_loaded(host_ssh)
        verify_dmesg_message(host_ssh, "Hello, world!")

    get_logger().log_test_case_step("Verifying both Module resources exist")
    verify_kmm_module_exists(ssh_connection, "kmm-multi-1")
    verify_kmm_module_exists(ssh_connection, "kmm-multi-2")

    get_logger().log_test_case_step("Deleting first module (kmm-multi-1) to verify module isolation")
    KubectlDeleteModuleKeywords(ssh_connection).delete_module("kmm-multi-1", NAMESPACE)

    get_logger().log_test_case_step("Verifying kmm-multi-1 Module CR is deleted")
    module_keywords = KubectlGetModuleKeywords(ssh_connection)
    validate_equals(module_keywords.is_module_present("kmm-multi-1", NAMESPACE), False, "kmm-multi-1 should be deleted")

    get_logger().log_test_case_step("Verifying kmm-multi-2 Module CR still exists")
    verify_kmm_module_exists(ssh_connection, "kmm-multi-2")

    get_logger().log_test_case_step("Deleting second module (kmm-multi-2)")
    KubectlDeleteModuleKeywords(ssh_connection).delete_module("kmm-multi-2", NAMESPACE)

    get_logger().log_test_case_step("Verifying kmm-multi-2 Module CR is deleted")
    validate_equals(module_keywords.is_module_present("kmm-multi-2", NAMESPACE), False, "kmm-multi-2 should be deleted")

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module unloaded from all hosts")
    for host in all_hosts:
        get_logger().log_info(f"Verifying module unloaded from {host}")
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(host)
        verify_module_unloaded(host_ssh)
        verify_dmesg_message(host_ssh, "Goodbye, world!")

    get_logger().log_test_case_step("Deleting ConfigMap resources")
    delete_configmap_keywords = KubectlDeleteConfigmapKeywords(ssh_connection)
    delete_configmap_keywords.delete_configmap("kmm-multi-1-cm", NAMESPACE)
    delete_configmap_keywords.delete_configmap("kmm-multi-2-cm", NAMESPACE)

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p1
def test_kernel_module_prebuilt_image(request):
    """Test kernel module deployment using prebuilt container image without ConfigMap.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Generate Module YAML with prebuilt container image (no build step required)
        - Apply Module resource to cluster
        - Verify hello_world_dmesg kernel module loads on active controller
        - Verify Hello, world! message appears in dmesg
        - Verify kmm-prebuilt Module CR exists
        - Delete Module resource to trigger unload
        - Verify hello_world_dmesg kernel module unloads from active controller
        - Verify Goodbye, world! message appears in dmesg
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Deleting kernel module resource")
        # Check if KMM app is still present before trying to delete module resources
        system_app_list = SystemApplicationListKeywords(ssh_connection)
        if system_app_list.is_app_present(APP_NAME):
            KubectlDeleteModuleKeywords(ssh_connection).delete_module("kmm-prebuilt", NAMESPACE, ignore_not_found=True)
        get_logger().log_teardown_step("Cleaning up kernel module YAML file")
        FileKeywords(ssh_connection).delete_file("/tmp/prebuilt_mod.yaml")
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Generating Module YAML with prebuilt container image")
    generate_prebuilt_module(ssh_connection)

    get_logger().log_test_case_step("Applying Module resource with prebuilt image")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml("/tmp/prebuilt_mod.yaml")

    get_logger().log_test_case_step("Verifying kmm-prebuilt Module CR exists")
    verify_kmm_module_exists(ssh_connection, "kmm-prebuilt")

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module loads on active controller")
    verify_module_loaded(ssh_connection)

    get_logger().log_test_case_step("Verifying Hello, world! message in dmesg")
    verify_dmesg_message(ssh_connection, "Hello, world!")

    get_logger().log_test_case_step("Deleting Module resource to trigger unload")
    KubectlDeleteModuleKeywords(ssh_connection).delete_module("kmm-prebuilt", NAMESPACE)

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module unloads from active controller")
    verify_module_unloaded(ssh_connection)

    get_logger().log_test_case_step("Verifying Goodbye, world! message in dmesg")
    verify_dmesg_message(ssh_connection, "Goodbye, world!")

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p1
def test_kernel_module_ordered_upgrade(request):
    """Test kernel module ordered upgrade without reboot using version labels.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Upload hello world ConfigMap for kernel module build
        - Generate Module YAML with version 1.0 targeting controller-0
        - Apply ConfigMap and Module v1.0 resources to cluster
        - Set initial version label (v1.0) on controller-0 to trigger module load
        - Wait for worker pod to complete building and loading module v1.0
        - Verify hello_world_dmesg kernel module is loaded on controller-0
        - Verify Hello, world! message appears in dmesg
        - Verify version.ready label shows v1.0 on controller-0
        - Perform atomic upgrade by patching Module to v2.0 (containerImage + version)
        - Remove version label from controller-0 to unload kernel module
        - Verify kernel module unloads from controller-0
        - Verify Goodbye, world! message appears in dmesg
        - Trigger ordered upgrade by setting version label to v2.0 on controller-0
        - Verify version.ready label updates to v2.0 on controller-0
        - Wait for worker pod to complete loading module v2.0
        - Verify hello_world_dmesg kernel module is loaded after upgrade
        - Verify KMM module resource exists
        - Delete kernel module resource
        - Delete configmap resource
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    module_name = "kmm-test-upgrade"
    VERSION_1 = "1.0"
    VERSION_2 = "2.0"

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Deleting kernel module and configmap resources")
        # Check if KMM app is still present before trying to delete module resources
        system_app_list = SystemApplicationListKeywords(ssh_connection)
        if system_app_list.is_app_present(APP_NAME):
            delete_module_and_configmap(ssh_connection, module_name, ignore_not_found=True)
        get_logger().log_teardown_step("Removing version label from controller-0")
        label_keywords = KubectlLabelNodeKeywords(ssh_connection)
        label_keywords.remove_label("controller-0", f"kmm.node.kubernetes.io/version-module.{NAMESPACE}.{module_name}")
        get_logger().log_teardown_step("Cleaning up kernel module YAML files")
        file_keywords = FileKeywords(ssh_connection)
        file_keywords.delete_file("/tmp/hello_world_cm.yaml")
        file_keywords.delete_file("/tmp/hello_world_mod_v1.yaml")
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Uploading hello world ConfigMap for kernel module build")
    generate_hello_world_configmap(ssh_connection, module_name)

    get_logger().log_test_case_step("Generating Module YAML with version 1.0 for controller-0")
    generate_versioned_module(ssh_connection, module_name, VERSION_1, "controller-0", "hello_world_mod_v1.yaml")

    get_logger().log_test_case_step("Applying ConfigMap and Module v1.0 resources to cluster")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod_v1.yaml")

    get_logger().log_test_case_step("Setting initial version label (v1.0) on controller-0 to trigger module load")
    label_keywords = KubectlLabelNodeKeywords(ssh_connection)
    version_label = f"kmm.node.kubernetes.io/version-module.{NAMESPACE}.{module_name}"
    label_keywords.label_node("controller-0", version_label, VERSION_1)

    get_logger().log_test_case_step("Waiting for worker pod to complete building and loading module v1.0")
    wait_for_worker_pods_completed(ssh_connection)

    get_logger().log_test_case_step("Verifying KMM module resource exists")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module is loaded on controller-0")
    verify_module_loaded(ssh_connection)

    get_logger().log_test_case_step("Verifying Hello, world! message in dmesg")
    verify_dmesg_message(ssh_connection, "Hello, world!")

    get_logger().log_test_case_step("Performing atomic upgrade by patching Module to v2.0 (containerImage + version)")
    patch_module_version(ssh_connection, module_name, VERSION_2)

    get_logger().log_test_case_step("Removing version label from controller-0 to unload kernel module")
    label_keywords.remove_label("controller-0", version_label)

    get_logger().log_test_case_step("Verifying kernel module unloads from controller-0")
    verify_module_unloaded(ssh_connection)

    get_logger().log_test_case_step("Verifying Goodbye, world! message in dmesg")
    verify_dmesg_message(ssh_connection, "Goodbye, world!")

    get_logger().log_test_case_step("Triggering ordered upgrade by setting version label to v2.0 on controller-0")
    label_keywords.label_node("controller-0", version_label, VERSION_2)

    get_logger().log_test_case_step("Waiting for worker pod to complete loading module v2.0")
    wait_for_worker_pods_completed(ssh_connection)

    get_logger().log_test_case_step("Verifying hello_world_dmesg kernel module is loaded after upgrade")
    verify_module_loaded(ssh_connection)

    get_logger().log_test_case_step("Verifying KMM module resource exists")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step("Deleting kernel module resource")
    KubectlDeleteModuleKeywords(ssh_connection).delete_module(module_name, NAMESPACE)

    get_logger().log_test_case_step("Deleting configmap resource")
    KubectlDeleteConfigmapKeywords(ssh_connection).delete_configmap(f"{module_name}-cm", NAMESPACE)

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p2
def test_kernel_module_invalid_module_handling(request):
    """Test KMM error handling with invalid module configurations.

    Steps:
        - Setup kernel module management environment
        - Generate and apply module with invalid container image reference
        - Verify Module CR is created
        - Verify kernel module does not load on active controller
        - Delete invalid image module
        - Generate and apply module with missing configmap reference
        - Verify Module CR is created but worker pods fail with CreateContainerConfigError
        - Verify kernel module does not load on active controller
        - Delete invalid configmap module and configmap
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    module_name = "kmm-invalid-img"

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Cleaning up test resources")
        cleanup_test_resources(ssh_connection, module_name)
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Getting active controller hostname")
    system_host_list = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list.get_active_controller().get_host_name()

    # Test 1: Invalid container image reference
    get_logger().log_test_case_step("Uploading module with invalid container image")
    yaml_keywords = YamlKeywords(ssh_connection)
    yaml_keywords.generate_yaml_file_from_template(get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/hello_world_mod.yaml.j2"), {"kmm_container_image_registry": "registry.local:9001/invalid/nonexistent", "module_name": module_name, "target_host": active_controller}, "hello_world_mod.yaml", "/tmp")

    get_logger().log_test_case_step("Applying module with invalid image")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Verifying module resource created")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step(f"Verifying module does not load on {active_controller}")
    verify_module_unloaded(ssh_connection)

    get_logger().log_test_case_step("Deleting invalid image module")
    KubectlDeleteModuleKeywords(ssh_connection).delete_module(module_name, NAMESPACE)

    # Test 2: Missing configmap reference
    get_logger().log_test_case_step("Uploading configmap and module with missing configmap reference")
    generate_hello_world_configmap(ssh_connection, f"{module_name}-cm")
    yaml_keywords.generate_yaml_file_from_template(
        get_stx_resource_path("resources/cloud_platform/kubernetes-operator-framework/kernel-module-mgmt/hello_world_cm.yaml.j2"),
        {
            "kmm_builder_image": "registry.local:9001/invalid/nonexistent",
            "module_name": f"{module_name}",
        },
        "hello_world_cm.yaml",
        "/tmp",
    )

    get_logger().log_test_case_step("Applying configmap and module with missing configmap reference")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Verifying module resource created")
    verify_kmm_module_exists(ssh_connection, f"{module_name}")

    get_logger().log_test_case_step("Verifying worker pods fail due to missing configmap")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status=["CreateContainerConfigError", "Error"], pod_names=[module_name], namespace=NAMESPACE, timeout=180)

    get_logger().log_test_case_step(f"Verifying module does not load on {active_controller}")
    verify_module_unloaded(ssh_connection)

    get_logger().log_test_case_step("Deleting invalid configmap module")
    KubectlDeleteModuleKeywords(ssh_connection).delete_module(f"{module_name}", NAMESPACE)

    get_logger().log_test_case_step("Deleting configmap resource")
    KubectlDeleteConfigmapKeywords(ssh_connection).delete_configmap(f"{module_name}-cm", NAMESPACE)

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)


@mark.p2
@mark.lab_has_compute
def test_kernel_module_hello_world_compute_reboot(request):
    """Test kernel module hello world persistence after compute node reboot.

    Steps:
        - Cleanup kernel module management application
        - Setup kernel module management environment
        - Select compute node for module deployment
        - Generate hello world kernel module ConfigMap and Module YAML files
        - Apply hello world kernel module resources on compute node
        - Wait for worker pod to complete module build and load
        - Verify hello_world_dmesg kernel module is loaded on compute node
        - Verify Hello, world! message appears in dmesg on compute node
        - Verify KMM Module resource exists
        - Reboot compute node and wait for host to come back online
        - Verify KMM application is in applied state after reboot
        - Verify KMM pods are running after reboot
        - Verify hello_world_dmesg kernel module is still loaded on compute node after reboot
        - Verify Hello, world! message still appears in dmesg on compute node after reboot
        - Delete Module and ConfigMap resources
        - Cleanup kernel module management application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    module_name = "kmm-test-compute-reboot"

    get_logger().log_test_case_step("Cleanup kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Cleaning up test resources")
        cleanup_test_resources(ssh_connection, module_name)
        get_logger().log_teardown_step("Removing kernel module management application")
        cleanup_kernel_module_management_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kernel module management environment")
    setup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Getting compute node hostname")
    system_host_list = SystemHostListKeywords(ssh_connection)
    compute_hosts = system_host_list.get_computes()
    validate_not_none(compute_hosts, "At least one compute node should be available")
    compute_node = compute_hosts[0].get_host_name()
    get_logger().log_info(f"Selected compute node: {compute_node}")

    get_logger().log_test_case_step("Uploading hello world kernel module YAML files")
    generate_hello_world_configmap(ssh_connection, module_name)
    generate_hello_world_module_with_target_host(ssh_connection, module_name, compute_node)

    get_logger().log_test_case_step("Applying hello world kernel module")
    apply_keywords = KubectlFileApplyKeywords(ssh_connection)
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_cm.yaml")
    apply_keywords.apply_resource_from_yaml("/tmp/hello_world_mod.yaml")

    get_logger().log_test_case_step("Verifying worker pod completes")
    wait_for_worker_pods_completed(ssh_connection)

    get_logger().log_test_case_step(f"Verifying hello_world_dmesg kernel module is loaded on {compute_node}")
    compute_node_ssh = LabConnectionKeywords().get_ssh_for_hostname(compute_node)
    verify_module_loaded(compute_node_ssh)

    get_logger().log_test_case_step(f"Verifying Hello, world! message in dmesg on {compute_node}")
    verify_dmesg_message(compute_node_ssh, "Hello, world!")

    get_logger().log_test_case_step("Verifying KMM module resource exists")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step(f"Rebooting compute node {compute_node}")
    pre_uptime = system_host_list.get_uptime(compute_node)
    compute_node_ssh.send_as_sudo("reboot -f")
    system_host_reboot = SystemHostRebootKeywords(ssh_connection)
    reboot_success = system_host_reboot.wait_for_force_reboot(compute_node, pre_uptime)
    validate_equals(reboot_success, True, "Compute node should reboot successfully")

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after reboot")
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    system_app_list.validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Verifying KMM pods are running after reboot")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KMM_EXPECTED_PODS, namespace=NAMESPACE, timeout=120)

    get_logger().log_test_case_step(f"Verifying hello_world_dmesg kernel module is still loaded on {compute_node} after reboot")
    compute_node_ssh = LabConnectionKeywords().get_ssh_for_hostname(compute_node)
    verify_module_loaded(compute_node_ssh)

    get_logger().log_test_case_step(f"Verifying Hello, world! message still in dmesg on {compute_node} after reboot")
    verify_dmesg_message(compute_node_ssh, "Hello, world!")

    get_logger().log_test_case_step("Verifying KMM module resource still exists after reboot")
    verify_kmm_module_exists(ssh_connection, module_name)

    get_logger().log_test_case_step("Deleting kernel module and configmap resources")
    delete_module_and_configmap(ssh_connection, module_name)

    get_logger().log_test_case_step("Verifying kernel module is no longer loaded")
    verify_module_unloaded(compute_node_ssh)

    get_logger().log_test_case_step("Verifying module unload message in dmesg")
    verify_dmesg_message(compute_node_ssh, "Goodbye, world!")

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)
