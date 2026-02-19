import time

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than_or_equal, validate_str_contains
from framework.web.webdriver_core import WebDriverCore
from keywords.cloud_platform.dcmanager.dcmanager_kube_rootca_update_strategy_keywords import DcmanagerKubeRootcaUpdateStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object_filter import DcManagerSubcloudListObjectFilter
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_rootca_update_strategy_keywords import SwManagerKubeRootcaUpdateStrategyKeywords
from keywords.cloud_platform.system.certificate.system_certificate_keywords import SystemCertificateKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.kube_rootca.system_kube_rootca_update_keywords import SystemKubeRootcaUpdateKeywords
from web_pages.horizon.admin.dc.horizon_dc_subcloud_page import HorizonDCSubcloudPage
from web_pages.horizon.login.horizon_login_page import HorizonLoginPage


@mark.p1
def test_k8s_root_ca_update(request):
    """Test Kubernetes Root CA certificate update procedure.

    Steps:
        - Start update and generate certificate
        - Update all hosts through trust-both-cas phase
        - Update pods trust-both-cas
        - Update all hosts through update-certs phase
        - Update all hosts through trust-new-ca phase
        - Update pods trust-new-ca
        - Complete update
    """

    def cleanup_kube_rootca_update():
        get_logger().log_test_case_step("Kube rootca update test completed")

    request.addfinalizer(cleanup_kube_rootca_update)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kube_rootca = SystemKubeRootcaUpdateKeywords(ssh_connection)
    system_hosts = SystemHostListKeywords(ssh_connection)

    get_logger().log_test_case_step("Starting kube rootca update")
    update_output = kube_rootca.kube_rootca_update_start(force=True)
    validate_equals(update_output.get_kube_rootca_update().is_update_started(), True, "Update should start")

    get_logger().log_test_case_step("Generating new certificate")
    kube_rootca.kube_rootca_update_generate_cert("2031-08-25", "C=CA ST=ON L=Ottawa O=company OU=sale CN=kubernetes")
    validate_equals(kube_rootca.wait_for_update_state("update-new-rootca-cert-generated", 60), True, "Certificate should generate")

    hosts_output = system_hosts.get_system_host_list()
    all_hosts = hosts_output.get_controllers()
    try:
        all_hosts += hosts_output.get_workers()
    except Exception:
        pass

    for host in all_hosts:
        hostname = host.get_host_name()
        get_logger().log_test_case_step(f"Updating {hostname} trust-both-cas")
        kube_rootca.kube_rootca_host_update(hostname, "trust-both-cas")
        validate_equals(kube_rootca.wait_for_host_update_state(hostname, "updated-host-trust-both-cas", 600), True, f"{hostname} should update")

    kube_rootca.kube_rootca_pods_update("trust-both-cas")
    validate_equals(kube_rootca.wait_for_update_state("updated-pods-trust-both-cas", 3600), True, "Pods should update trust-both-cas")

    for host in all_hosts:
        hostname = host.get_host_name()
        get_logger().log_test_case_step(f"Updating {hostname} update-certs")
        kube_rootca.kube_rootca_host_update(hostname, "update-certs")
        validate_equals(kube_rootca.wait_for_host_update_state(hostname, "updated-host-update-certs", 600), True, f"{hostname} should update certs")

    for host in all_hosts:
        hostname = host.get_host_name()
        get_logger().log_test_case_step(f"Updating {hostname} trust-new-ca")
        kube_rootca.kube_rootca_host_update(hostname, "trust-new-ca")
        validate_equals(kube_rootca.wait_for_host_update_state(hostname, "updated-host-trust-new-ca", 600), True, f"{hostname} should trust new ca")

    kube_rootca.kube_rootca_pods_update("trust-new-ca")
    validate_equals(kube_rootca.wait_for_update_state("updated-pods-trust-new-ca", 3600), True, "Pods should trust new ca")

    get_logger().log_test_case_step("Completing kube rootca update")
    complete_output = kube_rootca.kube_rootca_update_complete()
    validate_equals(complete_output.get_kube_rootca_update().is_update_completed(), True, "Update should complete")
    get_logger().log_test_case_step("Kubernetes Root CA update completed successfully")


@mark.p1
def test_kubernetes_root_ca_is_self_signed():
    """Verify kubernetes-root-ca certificate is system-generated and self-signed.

    Steps:
        - Run system certificate-list
        - Find kubernetes-root-ca certificate
        - Verify issuer is CN=starlingx
        - Verify subject equals issuer (self-signed)
    """
    get_logger().log_test_case_step("Starting kubernetes-root-ca certificate verification test")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    cert_keywords = SystemCertificateKeywords(ssh_connection)

    get_logger().log_test_case_step("Retrieving system certificate list")
    cert_list_output = cert_keywords.certificate_list()

    get_logger().log_test_case_step("Finding kubernetes-root-ca certificate")
    kube_rootca_cert = cert_list_output.get_certificate_by_name("kubernetes-root-ca")

    validate_str_contains(kube_rootca_cert.get_issuer(), "CN=starlingx", "Issuer should be CN=starlingx")
    validate_equals(kube_rootca_cert.get_subject(), kube_rootca_cert.get_issuer(), "Subject should equal issuer (self-signed)")

    get_logger().log_info("kubernetes-root-ca certificate verification completed")


