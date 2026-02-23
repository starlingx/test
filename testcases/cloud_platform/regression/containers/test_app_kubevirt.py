from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.helm.kubectl_get_helm_keywords import KubectlGetHelmKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.ln.ln_keywords import LnKeywords
from keywords.linux.ls.ls_keywords import LsKeywords
from keywords.linux.which.which_keywords import WhichKeywords

APP_NAME = "kubevirt-app"
KUBEVIRT_NAMESPACE = "kubevirt"
CDI_NAMESPACE = "cdi"
CHART_PATH = "/usr/local/share/applications/helm/kubevirt-app-[0-9]*"
CHART_NAME = "kube-system-kubevirt-app"
KUBE_SYSTEM_NAMESPACE = "kube-system"

# Expected pod name patterns
KUBEVIRT_EXPECTED_PODS = ["virt-api", "virt-operator", "kubevirt-daemonset"]
CDI_EXPECTED_PODS = ["cdi-apiserver", "cdi-deployment", "cdi-operator", "cdi-uploadproxy"]

# For virtctl setup
PATH_VARIABLE = "/home/sysadmin/bin"
VIRTCTL_PATH = "/var/opt/kubevirt/virtctl"


def setup_virtctl_on_controller(ssh_connection: SSHConnection) -> bool:
    """Setup virtctl on a single controller.

    Args:
        ssh_connection (SSHConnection): SSH connection to controller.

    Returns:
        bool: True if virtctl setup successfully, False otherwise.
    """
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.create_directory(PATH_VARIABLE)

    get_logger().log_info("Finding virtctl executable path")
    ls_keywords = LsKeywords(ssh_connection)
    actual_virtctl_path = ls_keywords.get_first_matching_file(VIRTCTL_PATH)

    get_logger().log_info(f"Creating symbolic link to virtctl at {PATH_VARIABLE}/virtctl")
    ln_keywords = LnKeywords(ssh_connection)
    ln_keywords.create_symbolic_link_to_a_file(actual_virtctl_path, f"{PATH_VARIABLE}/virtctl")
    ssh_connection.close()


def setup_virtctl(ssh_connection: SSHConnection) -> None:
    """Setup virtctl client executable to be accessible from sysadmin's PATH.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    system_host_list = SystemHostListKeywords(ssh_connection)
    controllers = system_host_list.get_controllers()

    # Create symbolic link to virtctl on all controllers
    for controller in controllers:
        controller_name = controller.get_host_name()
        get_logger().log_info(f"Setting up virtctl on {controller_name}")
        controller_ssh = LabConnectionKeywords().get_ssh_for_hostname(controller_name)
        setup_virtctl_on_controller(controller_ssh)
        ssh_connection.close()

    get_logger().log_info("Validating virtctl is set up properly")
    which_keywords = WhichKeywords(ssh_connection)
    which_keywords.which_process("virtctl")


def remove_virtctl(ssh_connection: SSHConnection) -> None:
    """Remove virtctl client executable from sysadmin's PATH.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Removing virtctl from all controllers")
    system_host_list = SystemHostListKeywords(ssh_connection)
    controllers = system_host_list.get_controllers()

    for controller in controllers:
        controller_name = controller.get_host_name()
        get_logger().log_info(f"Removing virtctl from {controller_name}")
        controller_ssh = LabConnectionKeywords().get_ssh_for_hostname(controller_name)
        file_keywords = FileKeywords(controller_ssh)
        file_keywords.delete_file(f"{PATH_VARIABLE}/virtctl")
        file_keywords.delete_directory(PATH_VARIABLE)


def setup_kubevirt_environment(ssh_connection: SSHConnection) -> None:
    """Setup kubevirt application.

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

    # Verify all kubevirt and cdi pods are running
    get_logger().log_info("Verifying kubevirt pods are running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=30)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=30)

    # setting up virtctl
    get_logger().log_info("Setting up virtctl on all controllers")
    setup_virtctl(ssh_connection)


def verify_kubevirt_helmchart_removed(ssh_connection: SSHConnection) -> None:
    """Verify that kubevirt entry is removed from HelmChart list.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Verifying kubevirt HelmChart is removed")
    kubectl_helmchart = KubectlGetHelmKeywords(ssh_connection)
    chart = kubectl_helmchart.get_helmchart_by_name(CHART_NAME, KUBE_SYSTEM_NAMESPACE)
    validate_none(chart, "kubevirt HelmChart should be removed")


def cleanup_kubevirt_environment(ssh_connection: SSHConnection) -> None:
    """Clean up kubevirt test resources.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Cleaning up kubevirt test resources")

    system_app_list = SystemApplicationListKeywords(ssh_connection)
    if system_app_list.is_app_present(APP_NAME):
        get_logger().log_info(f"Removing {APP_NAME} application")
        system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        if system_app_apply.is_applied_or_failed(APP_NAME):
            remove_input = SystemApplicationRemoveInput()
            remove_input.set_app_name(APP_NAME)
            system_app_remove = SystemApplicationRemoveKeywords(ssh_connection)
            system_app_remove.system_application_remove(remove_input)

        delete_input = SystemApplicationDeleteInput()
        delete_input.set_app_name(APP_NAME)
        delete_input.set_force_deletion(True)
        system_app_delete = SystemApplicationDeleteKeywords(ssh_connection)
        system_app_delete.get_system_application_delete(delete_input)
        # remove virtctl
        remove_virtctl(ssh_connection)


@mark.p1
def test_kubevirt_upload_apply_delete(request):
    """Test kubevirt application upload, apply and delete.

    Steps:
        - Cleanup kubevirt application
        - Upload and Apply kubevirt application
        - Reapply the application
        - Verify pods are running
        - Reboot the controller
        - Verify application is in applied state
        - Verify pods are running
        - Remove and delete the application
        - Verify kubevirt HelmChart is removed
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleanup kubevirt application")
    cleanup_kubevirt_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Removing kubevirt application if not already removed")
        cleanup_kubevirt_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Setting up kubevirt environment")
    setup_kubevirt_environment(ssh_connection)

    get_logger().log_test_case_step(f"Reapplying {APP_NAME} application")
    system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
    system_app_apply.system_application_apply(APP_NAME)

    get_logger().log_test_case_step("Verifying kubevirt pods are running after reapply")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=120)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=120)

    system_host_list = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list.get_active_controller().get_host_name()

    get_logger().log_test_case_step(f"Rebooting controller {active_controller}")
    pre_uptime = system_host_list.get_uptime(active_controller)
    ssh_connection.send_as_sudo("reboot -f")
    system_host_reboot = SystemHostRebootKeywords(ssh_connection)
    reboot_success = system_host_reboot.wait_for_force_reboot(active_controller, pre_uptime)
    validate_equals(reboot_success, True, "Controller should reboot successfully")

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after reboot")
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    system_app_list.validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Verifying kubevirt pods are running after reboot")
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=120)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=120)

    get_logger().log_test_case_step("Removing kubevirt application")
    cleanup_kubevirt_environment(ssh_connection)

    get_logger().log_test_case_step("Verifying kubevirt HelmChart is removed")
    verify_kubevirt_helmchart_removed(ssh_connection)
