from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.k8s.raw_metrics.kubectl_get_raw_metrics_keywords import KubectlGetRawMetricsKeywords


@mark.p3
def test_deprecated_api_system_default():
    """
    Test to ensure which deprecated APIs are present in cloud platform.
    This test will fail if any unexpected deprecated API is found.
    kubectl get --raw /metrics | grep apiserver_requested_deprecated_apis{}

    Test Steps:
        Step 1: Execute the command to get the raw metrics from the Kubernetes API server.
        Step 2: Use grep to filter out the deprecated APIs.
        Step 3: Check if any deprecated APIs are found in the output.
        Step 4: If any deprecated APIs are found, the test will fail.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_test_case_step("Get deprecated APIs from the Kubernetes API server")
    # these groups :  ["helm.toolkit.fluxcd.io", "source.toolkit.fluxcd.io"]
    # are expected to be removed in the future, so we check if they are not present
    deprecated_api_output = KubectlGetRawMetricsKeywords(ssh_connection).is_deprecated_api_found(["helm.toolkit.fluxcd.io", "source.toolkit.fluxcd.io"])
    validate_equals(deprecated_api_output, False, "Deprecated APIs validation in the Kubernetes API server output")


@mark.p3
def test_deprecated_api_system_kubevirt():
    """
    Test to ensure which deprecated APIs are present in cloud platform when kubevirt is applied.
    This test will fail if any unexpected deprecated API is not found.
    kubectl get --raw /metrics | grep apiserver_requested_deprecated_apis

    Test Steps:
        Step 1: Upload and apply the kubevirt-app to the active controller.
        Step 2: Execute the command to get the raw metrics from the Kubernetes API server in a system with kubevirt-app applied.
        Step 3: Use grep to filter out the deprecated APIs.
        Step 4: Check if any deprecated APIs are found in the output.
        Step 5: If any deprecated APIs are found, the test will fail.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    # Setups the upload input object
    get_logger().log_test_case_step("Upload kubevirt-app in the active controller")
    app_config = ConfigurationManager.get_app_config()
    kubevirt_app_name = "kubevirt-app"

    base_path = app_config.get_base_application_path()
    system_application_upload_input = SystemApplicationUploadInput()
    system_application_upload_input.set_app_name(kubevirt_app_name)
    system_application_upload_input.set_tar_file_path(f"{base_path}{kubevirt_app_name}*.tgz")

    # Uploads the app file and verifies it
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    kubevirt_app_status = system_applications.get_application(kubevirt_app_name).get_status()
    validate_equals(kubevirt_app_status, "uploaded", f"{kubevirt_app_name} upload status validation")
    get_logger().log_test_case_step("Apply kubevirt-app in the active controller")

    # Applies the app to the active controller
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(kubevirt_app_name)

    system_application_show_output = SystemApplicationShowKeywords(ssh_connection).validate_app_progress_contains("kubevirt-app", "completed")
    validate_equals(system_application_show_output.get_status(), "applied", "kubevirt-app's status is applied")
    validate_equals(system_application_show_output.get_active(), "True", "kubevirt-app's active is True")

    get_logger().log_test_case_step("Get deprecated APIs from the Kubernetes API server")
    expected_deprecated_output_groups = ["cdi.kubevirt.io", "kubevirt.io"]
    deprecated_api_output = KubectlGetRawMetricsKeywords(ssh_connection=ssh_connection).is_deprecated_api_found(expected_deprecated_output_groups)

    # Removes the application
    get_logger().log_test_case_step("Remove kubevirt-app in the active controller")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(kubevirt_app_name)
    system_application_remove_input.set_force_removal(False)
    system_application_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)
    validate_equals(system_application_output.get_system_application_object().get_status(), SystemApplicationStatusEnum.UPLOADED.value, "Application removal status validation")

    # Deletes the application
    get_logger().log_test_case_step("Delete kubevirt-app in the active controller")
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(kubevirt_app_name)
    system_application_delete_input.set_force_deletion(False)
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(delete_msg, f"Application {kubevirt_app_name} deleted.\n", "Application deletion message validation")
    validate_equals(deprecated_api_output, True, "Deprecated APIs validation in the Kubernetes API server output")
