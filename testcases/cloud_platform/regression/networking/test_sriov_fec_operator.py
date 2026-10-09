from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.networking.sriov_fec.sriov_fec_operator_keywords import SriovFecOperatorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


@mark.p0
@mark.lab_has_sriov
def test_sriov_fec_operator_install_uninstall(request: FixtureRequest) -> None:
    """Verify sriov-fec-operator application install and uninstall.

    Install the sriov-fec-operator application using separate upload and apply
    keywords, verifying the application status after each step, then uninstall
    it using separate remove and delete keywords, again verifying the status
    after each step.

    Preconditions:
        - Lab has SR-IOV capability

    Setup:
        - Clean up any previously installed/uploaded sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Upload the sriov-fec-operator application and verify status is uploaded
        2. Apply the sriov-fec-operator application and verify status is applied
        3. Verify the sriov-fec-operator pods reach the Running status
        4. Remove the sriov-fec-operator application and verify status is uploaded
        5. Delete the sriov-fec-operator application and verify the deletion message
        6. Verify the sriov-fec-operator pods are deleted

    Teardown:
        - Remove and delete sriov-fec-operator application if still present
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    sriov_fec_name = app_config.get_sriov_fec_operator_app_name()
    sriov_fec_file_path = f"{base_path}{sriov_fec_name}*.tgz"

    sriov_fec_operator_kw = SriovFecOperatorKeywords(ssh_connection)
    sriov_fec_operator_kw.cleanup_sriov_fec_operator_and_pods()

    def teardown():
        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    # Step 1: Upload the sriov-fec-operator application
    get_logger().log_test_case_step("Upload the sriov-fec-operator application and verify status is uploaded")
    system_application_upload_input = SystemApplicationUploadInput()
    system_application_upload_input.set_app_name(sriov_fec_name)
    system_application_upload_input.set_tar_file_path(sriov_fec_file_path)
    upload_output = SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
    upload_object = upload_output.get_system_application_object()
    validate_equals(upload_object.get_name(), sriov_fec_name, f"{sriov_fec_name} name validation after upload")
    validate_equals(upload_object.get_status(), SystemApplicationStatusEnum.UPLOADED.value, f"{sriov_fec_name} status validation after upload")

    # Step 2: Apply the sriov-fec-operator application
    get_logger().log_test_case_step("Apply the sriov-fec-operator application and verify status is applied")
    apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(sriov_fec_name)
    apply_object = apply_output.get_system_application_object()
    validate_equals(apply_object.get_name(), sriov_fec_name, f"{sriov_fec_name} name validation after apply")
    validate_equals(apply_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{sriov_fec_name} status validation after apply")

    # Step 3: Verify the sriov-fec-operator pods are running
    get_logger().log_test_case_step("Verify the sriov-fec-operator pods reach the Running status")
    pod_status = KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")
    validate_equals(pod_status, True, "sriov-fec-operator pods are running")

    # Step 4: Remove the sriov-fec-operator application
    get_logger().log_test_case_step("Remove the sriov-fec-operator application and verify status is uploaded")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(sriov_fec_name)
    system_application_remove_input.set_force_removal(False)
    remove_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)
    remove_object = remove_output.get_system_application_object()
    validate_equals(remove_object.get_name(), sriov_fec_name, f"{sriov_fec_name} name validation after remove")
    validate_equals(remove_object.get_status(), SystemApplicationStatusEnum.UPLOADED.value, f"{sriov_fec_name} status validation after remove")

    # Step 5: Delete the sriov-fec-operator application
    get_logger().log_test_case_step("Delete the sriov-fec-operator application and verify the deletion message")
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(sriov_fec_name)
    system_application_delete_input.set_force_deletion(False)
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(delete_msg, f"Application {sriov_fec_name} deleted.\n", f"{sriov_fec_name} deletion message validation")

    # Step 6: Verify the sriov-fec-operator pods are deleted
    get_logger().log_test_case_step("Verify the sriov-fec-operator pods are deleted")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_be_deleted(namespace="sriov-fec-system")
