from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from framework.web.webdriver_core import WebDriverCore
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object_filter import DcManagerSubcloudListObjectFilter
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.certificate.system_certificate_keywords import SystemCertificateKeywords
from web_pages.horizon.admin.dc.horizon_dc_subcloud_page import HorizonDCSubcloudPage
from web_pages.horizon.login.horizon_login_page import HorizonLoginPage


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
