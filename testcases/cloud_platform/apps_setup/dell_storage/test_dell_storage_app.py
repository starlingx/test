from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_abort_keywords import SystemApplicationAbortKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.yaml_keywords import YamlKeywords


def setup_powerstore_dell(ssh_connection: SSHConnection):
    """Update the CSI-Powerstore helm chart user-overrides for dell-storage.
    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    get_logger().log_test_case_step("Update user-overrides for CSI-Powerstore chart")
    dell_storage_name = ConfigurationManager.get_app_config().get_dell_storage_app_name()
    chart_name = "csi-powerstore"
    namespace = "dell-storage"
    storage_config = ConfigurationManager.get_storage_config()
    yaml_file = "dell-storage-powerstoreOverrides.yaml"
    username = storage_config.get_credentials().get_user_name()
    password = storage_config.get_credentials().get_password()
    array_id = storage_config.get_storage_array_id()
    endpoint = storage_config.get_storage_array_endpoint()
    nas_name = storage_config.get_storage_array_nas_name()
    template_file = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{yaml_file}")
    replacement_dictionary = {"username": username, "password": password, "array_id": array_id, "endpoint": endpoint, "nas_name": nas_name}
    remote_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, yaml_file, "/home/sysadmin")
    get_logger().log_test_case_step("Create powerstoreOverrides.yaml file to use as user-overrides (ISCSI)")
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override(remote_yaml, dell_storage_name, chart_name, namespace)


@mark.p2
def test_pre_upgrade_check_dell_storage_app():
    """
    Check ceph health and ensure the dell-storage application is applied.
    Test Steps:
        - Verify ceph health status is healthy
        - Check if dell-storage application is present and applied
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dell_storage_name = ConfigurationManager.get_app_config().get_dell_storage_app_name()
    base_path = ConfigurationManager.get_app_config().get_base_application_path()
    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(active_ssh_connection).wait_for_ceph_health_status(expect_health_status=True)
    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
    if not app_list_keywords.is_app_present(dell_storage_name):
        get_logger().log_test_case_step("Upload dell-storage app.")
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(dell_storage_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{dell_storage_name}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)
        setup_powerstore_dell(active_ssh_connection)
        get_logger().log_test_case_step("Apply dell-storage app.")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=dell_storage_name)
    else:
        setup_powerstore_dell(active_ssh_connection)
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=dell_storage_name)

    show_output = SystemHelmOverrideKeywords(active_ssh_connection).get_system_helm_override_show(
        "dell-storage",  # app_name
        "csi-powerstore",  # chart_name
        "dell-storage",  # namespace
    )
    user_overrides = show_output.get_helm_override_show().get_user_overrides()
    validate_equals(
        user_overrides is not None and user_overrides.strip() not in ("", "None"),
        True,
        "dell-storage csi-powerstore user_overrides should not be empty",
    )


@mark.p2
def test_post_upgrade_check_dell_storage_app():
    """
    Verify ceph health and dell-storage application status after upgrade, then remove, apply, abort, and re-apply.
    Test Steps:
        - Verify ceph health status is healthy
        - Validate the dell-storage application is present and in applied state
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dell_storage_name = ConfigurationManager.get_app_config().get_dell_storage_app_name()
    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(active_ssh_connection).wait_for_ceph_health_status(expect_health_status=True)
    get_logger().log_test_case_step("Validate dell-storage app is applied.")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(dell_storage_name, "applied")
    show_output = SystemHelmOverrideKeywords(active_ssh_connection).get_system_helm_override_show(
        "dell-storage",  # app_name
        "csi-powerstore",  # chart_name
        "dell-storage",  # namespace
    )
    user_overrides = show_output.get_helm_override_show().get_user_overrides()
    validate_equals(
        user_overrides is not None and user_overrides.strip() not in ("", "None"),
        True,
        "dell-storage csi-powerstore user_overrides should not be empty",
    )

    get_logger().log_test_case_step("Remove dell-storage.")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(dell_storage_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Update user-overrides for CSI-Powerstore chart")
    setup_powerstore_dell(active_ssh_connection)

    get_logger().log_test_case_step("Apply dell-storage.")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=dell_storage_name, wait_for_applied=False)
    get_logger().log_test_case_step("Abort dell-storage.")
    SystemApplicationAbortKeywords(active_ssh_connection).system_application_abort(app_name=dell_storage_name)
    get_logger().log_test_case_step("Validate application status changed to apply-failed.")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(dell_storage_name, "apply-failed")
    get_logger().log_test_case_step("Apply dell-storage.")
