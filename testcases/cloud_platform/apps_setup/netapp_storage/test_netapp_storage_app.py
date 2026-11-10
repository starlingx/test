"""Pre and post platform upgrade checks of the netapp-storage application on the ONTAP SAN Fibre Channel backend."""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_abort_keywords import SystemApplicationAbortKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from testcases.cloud_platform.apps_setup.netapp_storage.helper_netapp_storage import NETAPP_FC_CAPABILITY, TRIDENT_NAMESPACE, verify_netapp_integrity


@mark.p2
@mark.lab_has_netapp_fc
def test_pre_upgrade_check_netapp_storage_app():
    """
    Check the netapp-storage application is applied and the Fibre Channel backend is healthy before the upgrade.

    Test Steps:
        - Verify the netapp-storage application is present
        - Wait for an apply already in progress to finish
        - Apply netapp-storage if it is present but not in applied state
        - Verify the netapp-storage integrity: application applied, trident pods healthy
          and the ontap-san Fibre Channel backend reporting Success
        - Validate the netapp-storage application version matches the platform version
    """
    platform_version = CloudPlatformVersionManagerClass().get_sw_version().get_name()
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    netapp_storage_name = ConfigurationManager.get_app_config().get_netapp_storage_app_name()

    get_logger().log_test_case_step(f"Verify the {netapp_storage_name} application is present.")
    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
    validate_equals(app_list_keywords.is_app_present(netapp_storage_name), True, f"{netapp_storage_name} application is present")

    app_status = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(netapp_storage_name).get_system_application_object().get_status()
    if app_status == SystemApplicationStatusEnum.APPLYING.value:
        # 'system application-apply' is rejected while an apply is in progress, so let it finish first.
        get_logger().log_test_case_step(f"Wait for the in-progress {netapp_storage_name} apply to finish.")
        app_status = app_list_keywords.validate_app_status_in_list(netapp_storage_name, [SystemApplicationStatusEnum.APPLIED.value, SystemApplicationStatusEnum.APPLY_FAILED.value], timeout=1800, polling_sleep_time=15)
    if app_status != SystemApplicationStatusEnum.APPLIED.value:
        get_logger().log_test_case_step(f"Apply {netapp_storage_name} app.")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=netapp_storage_name, timeout=1800, wait_for_pods_namespace=TRIDENT_NAMESPACE)

    get_logger().log_test_case_step(f"Verify {netapp_storage_name} integrity for {NETAPP_FC_CAPABILITY}.")
    verify_netapp_integrity(active_ssh_connection, NETAPP_FC_CAPABILITY)

    get_logger().log_test_case_step(f"Validate the {netapp_storage_name} app version matches the platform version.")
    app_list_keywords.validate_app_version(netapp_storage_name, platform_version)


@mark.p2
@mark.lab_has_netapp_fc
def test_post_upgrade_check_netapp_storage_app():
    """
    Verify the netapp-storage application after the upgrade, then remove, apply, abort, and re-apply.

    Test Steps:
        - Verify the netapp-storage integrity: application applied, trident pods healthy
          and the ontap-san Fibre Channel backend reporting Success
        - Validate the netapp-storage application version matches the platform version
        - Remove the netapp-storage application using "system application-remove"
        - Apply the netapp-storage application without waiting for completion
        - Wait for the application to be in applying state
        - Abort the netapp-storage application using "system application-abort"
        - Validate the application status changed to apply-failed
        - Apply the netapp-storage application again to ensure it can be applied after aborting
        - Verify the netapp-storage integrity again
    """
    platform_version = CloudPlatformVersionManagerClass().get_sw_version().get_name()
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    netapp_storage_name = ConfigurationManager.get_app_config().get_netapp_storage_app_name()
    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)

    get_logger().log_test_case_step(f"Verify {netapp_storage_name} integrity for {NETAPP_FC_CAPABILITY}.")
    verify_netapp_integrity(active_ssh_connection, NETAPP_FC_CAPABILITY)

    get_logger().log_test_case_step(f"Validate the {netapp_storage_name} app version matches the platform version.")
    app_list_keywords.validate_app_version(netapp_storage_name, platform_version)

    get_logger().log_test_case_step(f"Remove {netapp_storage_name}.")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(netapp_storage_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step(f"Apply {netapp_storage_name}.")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=netapp_storage_name, wait_for_applied=False)

    get_logger().log_test_case_step(f"Wait for {netapp_storage_name} to be in applying state before the abort.")
    app_list_keywords.validate_app_status(netapp_storage_name, SystemApplicationStatusEnum.APPLYING.value, timeout=120, polling_sleep_time=1)

    get_logger().log_test_case_step(f"Abort {netapp_storage_name}.")
    SystemApplicationAbortKeywords(active_ssh_connection).system_application_abort(app_name=netapp_storage_name)

    get_logger().log_test_case_step("Validate application status changed to apply-failed.")
    app_list_keywords.validate_app_status(netapp_storage_name, SystemApplicationStatusEnum.APPLY_FAILED.value)

    get_logger().log_test_case_step(f"Apply {netapp_storage_name}.")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=netapp_storage_name, timeout=1800, wait_for_pods_namespace=TRIDENT_NAMESPACE)

    get_logger().log_test_case_step(f"Verify {netapp_storage_name} integrity for {NETAPP_FC_CAPABILITY}.")
    verify_netapp_integrity(active_ssh_connection, NETAPP_FC_CAPABILITY)
