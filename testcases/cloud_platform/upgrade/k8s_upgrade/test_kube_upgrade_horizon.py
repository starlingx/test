from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.web.webdriver_core import WebDriverCore
from keywords.cloud_platform.dcmanager.dcmanager_kube_deploy_strategy_keywords import DcmanagerKubeStrategyKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from web_pages.horizon.admin.dc.horizon_dc_orchestration_page import HorizonDCOrchestrationPage
from web_pages.horizon.login.horizon_login_page import HorizonLoginPage


@mark.p2
@mark.lab_has_subcloud
def test_dc_subcloud_kube_upgrade_horizon(request: FixtureRequest):
    """Test Kubernetes upgrade orchestration via Horizon UI.

    Test Steps:
        - Login to Horizon as admin
        - Navigate to DC Orchestration page
        - Create a Kubernetes upgrade strategy
        - Apply the strategy
        - Wait for strategy completion via dcmanager CLI
        - Delete the strategy via Horizon
    """
    k8s_config = ConfigurationManager.get_k8s_config()
    target_version = k8s_config.get_k8_target_version()
    subcloud_name = k8s_config.get_subcloud_name()
    subcloud_group = k8s_config.get_subcloud_group()

    driver = WebDriverCore()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcm_kube_keywords = DcmanagerKubeStrategyKeywords(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Closing Horizon browser")
        driver.close()

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Login to Horizon")
    login_page = HorizonLoginPage(driver)
    login_page.navigate_to_login_page()
    login_page.login_as_admin()

    get_logger().log_test_case_step("Navigate to DC Orchestration page")
    orch_page = HorizonDCOrchestrationPage(driver)
    orch_page.navigate_to_dc_orchestration_page()

    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy to version {target_version}")
    create_kwargs = {"to_version": target_version}
    if subcloud_name != "None":
        create_kwargs["subcloud"] = subcloud_name
    elif subcloud_group != "None" and subcloud_group != "Default":
        create_kwargs["subcloud_group"] = subcloud_group
    orch_page.create_kubernetes_strategy(**create_kwargs)

    get_logger().log_test_case_step("Apply the Kubernetes upgrade strategy")
    orch_page.navigate_to_dc_orchestration_page()
    orch_page.apply_strategy()

    get_logger().log_test_case_step("Wait for strategy completion via dcmanager CLI")
    dcm_kube_keywords.wait_kube_upgrade(expected_status="complete", timeout=3600)

    get_logger().log_test_case_step("Delete the Kubernetes upgrade strategy")
    orch_page.navigate_to_dc_orchestration_page()
    orch_page.delete_strategy()
