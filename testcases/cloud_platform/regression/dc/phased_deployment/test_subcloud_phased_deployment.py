import os
import time

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.kpi.time_kpi import TimeKPI
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords, pick_subcloud_with_fallback
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.yaml.deployment_assets_yaml import DeploymentAssetsHandler
from keywords.files.file_keywords import FileKeywords


def _remove_subcloud(ssh_connection: SSHConnection, subcloud_name: str) -> None:
    """Power off, unmanage, and delete a subcloud from a system controller.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller that owns the subcloud.
        subcloud_name (str): Subcloud to remove.
    """
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(ssh_connection)

    get_logger().log_setup_step(f"Power off subcloud '{subcloud_name}'")
    dcm_sc_manager_kw.set_subcloud_poweroff(subcloud_name)

    subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    if subcloud.get_management() == "managed":
        get_logger().log_setup_step(f"Unmanage subcloud '{subcloud_name}'")
        dcm_sc_manage_output = dcm_sc_manager_kw.get_dcmanager_subcloud_unmanage(subcloud_name, timeout=10)
        get_logger().log_info(f"Management state changed to {dcm_sc_manage_output.get_dcmanager_subcloud_manage_object().get_management()}")

    get_logger().log_setup_step(f"Delete subcloud '{subcloud_name}'")
    DcManagerSubcloudDeleteKeywords(ssh_connection).dcmanager_subcloud_delete(subcloud_name)


def get_undeployed_subcloud_name() -> str:
    """Get an undeployed subcloud name, checking both system controllers.

    Uses pick_undeployed_with_fallback to find a config subcloud not deployed on
    either system controller. If all are deployed, picks one via
    pick_subcloud_with_fallback and removes it.

    Returns:
        str: Subcloud name ready for deployment on the primary system controller.
    """
    subcloud_name = SubcloudPickerKeywords.pick_undeployed_with_fallback()
    if subcloud_name is not None:
        return subcloud_name

    get_logger().log_info("All config subclouds are deployed, removing one to free it")
    owner_ssh, result = pick_subcloud_with_fallback(present_in_config=True)
    subcloud_name = result.get_name()
    _remove_subcloud(owner_ssh, subcloud_name)
    return subcloud_name


@mark.p0
@mark.lab_has_subcloud
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
        - execute the subcloud manage
    """
    primary_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = get_undeployed_subcloud_name()
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(primary_ssh)
    dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(primary_ssh)

    # dcmanager subcloud deploy create
    time_kpi_start_create = TimeKPI(time.time())
    get_logger().log_info(f"dcmanager subcloud deploy create {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_create(subcloud_name)
    time_kpi_start_create.log_elapsed_time(time.time(), "time taken subcloud deploy create")

    # dcmanager subcloud deploy install
    time_kpi_start_install = TimeKPI(time.time())
    get_logger().log_info(f"dcmanager subcloud deploy install {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_install(subcloud_name)
    time_kpi_start_install.log_elapsed_time(time.time(), "time taken subcloud deploy install")

    # dcmanager subcloud deploy bootstrap
    time_kpi_start_bootstrap = TimeKPI(time.time())
    get_logger().log_info(f"dcmanager subcloud deploy bootstrap {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_bootstrap(subcloud_name)
    time_kpi_start_bootstrap.log_elapsed_time(time.time(), "time taken subcloud deploy bootstrap")

    # dcmanager subcloud deploy config
    time_kpi_start_config = TimeKPI(time.time())
    get_logger().log_info(f"dcmanager subcloud deploy config {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_config(subcloud_name)
    time_kpi_start_config.log_elapsed_time(time.time(), "time taken subcloud deploy config")

    # dcmanager subcloud manage
    get_logger().log_info(f"dcmanager subcloud manage {subcloud_name}.")
    dcmanager_subcloud_manage_output = dcm_sc_manager_kw.get_dcmanager_subcloud_manage(subcloud_name, timeout=60)
    manage_status = dcmanager_subcloud_manage_output.get_dcmanager_subcloud_manage_object().get_management()
    get_logger().log_info(f"The management state of the subcloud {subcloud_name} is {manage_status}")

@mark.p0
@mark.lab_has_subcloud
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
        - execute the subcloud manage
    """
    primary_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = get_undeployed_subcloud_name()
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(primary_ssh)
    dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(primary_ssh)

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
    # dcmanager subcloud deploy abort
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_abort(subcloud_name)
    get_logger().log_info(f"dcmanager subcloud deploy abort {subcloud_name}.")
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(primary_ssh)
    dcm_sc_list_kw.validate_subcloud_status(subcloud_name, "bootstrap-aborted")
    # dcmanager subcloud deploy resume
    time_kpi_start_resume = TimeKPI(time.time())
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_resume(subcloud_name)
    time_kpi_start_resume.log_elapsed_time(time.time(), "time taken subcloud deploy resume")

    # dcmanager subcloud manage
    get_logger().log_info(f"dcmanager subcloud manage {subcloud_name}.")
    dcmanager_subcloud_manage_output = dcm_sc_manager_kw.get_dcmanager_subcloud_manage(subcloud_name, timeout=60)
    manage_status = dcmanager_subcloud_manage_output.get_dcmanager_subcloud_manage_object().get_management()
    get_logger().log_info(f"The management state of the subcloud {subcloud_name} is {manage_status}")

