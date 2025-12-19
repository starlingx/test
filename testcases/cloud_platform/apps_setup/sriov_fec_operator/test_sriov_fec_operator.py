from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


def _cleanup_sriov_fec_operator():
    """Clean up sriov-fec-operation."""

    # Setup Preconditions - Clear Application
    # Verify the Sriov FEC operator app is not present in the system
    app_config = ConfigurationManager.get_app_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    sriov_fec_name = app_config.get_sriov_fec_operator_app_name()
    get_logger().log_setup_step("Verify if sriov fec operator is previously installed or uploaded...")
    sriov_fec_applied = SystemApplicationApplyKeywords(ssh_connection).is_applied_or_failed(sriov_fec_name)
    if sriov_fec_applied is True:
        get_logger().log_setup_step("Removing and deleting sriov fec operator application...")
        sriov_fec_app_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(sriov_fec_name)
        validate_equals(sriov_fec_app_output, f"Application {sriov_fec_name} deleted.\n", "SRIOV FEC deletion validation")
    else:
        sriov_fec_uploaded = SystemApplicationUploadKeywords(ssh_connection).is_already_uploaded(sriov_fec_name)
        if sriov_fec_uploaded:
            get_logger().log_setup_step("Deleting sriov fec operator application...")
            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(sriov_fec_name)
            system_application_delete_input.set_force_deletion(False)
            sriov_fec_app_output = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
            validate_equals(sriov_fec_app_output, f"Application {sriov_fec_name} deleted.\n", "Application deletion message validation")
        else:
            get_logger().log_setup_step("sriov-fec-operator is not installed...")


@mark.p0
@mark.lab_has_sriov
def test_install_sriov_fec_operator():
    """
    Install (Upload and Apply) and check the application pods

    Setup:
    - Verify the Sriov FEC operator app is present in the system If it is installled, delete and remove sriov-fec-operator

    Raises:
        Exception: If application Sriov Fec operator failed to upload or apply
    """
    _cleanup_sriov_fec_operator()

    # Setup app configs and lab connection
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    sriov_fec_name = app_config.get_sriov_fec_operator_app_name()
    sriov_fec_file_path = f"{base_path}{sriov_fec_name}*.tgz"
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    # Step : Uploading sriov-fec-operator application
    get_logger().log_test_case_step("SRIOV FEC Operator not installed. Uploading .tgz file...")
    # Setups the upload input object
    system_application_upload_input = SystemApplicationUploadInput()
    system_application_upload_input.set_app_name(sriov_fec_name)
    system_application_upload_input.set_tar_file_path(sriov_fec_file_path)
    # Uploads the application file
    sriov_fec_app_output = SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
    sriov_fec_app_object = sriov_fec_app_output.get_system_application_object()
    # Verify if application was uploded
    validate_equals(sriov_fec_app_object.get_name(), sriov_fec_name, f"{sriov_fec_name} name validation")
    validate_equals(sriov_fec_app_object.get_status(), SystemApplicationStatusEnum.UPLOADED.value, "Application status validation")

    # Step : Applying sriov-fec-operator application
    get_logger().log_test_case_step("SRIOV FEC Operator uploaded. Applying application...")
    # Applies the app to the active controller
    sriov_fec_app_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(sriov_fec_name)
    # Verify if the application was applied
    sriov_fec_app_object = sriov_fec_app_output.get_system_application_object()
    validate_equals(sriov_fec_app_object.get_name(), sriov_fec_name, f"{sriov_fec_name} name validation")
    validate_equals(sriov_fec_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{sriov_fec_name} application status validation")

    # Step : Check sriov-fec-operator pods
    get_logger().log_test_case_step("check if pod is running")
    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_names = get_pod_obj.get_pods(namespace="sriov-fec-system").get_unique_pod_matching_prefix(starts_with="sriov")
    pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", "sriov-fec-system")
    validate_equals(pod_status, True, f"Verify {'sriov'} pods are running")


@mark.p0
@mark.lab_has_sriov
def test_uninstall_sriov_fec_operator():
    """
    Uninstall (Remove and Delete) sriov-fec-operator application

    Raises:
        Exception: If application Sriov Fec operator failed to remove or delete
    """

    # Setup app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    sriov_fec_name = app_config.get_sriov_fec_operator_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    # Verifies if the app is not present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(sriov_fec_name), True, f"The {sriov_fec_name} application should be uploaded/applied on the system")

    # Step : Removing  sriov-fec-operator application
    get_logger().log_test_case_step("SRIOV FEC Operator applied. Removing application...")
    # Setups the remove input object
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(sriov_fec_name)
    system_application_remove_input.set_force_removal(False)
    # Remove the appliacation
    sriov_fec_app_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)
    sriov_fec_app_object = sriov_fec_app_output.get_system_application_object()
    # Verify if the application was removed
    validate_equals(sriov_fec_app_object.get_name(), sriov_fec_name, f"{sriov_fec_name} name validation")
    validate_equals(sriov_fec_app_object.get_status(), SystemApplicationStatusEnum.UPLOADED.value, f"{sriov_fec_name} application status validation")

    # Step : Deleting  sriov-fec-operator application
    get_logger().log_test_case_step("SRIOV FEC Operator uploaded. Deleting application...")
    # Deletes the application
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(sriov_fec_name)
    system_application_delete_input.set_force_deletion(False)
    # Verify if the application was deleted
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(delete_msg, f"Application {sriov_fec_name} deleted.\n", "Application deletion message validation")
