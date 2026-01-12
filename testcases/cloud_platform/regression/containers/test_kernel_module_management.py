from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_greater_than, validate_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.k8s.helm.kubectl_get_helm_keywords import KubectlGetHelmKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "app-kernel-module-management"
NAMESPACE = "kernel-module-management"
CHART_PATH = "/usr/local/share/applications/helm/kernel-module-management-app-[0-9]*"


def setup_kernel_module_management_environment(ssh_connection: SSHConnection) -> None:
    """Setup kernel module management application.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info(f"Uploading {APP_NAME} application")
    ls_keywords = LsKeywords(ssh_connection)
    actual_chart = ls_keywords.get_first_matching_file(CHART_PATH)
    upload_input = SystemApplicationUploadInput()
    upload_input.set_tar_file_path(actual_chart)
    upload_input.set_app_name(APP_NAME)
    system_app_upload = SystemApplicationUploadKeywords(ssh_connection)
    system_app_upload.system_application_upload(upload_input)

    get_logger().log_info(f"Applying {APP_NAME} application")
    system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
    system_app_apply.system_application_apply(APP_NAME)

    # Wait for all kernel module management pods to be running
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    pods = kubectl_pods.get_pods(namespace=NAMESPACE).get_pods()
    validate_greater_than(len(pods), 0, f"Expected pods in namespace {NAMESPACE} but found none")
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", namespace=NAMESPACE)


def verify_kernel_module_manager_helmchart_removed(ssh_connection: SSHConnection) -> None:
    """Verify that kernel-module-manager entry is removed from HelmChart list.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Verifying kernel-module-manager HelmChart is removed")
    kubectl_helmchart = KubectlGetHelmKeywords(ssh_connection)
    chart = kubectl_helmchart.get_helmchart_by_name(APP_NAME, NAMESPACE)
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
        system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        if system_app_apply.is_already_applied(APP_NAME):
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
        - Remove and delete the application
        - Verify kernel-module-manager HelmChart is removed
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

    get_logger().log_test_case_step("Removing kernel module management application")
    cleanup_kernel_module_management_environment(ssh_connection)

    get_logger().log_test_case_step("Verifying kernel-module-manager HelmChart is removed")
    verify_kernel_module_manager_helmchart_removed(ssh_connection)
