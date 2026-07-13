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
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.cloud_platform.system.host.system_host_show_keywords import SystemHostShowKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

APP_NAME = "ptp-notification"
NAMESPACE = "notification"
POD_PREFIX = "ptp-ptp-notification"
REGISTRATION_POD_PREFIX = "ptp-ptp-notification-registration"
LABEL_NOTIFICATION = "ptp-notification=true"
LABEL_REGISTRATION = "ptp-registration=true"


def _get_ssh_and_config():
    """Return active SSH connection and app config."""
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_config = ConfigurationManager.get_app_config()
    return ssh_connection, app_config


def _get_ptp_hosts(ssh_connection):
    """Return list of host names with clock_synchronization=ptp."""
    nodes = ConfigurationManager.get_lab_config().get_nodes()
    host_show_keywords = SystemHostShowKeywords(ssh_connection)
    ptp_hosts = []
    for node in nodes:
        node_name = node.get_name()
        host_show_output = host_show_keywords.get_system_host_show_output(node_name)
        host_show_object = host_show_output.get_system_host_show_object()
        clock_sync = host_show_object.get_clock_synchronization()
        if clock_sync == "ptp":
            ptp_hosts.append(node_name)
            get_logger().log_info(
                f"Host {node_name} has clock_synchronization=ptp")
        else:
            get_logger().log_info(
                f"Host {node_name} has clock_synchronization={clock_sync}, "
                f"skipping PTP label assignment for this host")
    return ptp_hosts


def _get_labeled_node_count(ptp_hosts):
    """Return the number of PTP hosts that will get ptp-notification label."""
    return len(ptp_hosts)


def assign_ptp_notification_labels(ssh_connection, ptp_hosts):
    """Assign ptp-notification and ptp-registration labels to PTP hosts only."""
    nodes = ConfigurationManager.get_lab_config().get_nodes()
    label_keywords = SystemHostLabelKeywords(ssh_connection)
    for node in nodes:
        node_name = node.get_name()
        if node_name not in ptp_hosts:
            get_logger().log_info(
                f"Skipping label assignment for {node_name} "
                f"(no PTP clock synchronization)")
            continue
        if not label_keywords.get_system_host_label_list(node_name).get_label_value("ptp-notification"):
            label_keywords.system_host_label_assign(node_name, LABEL_NOTIFICATION)
        if node.get_type() == "controller":
            if not label_keywords.get_system_host_label_list(node_name).get_label_value("ptp-registration"):
                label_keywords.system_host_label_assign(node_name, LABEL_REGISTRATION)


def remove_ptp_notification_labels(ssh_connection):
    """Remove ptp-notification and ptp-registration labels from nodes."""
    nodes = ConfigurationManager.get_lab_config().get_nodes()
    label_keywords = SystemHostLabelKeywords(ssh_connection)
    for node in nodes:
        node_name = node.get_name()
        if label_keywords.get_system_host_label_list(node_name).get_label_value("ptp-notification"):
            label_keywords.system_host_label_remove(node_name, "ptp-notification")
        if node.get_type() == "controller":
            if label_keywords.get_system_host_label_list(node_name).get_label_value("ptp-registration"):
                label_keywords.system_host_label_remove(node_name, "ptp-registration")


def upload_ptp_notification_application(ssh_connection, app_config):
    """Upload the ptp-notification application tarball."""
    base_path = app_config.get_base_application_path()
    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name(APP_NAME)
    upload_input.set_tar_file_path(f"{base_path}{APP_NAME}*.tgz")
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)


def override_ptp_notification_application(ssh_connection):
    """Create and apply helm override to disable v1 ptptracking."""
    notification_override = """\
ptptracking:
  enabled: False
"""
    override_path = "/home/sysadmin/ptp-notification-override.yaml"
    FileKeywords(ssh_connection).create_file_with_echo(override_path, notification_override)
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override(
        override_path, APP_NAME, APP_NAME, NAMESPACE
    )


def apply_ptp_notification_application(ssh_connection):
    """Apply the ptp-notification application."""
    return SystemApplicationApplyKeywords(ssh_connection).system_application_apply(
        app_name=APP_NAME, timeout=600
    )


def remove_ptp_notification_application(ssh_connection):
    """Remove the ptp-notification application."""
    remove_input = SystemApplicationRemoveInput()
    remove_input.set_app_name(APP_NAME)
    SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(remove_input)


def delete_ptp_notification_application(ssh_connection):
    """Delete the ptp-notification application."""
    delete_input = SystemApplicationDeleteInput()
    delete_input.set_app_name(APP_NAME)
    SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(delete_input)


def verify_ptp_notification_application_applied(ssh_connection, ptp_hosts):
    """Verify app status is 'applied' and pods are Running.

    Validates:
        - Application status is 'applied'
        - One registration pod on any host
        - One ptp-ptp-notification pod per PTP labeled host (all Running)
    """
    SystemApplicationListKeywords(ssh_connection).validate_app_status(
        APP_NAME, SystemApplicationStatusEnum.APPLIED.value
    )
    labeled_node_count = _get_labeled_node_count(ptp_hosts)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    pods_output = pod_keywords.get_pods(namespace=NAMESPACE)
    # Validate ptp-notification pod count (one per labeled host)
    ptp_pods = pods_output.get_pods_start_with(starts_with=POD_PREFIX)
    validate_equals(len(ptp_pods), labeled_node_count,
                    f"Expected {labeled_node_count} ptp-notification pods (one per PTP host)")
    # Validate registration pod count (exactly one)
    reg_pods = pods_output.get_pods_start_with(starts_with="registration")
    validate_equals(len(reg_pods), 1, "Expected 1 registration pod")
    # Validate all ptp-notification pods are Running
    pod_names = pods_output.get_unique_pod_matching_prefix(starts_with=POD_PREFIX)
    pod_status = pod_keywords.wait_for_pod_status(pod_names, "Running", NAMESPACE)
    validate_equals(pod_status, True, f"Verify {POD_PREFIX} pods are running")


