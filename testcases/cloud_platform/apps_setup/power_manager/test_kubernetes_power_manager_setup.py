from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

# Namespace where the kubernetes-power-manager pods are deployed
POWER_MANAGER_NAMESPACE = "intel-power"
# Label required on the hosts for the kubernetes-power-manager application
POWER_MANAGEMENT_LABEL = "power-management=enabled"
# Label key used when removing the label from the hosts
POWER_MANAGEMENT_LABEL_KEY = "power-management"


def _cleanup_power_manager_operator():
    """Clean up the Power Manager application and its host label if present.

    Removes and deletes the kubernetes-power-manager application, handling both
    the applied and uploaded states, and removes the power-management label from
    any controller that still has it.
    """
    app_config = ConfigurationManager.get_app_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    power_manager_name = app_config.get_power_manager_app_name()

    get_logger().log_setup_step("Verify if power manager is previously installed or uploaded...")
    SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(power_manager_name)

    get_logger().log_setup_step("Verify if the power-management label is present on any node...")
    host_label_keywords = SystemHostLabelKeywords(ssh_connection)
    hosts = SystemHostListKeywords(ssh_connection).get_system_host_list().get_hosts()
    for host in hosts:
        host_name = host.get_host_name()
        label_value = host_label_keywords.get_system_host_label_list(host_name).get_label_value(POWER_MANAGEMENT_LABEL_KEY)
        if label_value is not None:
            get_logger().log_setup_step(f"Removing power-management label from {host_name}...")
            host_label_keywords.system_host_label_remove(host_name, POWER_MANAGEMENT_LABEL_KEY)


@mark.p2
def test_install_power_manager():
    """
    Install (Upload and Apply) Application Power Manager with its dependency Node Feature Discovery

    Raises:
        Exception: If application node-feature-discovery or kubernetes-power-manager failed to upload or apply
    """
    # Setup app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    power_manager_name = app_config.get_power_manager_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    # Cleanup: ensure the Power Manager application is not present before starting
    _cleanup_power_manager_operator()

    # Step 1: Install Node Feature Discovery first

    # Verify if NFD is already installed (applied)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    nfd_installed = system_applications.is_in_application_list(nfd_name) and system_applications.get_application(nfd_name).get_status() == SystemApplicationStatusEnum.APPLIED.value

    # If NFD is not already installed, ensure it is uploaded and then apply it
    if not nfd_installed:
        # If NFD is not uploaded yet, upload it
        if not system_applications.is_in_application_list(nfd_name):
            # Setup the upload input object for NFD
            nfd_upload_input = SystemApplicationUploadInput()
            nfd_upload_input.set_app_name(nfd_name)
            nfd_upload_input.set_tar_file_path(f"{base_path}{nfd_name}*.tgz")

            # Upload the NFD app file and verify it
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(nfd_upload_input)
            system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
            nfd_app_status = system_applications.get_application(nfd_name).get_status()
            validate_equals(nfd_app_status, SystemApplicationStatusEnum.UPLOADED.value, f"{nfd_name} upload status validation")

        # Apply the NFD app to the active controller and verify it was applied
        nfd_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(nfd_name)
        nfd_app_object = nfd_apply_output.get_system_application_object()
        validate_not_equals(nfd_app_object, None, "NFD application object should not be None")
        validate_equals(nfd_app_object.get_name(), nfd_name, "NFD application name validation")
        validate_equals(nfd_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "NFD application status validation")

    # Step 2: Assign the power-management=enabled label to all nodes

    hosts = SystemHostListKeywords(ssh_connection).get_system_host_list().get_hosts()
    for host in hosts:
        SystemHostLabelKeywords(ssh_connection).system_host_label_assign(host.get_host_name(), POWER_MANAGEMENT_LABEL, overwrite=True)

    # Step 3: Install Power Manager

    # Setup the upload input object for Power Manager
    power_manager_upload_input = SystemApplicationUploadInput()
    power_manager_upload_input.set_app_name(power_manager_name)
    power_manager_upload_input.set_tar_file_path(f"{base_path}{power_manager_name}*.tgz")

    # Upload the Power Manager app file and verify it
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(power_manager_upload_input)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    power_manager_app_status = system_applications.get_application(power_manager_name).get_status()
    validate_equals(power_manager_app_status, SystemApplicationStatusEnum.UPLOADED.value, f"{power_manager_name} upload status validation")

    # Apply the Power Manager app to the active controller
    power_manager_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(power_manager_name)

    # Verify the Power Manager app was applied
    power_manager_app_object = power_manager_apply_output.get_system_application_object()
    validate_not_equals(power_manager_app_object, None, "Power Manager application object should not be None")
    validate_equals(power_manager_app_object.get_name(), power_manager_name, "Power Manager application name validation")
    validate_equals(power_manager_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Power Manager application status validation")

    # Verify the Power Manager pods are up and running
    all_pods_running = KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace=POWER_MANAGER_NAMESPACE)
    validate_equals(all_pods_running, True, f"Power Manager pods should be running in namespace {POWER_MANAGER_NAMESPACE}")