@mark.lab_has_subcloud
def test_bootstrap_failure_replay():
    """Test bootstrap failure and resume

    Test Steps:
        - log onto system controller
        - get the ssh connection to the active controller
        - check first to see if there is an undeployed subcloud if yes run test
        - If we don't have a subcloud that is undeployed, remove it and then run the test.
        - backup the original bootstrap values yaml file
        - download the bootstrap values yaml file
        - inject the wrong docker registery
        - execute the phased deployment create
        - execute the phased deployment install
        - execute the phased deployment bootstrap
        - wait for bootstrap to fail
        - restore original bootstrap values yaml file
        - execute the phased deployment resume
        - execute the subcloud manage
    """
    primary_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = get_undeployed_subcloud_name()

    # Get the subcloud deployment assets
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
    bootstrap_file = sc_assets.get_bootstrap_file()
    directory, local_bootstrap_file = os.path.split(bootstrap_file)
    bootstrap_bkup_file = f"{bootstrap_file}.bkup"

    # backup the file before editing
    FileKeywords(primary_ssh).copy_file(bootstrap_file, bootstrap_bkup_file)
    # download file before for updation
    FileKeywords(primary_ssh).download_file(bootstrap_file, local_bootstrap_file)

    # download bootstrap values file
    bootstrap_yaml_obj = DeploymentAssetsHandler(local_bootstrap_file)
    bootstrap_yaml_obj.inject_wrong_bootstrap_value()
    # upload file
    FileKeywords(primary_ssh).upload_file(local_bootstrap_file, bootstrap_file)

    # deploy the subcloud with wrong values
    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(primary_ssh)
    dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(primary_ssh)

    # dcmanager subcloud deploy create
    get_logger().log_info(f"dcmanager subcloud deploy create {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_create(subcloud_name)

    # dcmanager subcloud deploy install
    get_logger().log_info(f"dcmanager subcloud deploy install {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_install(subcloud_name)

    # dcmanager subcloud deploy bootstrap
    get_logger().log_info(f"dcmanager subcloud deploy bootstrap {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_bootstrap(subcloud_name, wait_for_status=False)
    dc_manager_sc_list_kw = DcManagerSubcloudListKeywords(primary_ssh)
    dc_manager_sc_list_kw.validate_subcloud_status(subcloud_name, "bootstrap-failed")

    # restore original file
    FileKeywords(primary_ssh).rename_file(bootstrap_bkup_file, bootstrap_file)

    # dcmanager subcloud deploy resume
    time_kpi_start_resume = TimeKPI(time.time())
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_resume(subcloud_name)
    time_kpi_start_resume.log_elapsed_time(time.time(), "time taken subcloud deploy resume")
    # dcmanager subcloud deploy config
    get_logger().log_info(f"dcmanager subcloud deploy config {subcloud_name}.")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_config(subcloud_name)
    sc_status = dc_manager_sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name).get_deploy_status()
    validate_equals(sc_status, "complete", "Validate that subcloud is now deployed")

    # dcmanager subcloud manage
    get_logger().log_info(f"dcmanager subcloud manage {subcloud_name}.")
    dcmanager_subcloud_manage_output = dcm_sc_manager_kw.get_dcmanager_subcloud_manage(subcloud_name, timeout=60)
    manage_status = dcmanager_subcloud_manage_output.get_dcmanager_subcloud_manage_object().get_management()
    get_logger().log_info(f"The management state of the subcloud {subcloud_name} is {manage_status}")
