from typing import Iterable

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.node.kubectl_describe_node_keywords import KubectlDescribeNodeKeywords
from keywords.k8s.pods.kubectl_create_pods_keywords import KubectlCreatePodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.hardware.hardware_keywords import HardwareKeywords
from keywords.linux.lsmod.lsmod_keywords import LsmodKeywords

from pytest import mark


def count_qat_env_vars(env_lines: Iterable[str]) -> int:
    """
    Count QAT-related environment variables in the given output.

    Args:
        env_lines (Iterable[str]): Environment variable lines.

    Returns:
        int: Number of variables starting with 'QAT'.
    """

    count = 0
    for line in env_lines:
        if line.startswith("QAT"):
            count += 1
    return count


@mark.p0
@mark.lab_has_qat
@mark.lab_has_page_size_1gb
def test_intel_qat_lifecycle(request):
    """Tests the full lifecycle of Intel QAT device plugins.

    Validates module loading, installs NFD and Intel Device Plugins,
    enables the QAT Helm chart, deploys a DPDK crypto test pod,
    and verifies QAT devices are allocated to the container.
    """

    def cleanup_qat_test():
        """Removes Intel Device Plugins, NFD apps, and the test pod."""
        app_config = ConfigurationManager.get_app_config()
        intel_plugins_app_name = app_config.get_intel_device_plugins_app_name()
        nfd_app_name = app_config.get_node_feature_discovery_app_name()
        get_logger().log_teardown_step(f"Removing {intel_plugins_app_name} app")
        SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(intel_plugins_app_name)
        get_logger().log_teardown_step(f"Removing {nfd_app_name} app")
        SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(nfd_app_name)
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod("dpdk-test-crypto-perf")

    request.addfinalizer(cleanup_qat_test)
    # Setup environment
    EXPECTED_QAT_DEVICE_COUNT = 4
    CONTAINER_DEPLOYED_TIMEOUT = 60

    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()

    nfd_app_name = app_config.get_node_feature_discovery_app_name()
    nfd_file_path = f"{base_path}{nfd_app_name}*.tgz"

    intel_plugins_app_name = app_config.get_intel_device_plugins_app_name()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    nfd_applied = SystemApplicationApplyKeywords(ssh_connection).is_already_applied(nfd_app_name)

    get_logger().log_test_case_step("Check if modules are loaded")
    lsmod_keywords = LsmodKeywords(ssh_connection)
    hw_keywords = HardwareKeywords(ssh_connection)
    module_list = hw_keywords.get_required_modules()
    lsmod_out = lsmod_keywords.get_lsmod_output()
    lsmod_result = lsmod_out.check_modules_loaded(module_list)
    validate_equals(all(lsmod_result.values()), True, "All modules are loaded!")

    if nfd_applied:
        get_logger().log_info("Node Feature Discovery detected. Removing...")
        nfd_delete_message_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(nfd_app_name)
        validate_equals(nfd_delete_message_output, f"Application {nfd_app_name} deleted.\n", "Node Feature Discovery validation")

    get_logger().log_info("NFD not installed. Installing...")
    nfd_app_output = SystemApplicationUploadKeywords(ssh_connection).system_application_upload_and_apply_app(nfd_app_name, nfd_file_path)
    nfd_app_object = nfd_app_output.get_system_application_object()
    validate_equals(nfd_app_object.get_name(), nfd_app_name, f"{nfd_app_name} name validation")
    validate_equals(nfd_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{nfd_app_name} application status validation")

    get_logger().log_test_case_step("Ensure Intel Device Plugins is installed")
    intel_plugins_applied = SystemApplicationApplyKeywords(ssh_connection).is_already_applied(intel_plugins_app_name)
    if intel_plugins_applied:
        get_logger().log_info("Intel Device Plugins detected. Removing...")
        remove_delete_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(intel_plugins_app_name)
        validate_equals(remove_delete_output, f"Application {intel_plugins_app_name} deleted.\n", "Intel Device Plugin deletion validation")

    get_logger().log_info("Intel Device Plugins not installed. Uploading...")

    # Upload Intel Device Plugins application
    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name(intel_plugins_app_name)
    upload_input.set_tar_file_path(f"{base_path}{intel_plugins_app_name}*.tgz")
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)

    get_logger().log_test_case_step("Enable Intel QAT Helm chart")
    helm_modify_keywords = SystemHelmChartAttributeModifyKeywords(ssh_connection)
    modify_output = helm_modify_keywords.helm_chart_attribute_modify_enabled(app_name=intel_plugins_app_name, namespace=intel_plugins_app_name, chart_name="intel-device-plugins-qat", enabled_value="true")

    modify_obj = modify_output.get_helm_chart_attribute_modify()
    modify_attributes = modify_obj.get_attributes()
    enabled_attr = modify_attributes.get("enabled", False)
    validate_equals(enabled_attr, True, "Validate QAT Helm chart is enabled")

    get_logger().log_test_case_step("Validate enablement using helm-override-show")
    helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
    override_output = helm_override_keywords.get_system_helm_override_show(intel_plugins_app_name, "intel-device-plugins-qat", intel_plugins_app_name)
    override_obj = override_output.get_helm_override_show()
    override_attributes = override_obj.get_attributes()

    # handle string case from CLI output
    is_enabled = "enabled: true" in override_attributes.lower()
    validate_equals(is_enabled, True, "Validate QAT plugin enablement in override show")

    get_logger().log_test_case_step("Apply Intel Device Plugins application")
    apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(intel_plugins_app_name)
    applied_app = apply_output.get_system_application_object()
    validate_not_equals(applied_app, None, "Intel Device Plugins application apply validation")

    get_logger().log_test_case_step("check if pod is running")
    namespace = "intel-device-plugins-operator"
    pod_prefix = "intel-qat-plugin"
    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
    pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
    validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

    get_logger().log_test_case_step("Check if resource name from pod is valid")
    # Before stx 11, the resource name for granite should be 'generic'
    major = CloudPlatformVersionManagerClass().get_sw_version().get_major_version()
    resource_name = hw_keywords.get_resource_name()
    if resource_name == "sym-asym-dc" and int(major) < 26:
        resource_name = "generic"
    dictionary = {"resource_name": resource_name}
    # Getting name from node description
    controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    node_description = KubectlDescribeNodeKeywords(ssh_connection).describe_node(controller).get_node_description()
    node_resource_name = node_description.get_allocated_resources().get_qat_intel_com().get_resource().split("/")[1]
    assert node_resource_name == resource_name, f"Resource name from node description ({node_resource_name}) does not match expected resource name ({resource_name})"

    get_logger().log_test_case_step("Create yaml for QAT Container using the proper resource name")

    # Set yaml file path using the resource name acquired
    jinja_template_path = get_stx_resource_path("resources/cloud_platform/networking/qat/qat-dpdk_template.yaml.j2")
    output_template_path = "qat-dpdk.yaml"
    node_qat_dpdk_path = "/home/sysadmin/"

    yaml_keywords = YamlKeywords(ssh_connection)
    yaml_keywords.generate_yaml_file_from_template(jinja_template_path, dictionary, output_template_path, node_qat_dpdk_path)

    get_logger().log_test_case_step("Running QAT Container")

    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(node_qat_dpdk_path+output_template_path)

    get_logger().log_test_case_step("check if QAT pod is running")
    namespace = "default"
    pod_prefix = "dpdk-test-crypto-perf"
    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
    pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace, CONTAINER_DEPLOYED_TIMEOUT)
    validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f" -n {namespace}"
    cmd = "printenv"
    output = kubeclt_exec_in_pods.run_pod_exec_cmd(pod_prefix, cmd, options=options)

    validate_equals(count_qat_env_vars(output), EXPECTED_QAT_DEVICE_COUNT, "Number of QAT devices allocated")