@mark.p2
def test_uninstall_power_manager():
    """
    Uninstall (Remove and Delete) Application Power Manager and its dependency Node Feature Discovery

    Raises:
        Exception: If application Power Manager or Node Feature Discovery failed to remove or delete
    """
    # Setup app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    power_manager_name = app_config.get_power_manager_app_name()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    # Step 1: Uninstall Power Manager first (since it depends on NFD)

    # Verify if the Power Manager app is present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    if system_applications.is_in_application_list(power_manager_name):
        # Remove the Power Manager application
        power_manager_status = system_applications.get_application(power_manager_name).get_status()
        power_manager_remove_input = SystemApplicationRemoveInput()
        power_manager_remove_input.set_app_name(power_manager_name)
        power_manager_remove_input.set_force_removal(False)
        power_manager_remove_input.set_timeout_in_seconds(90)
        if power_manager_status == SystemApplicationStatusEnum.APPLIED.value:
            power_manager_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(power_manager_remove_input)
            validate_equals(power_manager_output.get_system_application_object().get_status(), SystemApplicationStatusEnum.UPLOADED.value, "Power Manager removal status validation")

        # Delete the Power Manager application
        power_manager_delete_input = SystemApplicationDeleteInput()
        power_manager_delete_input.set_app_name(power_manager_name)
        power_manager_delete_input.set_force_deletion(False)
        power_manager_delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(power_manager_delete_input)
        validate_equals(power_manager_delete_msg, f"Application {power_manager_name} deleted.\n", "Power Manager deletion message validation")

    # Step 2: Remove the power-management label from all nodes

    hosts = SystemHostListKeywords(ssh_connection).get_system_host_list().get_hosts()
    for host in hosts:
        SystemHostLabelKeywords(ssh_connection).system_host_label_remove(host.get_host_name(), POWER_MANAGEMENT_LABEL_KEY)

    # Step 3: Uninstall Node Feature Discovery

    # Verify if the NFD app is present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    if system_applications.is_in_application_list(nfd_name):
        # Remove the NFD application
        nfd_app_status = system_applications.get_application(nfd_name).get_status()
        nfd_remove_input = SystemApplicationRemoveInput()
        nfd_remove_input.set_app_name(nfd_name)
        nfd_remove_input.set_force_removal(False)
        nfd_remove_input.set_timeout_in_seconds(90)
        if nfd_app_status == SystemApplicationStatusEnum.APPLIED.value:
            nfd_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(nfd_remove_input)
            validate_equals(nfd_output.get_system_application_object().get_status(), SystemApplicationStatusEnum.UPLOADED.value, "NFD removal status validation")

        # Delete the NFD application
        nfd_delete_input = SystemApplicationDeleteInput()
        nfd_delete_input.set_app_name(nfd_name)
        nfd_delete_input.set_force_deletion(False)
        nfd_delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(nfd_delete_input)
        validate_equals(nfd_delete_msg, f"Application {nfd_name} deleted.\n", "NFD deletion message validation")
