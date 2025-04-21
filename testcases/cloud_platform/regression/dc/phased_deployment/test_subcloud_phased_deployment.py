from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p0
@mark.lab_has_min_2_subclouds
def test_phased_deployment(request):
    """Test Phased deployment steps for subcloud deployment.

    Test Steps:
        - log onto system controller
        - get the ssh connection to the active controller
        - execute the phased deployment create
        - execute the phased deployment install
        - execute the phased deployment bootstrap
        - execute the phased deployment config
        - execute the phased deployment complete
        - delete the subcloud
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    subcloud_name = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_undeployed_subcloud_name(None)
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)
    # dcmanager subcloud deploy create
    get_logger().log_info(f"dcmanager subcloud deploy create {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_create(subcloud_name)

    # dcmanager subcloud deploy install
    get_logger().log_info(f"dcmanager subcloud deploy install {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_install(subcloud_name)

    # dcmanager subcloud deploy bootstrap
    get_logger().log_info(f"dcmanager subcloud deploy bootstrap {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_bootstrap(subcloud_name)

    # dcmanager subcloud deploy config
    get_logger().log_info(f"dcmanager subcloud deploy config {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_config(subcloud_name)

    def teardown():
        get_logger().log_info("Phased Deployment Teardown")
        dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(ssh_connection)
        # poweroff the subcloud.
        get_logger().log_test_case_step(f"Poweroff subcloud={subcloud_name}.")
        dcm_sc_manager_kw.set_subcloud_poweroff(subcloud_name)
        # delete the subcloud.
        dcm_sc_del_kw = DcManagerSubcloudDeleteKeywords(ssh_connection)
        dcm_sc_del_kw.dcmanager_subcloud_delete(subcloud_name)

    request.addfinalizer(teardown)
