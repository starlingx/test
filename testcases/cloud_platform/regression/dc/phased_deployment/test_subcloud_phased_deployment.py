import time

import yaml
from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_address_object import DcManagerSubcloudAddressObject
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_deploy_object import DcManagerSubcloudDeployObject
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_management_enum import DcManagerSubcloudListManagementEnum
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords


def select_test_subcloud(ssh_connection: SSHConnection) -> str:
    """
    Select the subcloud to perform the test on.

    Args:
        ssh_connection(SSHConnection): The ssh connection of the active controller

    Returns:
            str:
                Subcloud name to test on
    """
    subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    subclouds_list = subcloud_list_keywords.get_dcmanager_subcloud_list()
    real_subclouds = subclouds_list.get_dcmanager_subcloud_list_objects()
    if len(real_subclouds) == 0:
        get_logger().log_error("No subclouds found for testing.")
        fail("No subclouds found for testing.")

    for subcloud in real_subclouds:
        # Get the subcloud with state unmanaged and offline
        if subcloud.get_availability == DcManagerSubcloudListManagementEnum.UNMANAGED and subcloud.get_availability == DcManagerSubcloudListAvailabilityEnum.OFFLINE:
            return subcloud.get_name()

    get_logger().log_error("No subcloud found with required state (UNMANAGED and OFFLINE) for testing.")
    fail("No subcloud found with required state (UNMANAGED and OFFLINE) for testing.")


def get_bmc_bootstrap_address(ssh_connection: SSHConnection, subcloud: str) -> DcManagerSubcloudAddressObject:
    """
    Get bmc & bootstrap address from install-values-<subcloud>.yaml file

    Args:
        ssh_connection (SSHConnection): The ssh connection of the active controller
        subcloud (str): Name of the subcloud

    Raises:
        FileNotFoundError: If the file does not exist.
        KeyError: If required keys are missing in the file.

    Returns:
        DcManagerSubcloudAddressObject: Object containing BMC and bootstrap addresses
    """
    get_logger().log_info(f"Get BMC and bootstrap address for {subcloud}")
    config_files = DCManagerSubcloudDeployKeywords(ssh_connection).get_subcloud_config_files(subcloud)
    install_values_file_path = config_files.get_install_file()
    if not FileKeywords(ssh_connection).file_exists(install_values_file_path):
        raise FileNotFoundError(f"{install_values_file_path} is not found")

    get_logger().log_info(f"Get BMC & bootstrap addresses from {install_values_file_path}")
    stream = ssh_connection.send("cat {}".format(install_values_file_path))
    stream_string = "\n".join(stream)
    install_params = yaml.load(stream_string, Loader=yaml.SafeLoader)
    install_param_yaml = yaml.dump(install_params, default_flow_style=False)
    get_logger().log_info(f"Loaded install-values parameters:{install_param_yaml}")

    if "bmc_address" not in install_params or "bootstrap_address" not in install_params:
        raise KeyError(f"Missing required keys in {install_values_file_path}. Available keys: {list(install_params.keys())}")

    bmc_address = install_params["bmc_address"]
    bootstrap_address = install_params["bootstrap_address"]

    if not bmc_address or not bootstrap_address:
        raise ValueError(f"BMC address or bootstrap address cannot be empty in {install_values_file_path}")

    get_logger().log_info(f"Extracted BMC address: {bmc_address}, Bootstrap address: {bootstrap_address}")

    return DcManagerSubcloudAddressObject(bmc_address=bmc_address, bootstrap_address=bootstrap_address)


def capture_kpi(node_name: str, start_time: str, end_time: str, stage: str):
    """
    Capture kpi for subcloud deploy phases from start and end time

    Args:
        node_name (str): Name of the noden
        start_time (str): The start time of the specified stage execution
        end_time (str): The end time of the specified stage execution
        stage (str): The stage of the execution
    """
    time_taken = float(end_time) - float(start_time)
    get_logger().log_info(f"------The time taken for the node {node_name} to finish the stage {stage} is {time_taken} seconds-------")