@mark.p1
@mark.lab_has_subcloud
def test_dc_subcloud_kube_rootca_sync_status(request):
    """Verify subcloud kube-rootca sync status is in-sync in DC deployment.

    Steps:
        - Connect to system controller
        - Get first healthy subcloud (online, managed, complete)
        - Run dcmanager subcloud show for the subcloud
        - Verify kube-rootca_sync_status is 'in-sync'
        - Login to Horizon and verify same status in UI
    """
    get_logger().log_test_case_step("Starting DC subcloud kube-rootca sync status verification")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcmanager_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    dcmanager_show_keywords = DcManagerSubcloudShowKeywords(ssh_connection)

    healthy_filter = DcManagerSubcloudListObjectFilter.get_healthy_subcloud_filter()
    subcloud_list = dcmanager_list_keywords.get_dcmanager_subcloud_list()
    healthy_subclouds = subcloud_list.get_dcmanager_subcloud_list_objects_filtered(healthy_filter)

    validate_equals(len(healthy_subclouds) > 0, True, "At least one healthy subcloud should exist")
    subcloud_name = healthy_subclouds[0].get_name()

    get_logger().log_test_case_step(f"Checking kube-rootca sync status for {subcloud_name}")
    subcloud_show = dcmanager_show_keywords.get_dcmanager_subcloud_show(subcloud_name)
    subcloud_obj = subcloud_show.get_dcmanager_subcloud_show_object()

    validate_equals(subcloud_obj.get_kube_rootca_sync_status(), "in-sync", f"Subcloud {subcloud_name} kube-rootca sync status should be in-sync")

    get_logger().log_info(f"Subcloud {subcloud_name} kube-rootca sync status verification completed")

    driver = WebDriverCore()

    def cleanup_horizon():
        get_logger().log_teardown_step("Closing Horizon browser")
        driver.close()

    request.addfinalizer(cleanup_horizon)

    get_logger().log_test_case_step("Verifying kube-rootca sync status in Horizon")
    login_page = HorizonLoginPage(driver)
    login_page.navigate_to_login_page()
    login_page.login_as_admin()

    dc_subcloud_page = HorizonDCSubcloudPage(driver)
    dc_subcloud_page.navigate_to_dc_subcloud_page()
    dc_subcloud_page.expand_subcloud(subcloud_name)

    kube_rootca_status = dc_subcloud_page.get_kube_rootca_sync_status(subcloud_name)
    validate_equals(kube_rootca_status, "in-sync", f"Horizon should show {subcloud_name} kube-rootca sync status as in-sync")

    get_logger().log_info(f"Horizon verification completed for {subcloud_name}")


@mark.p1
def test_apply_kube_rootca_update_strategy(request):
    """Test sw-manager orchestrated kube-rootca-update strategy.

    This test creates, applies, and validates a kube-rootca-update strategy
    using sw-manager orchestration.

    Steps:
        - Create kube-rootca-update strategy with certificate parameters
        - Verify strategy reaches ready-to-apply state
        - Apply strategy and wait for completion
        - Verify strategy reaches applied state
        - Delete strategy in cleanup
    """

    def cleanup_strategy():
        """Clean up kube-rootca-update strategy after test."""
        get_logger().log_info("Cleaning up kube-rootca-update strategy")
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        strategy_keywords = SwManagerKubeRootcaUpdateStrategyKeywords(ssh_connection)
        strategy_keywords.delete_kube_rootca_update_strategy()

    request.addfinalizer(cleanup_strategy)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    strategy_keywords = SwManagerKubeRootcaUpdateStrategyKeywords(ssh_connection)

    get_logger().log_test_case_step("Creating kube-rootca-update strategy")
    strategy = strategy_keywords.create_kube_rootca_update_strategy(expiry_date="2031-08-25", subject="C=CA ST=ON L=Ottawa O=company OU=sale CN=kubernetes")
    validate_equals(strategy.is_ready_to_apply(), True, "Strategy should reach ready-to-apply state")

    get_logger().log_test_case_step("Applying kube-rootca-update strategy")
    applied_strategy = strategy_keywords.apply_kube_rootca_update_strategy(timeout=7200)
    validate_equals(applied_strategy.is_applied(), True, "Strategy should reach applied state")

    get_logger().log_test_case_step("Kube-rootca-update strategy completed successfully")


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

        # Check if strategy exists
        output = active_controller_ssh.send("source /etc/platform/openrc;dcmanager kube-rootca-update-strategy show")
        if active_controller_ssh.get_return_code() == 0:
            strategy_keywords = DcmanagerKubeRootcaUpdateStrategyKeywords(active_controller_ssh)
            # Only wait if strategy is not already deleting or deleted
            if "deleting" not in "\n".join(output).lower():
                try:
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
    expiry_15_days = active_controller_ssh.send("date +'%Y-%m-%d' --date='15 days'")[0].strip()

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
    timeout = 300
    start_time = time.time()
    while time.time() - start_time < timeout:
        active_controller_ssh.send("source /etc/platform/openrc;dcmanager kube-rootca-update-strategy show")
        if active_controller_ssh.get_return_code() != 0:
            get_logger().log_info("Strategy successfully deleted")
            break
        time.sleep(5)
    else:
        get_logger().log_info("Strategy still exists after timeout, proceeding anyway")

    # Test with 365 days expiry - should be in-sync
    expiry_365_days = active_controller_ssh.send("date +'%Y-%m-%d' --date='365 days'")[0].strip()

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
