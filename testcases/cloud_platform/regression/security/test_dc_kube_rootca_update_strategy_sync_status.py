from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than_or_equal
from keywords.cloud_platform.dcmanager.dcmanager_kube_rootca_update_strategy_keywords import DcmanagerKubeRootcaUpdateStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object_filter import DcManagerSubcloudListObjectFilter
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p0
@mark.lab_is_distributed_cloud
def test_dc_kube_rootca_update_strategy_sync_status(request):
    """Test kube-rootca sync status with different certificate expiry dates.

    Verifies subcloud kube-rootca sync status changes based on certificate
    expiry date proximity to system controller. Tests that certificates
    expiring within 15 days cause out-of-sync status and raise alarm 500.200,
    while certificates with 365 days expiry remain in-sync.

    Steps:
        - Get at least 1 managed, online, and in-sync subcloud
        - Create strategy with 15 days expiry and apply
        - Verify subcloud kube-rootca_sync_status is out-of-sync
        - Verify alarm 500.200 is raised on subcloud
        - Delete strategy and wait for deletion to complete
        - Create strategy with 365 days expiry and apply
        - Verify subcloud kube-rootca_sync_status is in-sync
        - Delete strategy
    """

    def cleanup_strategy():
        """Clean up kube-rootca-update strategy.

        Waits for strategy to complete if in progress, then deletes it.
        Handles cases where strategy is already deleting.
        """
        get_logger().log_info("Cleaning up kube-rootca-update strategy")
        active_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
        strategy_keywords = DcmanagerKubeRootcaUpdateStrategyKeywords(active_controller_ssh)

        # Check if strategy exists
        try:
            strategy_keywords.get_dcmanager_kube_rootca_update_strategy_step_show()
            # Strategy exists, wait and delete
            strategy_keywords.wait_kube_upgrade(expected_status="complete", check_interval=60, timeout=3600)
            strategy_keywords.dcmanager_kube_rootca_update_strategy_delete()
        except Exception as e:
            get_logger().log_info(f"Strategy cleanup: {str(e)}")

    request.addfinalizer(cleanup_strategy)

    # Test setup
    active_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    strategy_keywords = DcmanagerKubeRootcaUpdateStrategyKeywords(active_controller_ssh)
    subcloud_list_keywords = DcManagerSubcloudListKeywords(active_controller_ssh)
    subcloud_show_keywords = DcManagerSubcloudShowKeywords(active_controller_ssh)

    get_logger().log_test_case_step("Get managed, online, and in-sync subcloud")
    subcloud_list_output = subcloud_list_keywords.get_dcmanager_subcloud_list()
    subclouds = subcloud_list_output.get_dcmanager_subcloud_list_objects_filtered(DcManagerSubcloudListObjectFilter.get_healthy_subcloud_filter())
    validate_greater_than_or_equal(len(subclouds), 1, "Test requires at least 1 managed, online, and in-sync subcloud")

    subcloud = subclouds[0].get_name()
    get_logger().log_info(f"Using subcloud: {subcloud}")
    subject = "C=CA ST=ON L=Ottawa O=company OU=sale CN=kubernetes"

    # Test with 15 days expiry - should cause out-of-sync
    expiry_15_days = strategy_keywords.get_future_date(15)

    get_logger().log_test_case_step(f"Create strategy with 15 days expiry: {expiry_15_days}")
    strategy_keywords.dcmanager_kube_rootca_update_strategy_create(expiry_date=expiry_15_days, subject=subject, force=True)

    get_logger().log_test_case_step("Apply strategy with 15 days expiry")
    strategy_keywords.dcmanager_kube_rootca_update_strategy_apply()

    get_logger().log_test_case_step(f"Verify {subcloud} kube-rootca_sync_status is out-of-sync")
    subcloud_show_output = subcloud_show_keywords.get_dcmanager_subcloud_show(subcloud)
    kube_rootca_sync = subcloud_show_output.get_dcmanager_subcloud_show_object().get_kube_rootca_sync_status()
    validate_equals(kube_rootca_sync, "out-of-sync", f"Subcloud {subcloud} kube-rootca_sync_status should be out-of-sync with 15 days expiry")

    get_logger().log_test_case_step(f"Verify alarm 500.200 exists on subcloud {subcloud}")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud)
    alarm_keywords = AlarmListKeywords(subcloud_ssh)
    alarms_output = alarm_keywords.get_alarm_list()
    alarms = alarms_output.get_alarms()
    cert_expiry_alarm = next((alarm for alarm in alarms if alarm.get_alarm_id() == "500.200" and "kubernetes-root-ca" in alarm.get_entity_id()), None)
    validate_equals(cert_expiry_alarm is not None, True, f"Alarm 500.200 for kubernetes-root-ca should exist on subcloud {subcloud}")
    if cert_expiry_alarm:
        get_logger().log_info(f"Alarm found: {cert_expiry_alarm.get_reason_text()}")

    get_logger().log_test_case_step("Delete strategy")
    strategy_keywords.dcmanager_kube_rootca_update_strategy_delete()

    # Wait for strategy to be fully deleted
    get_logger().log_info("Waiting for strategy to be fully deleted")
    if strategy_keywords.wait_for_strategy_deletion(timeout=300):
        get_logger().log_info("Strategy successfully deleted")
    else:
        get_logger().log_info("Strategy still exists after timeout, proceeding anyway")

    # Test with 365 days expiry - should be in-sync
    expiry_365_days = strategy_keywords.get_future_date(365)

    get_logger().log_test_case_step(f"Create strategy with 365 days expiry: {expiry_365_days}")
    strategy_keywords.dcmanager_kube_rootca_update_strategy_create(expiry_date=expiry_365_days, subject=subject, force=True)

    get_logger().log_test_case_step("Apply strategy with 365 days expiry")
    strategy_keywords.dcmanager_kube_rootca_update_strategy_apply()

    get_logger().log_test_case_step(f"Verify {subcloud} kube-rootca_sync_status is in-sync")
    subcloud_show_output = subcloud_show_keywords.get_dcmanager_subcloud_show(subcloud)
    kube_rootca_sync = subcloud_show_output.get_dcmanager_subcloud_show_object().get_kube_rootca_sync_status()
    validate_equals(kube_rootca_sync, "in-sync", f"Subcloud {subcloud} kube-rootca_sync_status should be in-sync with 365 days expiry")

    get_logger().log_test_case_step("Delete strategy")
    strategy_keywords.dcmanager_kube_rootca_update_strategy_delete()

    get_logger().log_test_case_step("Kube-rootca-update strategy sync status test completed successfully")