@mark.p1
@mark.lab_has_subcloud
def test_kpi_subcloud_deploy_phases():
    """Capture Kpi for subcloud deploy
    verify subcloud deploy create, install, bootstrap and config with KPI's for each phase

    Test Steps:
        - Verify subcloud deploy create
        - Verify subcloud deploy install
        - Verify subcloud deploy bootstrap
        - Verify subcloud deploy config
        - Collect KPI data for create, install, bootstrap and config phases
    """
    get_logger().log_info("Starting 'test_kpi_subcloud_deploy_phases' test case.")

    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Get subcloud to perform the test on
    subcloud = select_test_subcloud(ssh_connection)
    get_logger().log_info(f"Selected subcloud for testing: {subcloud}")

    # Delete the selected subcloud to test on
    DcManagerSubcloudDeleteKeywords(ssh_connection).dcmanager_subcloud_delete(subcloud)

    # Get sysadmin password from lab config
    sysadmin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()

    # Get config files
    config_files = DCManagerSubcloudDeployKeywords(ssh_connection).get_subcloud_config_files(subcloud)
    bootstrap_file_path = config_files.get_bootstrap_file()
    install_values_file_path = config_files.get_install_file()
    deploy_standard_file_path = config_files.get_deploy_file()

    get_logger().log_info(f"Verify subcloud deploy create {subcloud}")

    # Get BMC and bootstrap addresses
    address_info = get_bmc_bootstrap_address(ssh_connection, subcloud)

    # Create phase
    start_time = time.time()
    deploy_params = DcManagerSubcloudDeployObject(subcloud=subcloud, bootstrap_address=address_info.get_bootstrap_address(), bootstrap_values=bootstrap_file_path)
    DCManagerSubcloudDeployKeywords(ssh_connection).deploy_create_subcloud(deploy_params)
    create_end_time = time.time()
    create_duration = create_end_time - start_time
    get_logger().log_info(f"Subcloud deploy create duration: {create_duration} seconds")

    # Install phase
    start_time = time.time()
    deploy_params = DcManagerSubcloudDeployObject(subcloud=subcloud, install_values=install_values_file_path, bmc_password=sysadmin_password)
    DCManagerSubcloudDeployKeywords(ssh_connection).deploy_install_subcloud(deploy_params)
    install_end_time = time.time()
    install_duration = install_end_time - start_time
    get_logger().log_info(f"Subcloud deploy install duration: {install_duration} seconds")

    # Bootstrap phase
    start_time = time.time()
    deploy_params = DcManagerSubcloudDeployObject(subcloud=subcloud, bootstrap_values=bootstrap_file_path, bootstrap_address=address_info.get_bootstrap_address(), bmc_password=sysadmin_password)
    DCManagerSubcloudDeployKeywords(ssh_connection).deploy_bootstrap_subcloud(deploy_params)
    bootstrap_end_time = time.time()
    bootstrap_duration = bootstrap_end_time - start_time
    get_logger().log_info(f"Subcloud deploy bootstrap duration: {bootstrap_duration} seconds")

    # Config phase
    start_time = time.time()
    deploy_params = DcManagerSubcloudDeployObject(subcloud=subcloud, deploy_config=deploy_standard_file_path, bmc_password=sysadmin_password)
    DCManagerSubcloudDeployKeywords(ssh_connection).deploy_config_subcloud(deploy_params)
    config_end_time = time.time()
    config_duration = config_end_time - start_time
    get_logger().log_info(f"Subcloud deploy config duration: {config_duration} seconds")

    # Verify final state
    subcloud_obj = DcManagerSubcloudListKeywords(ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud)
    validate_equals(subcloud_obj.get_deploy_status, DCManagerSubcloudDeployKeywords.CONFIG_EXECUTED, f"Succeeded to verify subcloud deploy config {subcloud}")
    end_time = time.time()
    total_duration = end_time - start_time
    get_logger().log_info(f"Total subcloud deploy duration: {total_duration} seconds")
