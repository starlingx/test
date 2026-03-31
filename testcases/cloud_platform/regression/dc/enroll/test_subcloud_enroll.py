import os
from pytest import mark, fail

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords


def create_fake_bootstrap_values(bootstrap_values: str, ssh_connection: SSHConnection):
    """Copy bootstrap_values file and change the last octet of admin_gateway_address to 60 to force enroll failure.

    Args:
        bootstrap_values: Path to the original bootstrap values file.
        ssh_connection: SSH connection to the system controller.

    Returns:
        Path to the fake bootstrap values file on the remote host.
    """
    dir_name = os.path.dirname(bootstrap_values)
    base_name = os.path.basename(bootstrap_values)
    fake_bootstrap_values = os.path.join(dir_name, f'fake_{base_name}')

    file_keywords = FileKeywords(ssh_connection)
    local_temp_file = f"/tmp/{base_name}"
    file_keywords.download_file(bootstrap_values, local_temp_file)

    modified_lines = []
    skip_registry_block = False
    with open(local_temp_file, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith('docker_registries:'):
                skip_registry_block = True
                modified_lines.append("docker_registries:\n")
                modified_lines.append("  k8s.gcr.io:\n")
                modified_lines.append("    url: registry.central:9001/k8s.gcr.io\n")
                modified_lines.append("    username: someuser\n")
                continue
            if skip_registry_block:
                if line.startswith(' ') or line.startswith('\t'):
                    continue
                skip_registry_block = False
            modified_lines.append(line)

    with open(local_temp_file, 'w') as f:
        f.writelines(modified_lines)

    file_keywords.upload_file(local_temp_file, fake_bootstrap_values)
    os.remove(local_temp_file)

    return fake_bootstrap_values

def run_enroll_operations(
        system_controller_ssh: SSHConnection,
        subcloud_name: str = None,
        bootstrap_values: str = None,
        install_values: str = None,
        deployment_config_file: str = None,
        phased: bool = False):

    """Run the enroll operations for a subcloud.

    Args:
        system_controller_ssh: SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud to enroll.
        bootstrap_values (str): Path to the bootstrap values file.
        install_values (str): Path to the install-values file.
        deployment_config_file (str): Path to the deployment config file.
        phased (bool): If the enroll operation should be in phases or complete flow. Defaults to False.
    """

    if phased and subcloud_name is not None:
        dcmanager_subcloud_deploy_kw = DCManagerSubcloudDeployKeywords(system_controller_ssh)
        get_logger().log_test_case_step(f"Enrolling {subcloud_name}")
        dcmanager_subcloud_deploy_kw.dcmanager_subcloud_enroll(subcloud_name)

        get_logger().log_test_case_step(f"Configuring {subcloud_name}")
        dcmanager_subcloud_deploy_kw.dcmanager_subcloud_deploy_config(subcloud_name)
    else:
        none_params = [name for name, value in {"bootstrap_values": bootstrap_values, "install_values": install_values,
                                                "deployment_config_file": deployment_config_file}.items() if value is None]
        if none_params:
            fail(f"The following required parameters are None: {', '.join(none_params)}")
        DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll(
            subcloud_name=subcloud_name,
            bootstrap_values=bootstrap_values,
            install_values=install_values,
            deploy_config_file=deployment_config_file
        )

@mark.p2
@mark.lab_has_subcloud
def test_enroll_one_sx_subcloud():
    """
    Execute a subcloud enroll

    Test Steps:
        - Validate the selected subcloud is factory-installed.
          subclouds are found.
        - Run enroll command.

    """

    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    get_logger().log_test_case_step(f"Verify that {subcloud_name} has completed factory-install process.")
    if not FileKeywords(subcloud_ssh).file_exists("/var/lib/factory-install/complete"):
        fail("This subcloud was not factory installed, unable to proceed with enroll.")

    bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
    deployment_config_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()

    run_enroll_operations(system_controller_ssh, subcloud_name, bootstrap_values, install_values, deployment_config_file)
    DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name, status="complete")
    DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_availability_status(subcloud_name)

@mark.p2
@mark.lab_has_subcloud
def test_retry_enroll_one_sx_subcloud(request):
    """
    Execute a subcloud enroll passing a dm file with wrong
    data. run subcloud enrollment retry.

    Test Steps:
        - Validate the selected subcloud is factory-installed.
        - Run enroll command passing invalid dm file with wrong data.
        - verify that enrollment failed.
        - Run subcloud enrollment retry.

    """

    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    get_logger().log_test_case_step(f"Verify that {subcloud_name} has completed factory-install process.")
    if not FileKeywords(subcloud_ssh).file_exists("/var/lib/factory-install/complete"):
        fail("This subcloud was not factory installed, unable to proceed with enroll.")

    bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
    deployment_config_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()

    # Create fake bootstrap file with wrong password to force enroll failure
    fake_bootstrap_values = create_fake_bootstrap_values(bootstrap_values, system_controller_ssh)

    def teardown():
        """Cleanup: Remove the fake bootstrap file."""
        get_logger().log_info(f"Removing fake bootstrap file: {fake_bootstrap_values}")
        FileKeywords(system_controller_ssh).delete_file(fake_bootstrap_values)
    
    request.addfinalizer(teardown)

    # Attempt to run enroll with wrong bootstrap values data.
    run_enroll_operations(system_controller_ssh, subcloud_name, fake_bootstrap_values, install_values, deployment_config_file)
    DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name, status="enroll-failed")
    DcManagerSubcloudDeleteKeywords(system_controller_ssh).dcmanager_subcloud_delete(subcloud_name)

    run_enroll_operations(system_controller_ssh, subcloud_name, bootstrap_values, install_values, deployment_config_file)
    DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name,status="complete")
    DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_availability_status(subcloud_name)
    DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

@mark.p2
@mark.lab_has_subcloud
def test_enroll_sx_subcloud_after_factory_restore(request):
    """
    Test subcloud enroll after a factory restore.

    Test Steps:
        - Validate the selected subcloud is factory-installed.
        - Create a deploy config yml file.
        - Create a subcloud backup.
        - Restore the subcloud to factory state.
        - Enroll the subcloud.
        - Validate enroll completion and availability.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    dcm_sc_list_kw = DcManagerSubcloudListKeywords(system_controller_ssh)
    dc_manager_backup = DcManagerSubcloudBackupKeywords(system_controller_ssh)
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    get_logger().log_test_case_step(f"Verify that {subcloud_name} has completed factory-install process.")
    if not FileKeywords(subcloud_ssh).file_exists("/var/lib/factory-install/complete"):
        fail("This subcloud was not factory installed, unable to proceed with enroll.")

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    home_path = "/home/sysadmin"

    restore_values = f"{home_path}/restore_values_{subcloud_name}.yml"
    FileKeywords(system_controller_ssh).create_file_with_echo(restore_values, "ipmi_sel_event_monitoring: false")

    def teardown() -> None:
        """Cleanup: Remove the restore values file."""
        FileKeywords(system_controller_ssh).delete_file(restore_values)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Restoring subcloud factory backup: {subcloud_name}")
    dc_manager_backup.restore_subcloud_backup(subcloud_password, system_controller_ssh, subcloud=subcloud_name, factory=True, restore_values_path=restore_values)

    get_logger().log_test_case_step("Waiting for subcloud to unlock.")
    dcm_sc_list_kw.validate_subcloud_availability_status(subcloud_name)
    DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)
