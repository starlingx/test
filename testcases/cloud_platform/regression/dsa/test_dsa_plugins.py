from pytest import mark

from config.configuration_manager import ConfigurationManager
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from framework.validation.validation import validate_equals, validate_not_equals
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.lsmod.lsmod_keywords import LsmodKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords


@mark.p0
@mark.lab_has_dsa
def test_intel_dsa_lifecycle(request):
    def cleanup_dsa_test():
        app_config = ConfigurationManager.get_app_config()
        intel_plugins_app_name = app_config.get_intel_device_plugins_app_name()
        nfd_app_name = app_config.get_node_feature_discovery_app_name()
        get_logger().log_teardown_step(f"Removing {intel_plugins_app_name} app")
        SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(intel_plugins_app_name)
        get_logger().log_teardown_step(f"Removing {nfd_app_name} app")
        SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(nfd_app_name)

    request.addfinalizer(cleanup_dsa_test)
    # Setup environment
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()

    nfd_app_name = app_config.get_node_feature_discovery_app_name()
    nfd_file_path = f"{base_path}{nfd_app_name}*.tgz"

    intel_plugins_app_name = app_config.get_intel_device_plugins_app_name()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    nfd_applied = SystemApplicationApplyKeywords(ssh_connection).is_already_applied(nfd_app_name)

    get_logger().log_test_case_step("Check if modules are loaded")
    lsmod_keywords = LsmodKeywords(ssh_connection)
    module_list = ("idxd", "idxd_bus")
    lsmod_out = lsmod_keywords.get_lsmod_output()
    lsmod_result = lsmod_out.check_modules_loaded(module_list)
    validate_equals(all(lsmod_result.values()), True, "All modules are loaded!")

    if nfd_applied:
        get_logger().log_info("Node Feature Discovery detected. Removing...")
        nfd_delete_message_output = (
            SystemApplicationRemoveKeywords(ssh_connection)
            .system_application_remove_and_delete_app(nfd_app_name)
        )
        validate_equals(nfd_delete_message_output, f"Application {nfd_app_name} deleted.\n", "Node Feature Discovery validation")

    get_logger().log_info("NFD not installed. Installing...")
    nfd_app_output = (SystemApplicationUploadKeywords(ssh_connection).system_application_upload_and_apply_app(nfd_app_name, nfd_file_path))
    nfd_app_object = nfd_app_output.get_system_application_object()
    validate_equals(nfd_app_object.get_name(), nfd_app_name, f"{nfd_app_name} name validation")
    validate_equals(nfd_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{nfd_app_name} application status validation")

    get_logger().log_test_case_step("Ensure Intel Device Plugins is installed")
    intel_plugins_applied = SystemApplicationApplyKeywords(ssh_connection).is_already_applied(intel_plugins_app_name)
    if intel_plugins_applied:
        get_logger().log_info("Intel Device Plugins detected. Removing...")
        remove_delete_output = (
            SystemApplicationRemoveKeywords(ssh_connection)
            .system_application_remove_and_delete_app(intel_plugins_app_name)
        )
        validate_equals(remove_delete_output, f"Application {intel_plugins_app_name} deleted.\n", "Intel Device Plugin deletion validation")

    get_logger().log_info("Intel Device Plugins not installed. Uploading...")

    # Upload Intel Device Plugins application
    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name(intel_plugins_app_name)
    upload_input.set_tar_file_path(f"{base_path}{intel_plugins_app_name}*.tgz")
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)

    get_logger().log_test_case_step("Enable Intel dsa Helm chart")
    helm_modify_keywords = SystemHelmChartAttributeModifyKeywords(ssh_connection)
    modify_output = helm_modify_keywords.helm_chart_attribute_modify_enabled(app_name=intel_plugins_app_name, namespace=intel_plugins_app_name, chart_name="intel-device-plugins-dsa", enabled_value="true")

    modify_obj = modify_output.get_helm_chart_attribute_modify()
    modify_attributes = modify_obj.get_attributes()
    enabled_attr = modify_attributes.get("enabled", False)
    validate_equals(enabled_attr, True, "Validate dsa Helm chart is enabled")

    get_logger().log_test_case_step("Validate enablement using helm-override-show")
    helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
    override_output = helm_override_keywords.get_system_helm_override_show(intel_plugins_app_name, "intel-device-plugins-dsa", intel_plugins_app_name)
    override_obj = override_output.get_helm_override_show()
    override_attributes = override_obj.get_attributes()

    # handle string case from CLI output
    is_enabled = "enabled: true" in override_attributes.lower()
    validate_equals(is_enabled, True, "Validate dsa plugin enablement in override show")

    get_logger().log_test_case_step("Apply Intel Device Plugins application")
    apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(intel_plugins_app_name)
    applied_app = apply_output.get_system_application_object()
    validate_not_equals(applied_app, None, "Intel Device Plugins application apply validation")

    get_logger().log_test_case_step("check if pod is running")
    namespace = "intel-device-plugins-operator"
    pod_prefix = "intel-dsa-plugin"
    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
    pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
    validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")