def verify_ptp_notification_application_removed(ssh_connection):
    """Verify app is removed and all pods are terminated."""
    app_list = SystemApplicationListKeywords(ssh_connection)
    if app_list.is_app_present(APP_NAME):
        app_status = app_list.get_system_application_list().get_application(APP_NAME).get_status()
        validate_equals(app_status, "uploaded",
                        "App should be in uploaded state after removal")
    # Wait for pods to terminate
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    pod_keywords.wait_for_pods_to_be_deleted(namespace=NAMESPACE, timeout=120)


def verify_ptp_notification_application_after_upgrade(ssh_connection, ptp_hosts):
    """Verify app is still applied and pods Running after upgrade."""
    verify_ptp_notification_application_applied(ssh_connection, ptp_hosts)


def upload_and_apply_ptp_notification_application(ssh_connection, app_config, ptp_hosts):
    """Full install: assign labels, upload, override, apply, verify."""
    get_logger().log_info("Assigning ptp-notification labels to PTP hosts")
    assign_ptp_notification_labels(ssh_connection, ptp_hosts)
    get_logger().log_info("Uploading ptp-notification application")
    upload_ptp_notification_application(ssh_connection, app_config)
    get_logger().log_info("Applying helm override to disable v1 ptptracking")
    override_ptp_notification_application(ssh_connection)
    get_logger().log_info("Applying ptp-notification application")
    apply_ptp_notification_application(ssh_connection)
    get_logger().log_info("Verifying ptp-notification application is applied")
    verify_ptp_notification_application_applied(ssh_connection, ptp_hosts)


def remove_and_delete_ptp_notification_application(ssh_connection):
    """Full uninstall: remove app, verify pods gone, delete app, remove labels."""
    get_logger().log_info("Removing ptp-notification application")
    remove_ptp_notification_application(ssh_connection)
    get_logger().log_info("Verifying ptp-notification pods are terminated")
    verify_ptp_notification_application_removed(ssh_connection)
    get_logger().log_info("Deleting ptp-notification application")
    delete_ptp_notification_application(ssh_connection)
    get_logger().log_info("Removing ptp-notification labels from nodes")
    remove_ptp_notification_labels(ssh_connection)


@mark.p2
@mark.lab_has_ptp
def test_install_ptp_notification_app():
    """
    Install ptp-notification application.

    Test Steps:
        - Get list of PTP-configured hosts
        - Remove existing ptp-notification if present
        - Assign required labels to PTP hosts only
        - Upload ptp-notification application
        - Apply helm override (disable v1 ptptracking)
        - Apply ptp-notification application
        - Verify application status is 'applied'
        - Verify pods are running
    """
    ssh_connection, app_config = _get_ssh_and_config()

    get_logger().log_test_case_step("Get PTP-configured hosts")
    ptp_hosts = _get_ptp_hosts(ssh_connection)

    get_logger().log_test_case_step("Check if ptp-notification is already present")
    app_list = SystemApplicationListKeywords(ssh_connection)
    if app_list.is_app_present(APP_NAME):
        app_status = app_list.get_system_application_list().get_application(APP_NAME).get_status()
        if app_status == SystemApplicationStatusEnum.APPLIED.value:
            get_logger().log_info("ptp-notification already applied. Removing first.")
            remove_and_delete_ptp_notification_application(ssh_connection)
        else:
            get_logger().log_info("ptp-notification present but not applied. Deleting.")
            delete_ptp_notification_application(ssh_connection)

    get_logger().log_test_case_step("Upload and apply ptp-notification application")
    upload_and_apply_ptp_notification_application(ssh_connection, app_config, ptp_hosts)


@mark.p2
@mark.lab_has_ptp
def test_uninstall_ptp_notification_app():
    """
    Uninstall ptp-notification application.

    Test Steps:
        - Get list of PTP-configured hosts
        - Ensure ptp-notification is applied (install if not)
        - Remove ptp-notification application
        - Verify pods are terminated
        - Delete ptp-notification application
        - Remove labels from nodes
    """
    ssh_connection, app_config = _get_ssh_and_config()

    get_logger().log_test_case_step("Get PTP-configured hosts")
    ptp_hosts = _get_ptp_hosts(ssh_connection)

    get_logger().log_test_case_step("Ensure ptp-notification is applied before uninstall")
    app_list = SystemApplicationListKeywords(ssh_connection)
    if not app_list.is_app_present(APP_NAME):
        get_logger().log_info("ptp-notification not present. Installing first.")
        upload_and_apply_ptp_notification_application(ssh_connection, app_config, ptp_hosts)
    else:
        app_status = app_list.get_system_application_list().get_application(APP_NAME).get_status()
        if app_status != SystemApplicationStatusEnum.APPLIED.value:
            get_logger().log_info("ptp-notification not applied. Cleaning up and installing.")
            delete_ptp_notification_application(ssh_connection)
            upload_and_apply_ptp_notification_application(ssh_connection, app_config, ptp_hosts)

    get_logger().log_test_case_step("Remove and delete ptp-notification application")
    remove_and_delete_ptp_notification_application(ssh_connection)
