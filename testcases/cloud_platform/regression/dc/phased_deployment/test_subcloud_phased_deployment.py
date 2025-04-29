import time

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


def get_undeployed_subcloud_name(ssh_connection: SSHConnection) -> str:
    """Function get undeployed subcloud name

    function to get undeployed subcloud name if no undeployed
    subcloud found then delete the deployed one and return

    Args:
        ssh_connection (SSHConnection): SSH connection object.

    Returns:
        str: subcloudname
    """
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)

    subcloud_name = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_undeployed_subcloud_name()
    if subcloud_name is None:
        get_logger().log_info("No Undeployed Subcloud found deleting existing one")
        # Gets the lowest subcloud (the subcloud with the lowest id).
        get_logger().log_info("Obtaining subcloud with the lowest ID.")
        lowest_subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
        get_logger().log_info(f"Subcloud with the lowest ID obtained: ID={lowest_subcloud.get_id()}, Name={lowest_subcloud.get_name()}, Management state={lowest_subcloud.get_management()}")
        subcloud_name = lowest_subcloud.get_name()
        dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(ssh_connection)
        # poweroff the subcloud.
        get_logger().log_test_case_step(f"Poweroff subcloud={subcloud_name}.")
        dcm_sc_manager_kw.set_subcloud_poweroff(subcloud_name)
        # delete the subcloud.
        dcm_sc_del_kw = DcManagerSubcloudDeleteKeywords(ssh_connection)
        dcm_sc_del_kw.dcmanager_subcloud_delete(subcloud_name)

    return subcloud_name


@mark.p0
@mark.lab_has_min_2_subclouds
def test_phased_deployment(request):
    """Test Phased deployment steps for subcloud deployment.

    Test Steps:
        - log onto system controller
        - get the ssh connection to the active controller
        - check first to see if there is an undeployed subcloud if yes run test
        - If we don't have a subcloud that is undeployed, remove it and then run the test.
        - execute the phased deployment create
        - execute the phased deployment install
        - execute the phased deployment bootstrap
        - execute the phased deployment config
        - execute the phased deployment complete
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = get_undeployed_subcloud_name(ssh_connection)
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


@mark.p0
@mark.lab_has_min_2_subclouds
def test_subcloud_deploy_abort_resume(request):
    """Test Phased deployment steps for subcloud deployment.

    Test Steps:
        - log onto system controller
        - get the ssh connection to the active controller
        - check first to see if there is an undeployed subcloud if yes run test
        - If we don't have a subcloud that is undeployed, remove it and then run the test.
        - execute the phased deployment create
        - execute the phased deployment install
        - execute the phased deployment bootstrap
        - execute the phased deployment abort in some between 10 to 15 mins
        - execute the phased deployment resume
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = get_undeployed_subcloud_name(ssh_connection)
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)
    # dcmanager subcloud deploy create
    get_logger().log_info(f"dcmanager subcloud deploy create {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_create(subcloud_name)

    # dcmanager subcloud deploy install
    get_logger().log_info(f"dcmanager subcloud deploy install {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_install(subcloud_name)

    # dcmanager subcloud deploy bootstrap
    get_logger().log_info(f"dcmanager subcloud deploy bootstrap {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_bootstrap(subcloud_name, wait_for_status=False)
    # sleep 10 mins for bootstrap to proccess
    # TODO: Find a better way than random sleep , EX tail log for x number of line
    sleep_time = 600
    get_logger().log_info(f"Sleeping for {sleep_time/60} Minutes.")
    time.sleep(sleep_time)
    # dcmanager subcloud deploy bootstrap
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_abort(subcloud_name)
    get_logger().log_info(f"dcmanager subcloud deploy abort {subcloud_name}.")
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    dcm_sc_list_kw.validate_subcloud_status(subcloud_name, "bootstrap-aborted")
    # dcmanager subcloud deploy resume
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_resume(subcloud_name)
