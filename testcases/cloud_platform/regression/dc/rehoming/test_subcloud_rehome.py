from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_kube_rootca_update_strategy_keywords import DcmanagerKubeRootcaUpdateStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.deployment_assets.host_profile_yaml_keywords import HostProfileYamlKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sync_files.sync_deployment_assets import SyncDeploymentAssets
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_route_keywords import SystemHostRouteKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from testcases.cloud_platform.regression.dc.backup_restore.test_verify_backup_file import teardown_central, verify_backup_central


def ensure_oidc_app_installed(subcloud_ssh: SSHConnection) -> bool:
    """
    Ensure OIDC app is installed on subcloud. Install if not present.

    Args:
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.

    Returns:
        bool: True if app was already installed, False if newly installed.
    """
    app_name = "oidc-auth-apps"
    app_path = "/usr/local/share/applications/helm/"

    # Check if OIDC app is already installed
    app_list_keywords = SystemApplicationListKeywords(subcloud_ssh)
    app_list = app_list_keywords.get_system_application_list()

    if app_list.is_application_in_output(app_name):
        app = app_list.get_application_by_name(app_name)
        if app.get_status() == "applied":
            get_logger().log_info(f"OIDC app {app_name} is already installed and applied")
            return True

    # Install OIDC app if not present or not applied
    get_logger().log_info(f"Installing OIDC app {app_name} on subcloud")

    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name(app_name)
    upload_input.set_force(True)
    upload_input.set_tar_file_path(app_path + app_name + "*")

    # Upload application
    upload_output = SystemApplicationUploadKeywords(subcloud_ssh).system_application_upload(upload_input)
    app_object = upload_output.get_system_application_object()
    validate_equals(app_object.get_status(), "uploaded", f"OIDC app {app_name} should be uploaded")

    # Apply application
    apply_output = SystemApplicationApplyKeywords(subcloud_ssh).system_application_apply(app_name, 3600, 30)
    app_object = apply_output.get_system_application_object()
    validate_equals(app_object.get_status(), "applied", f"OIDC app {app_name} should be applied")

    return False


def validate_oidc_app_installed(subcloud_ssh: SSHConnection) -> None:
    """
    Validate that OIDC app is installed and applied on subcloud.

    Args:
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.
    """
    app_name = "oidc-auth-apps"

    app_list_keywords = SystemApplicationListKeywords(subcloud_ssh)
    app_list = app_list_keywords.get_system_application_list()

    validate_equals(app_list.is_application_in_output(app_name), True, f"OIDC app {app_name} should be present")

    app = app_list.get_application_by_name(app_name)
    validate_equals(app.get_status(), "applied", f"OIDC app {app_name} should be applied after rehoming")

    get_logger().log_info(f"OIDC app {app_name} validation successful")


def count_pods_on_subcloud(subcloud_ssh: SSHConnection) -> int:
    """
    Count the total number of pods running on a subcloud.

    Args:
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.

    Returns:
        int: Total number of pods on the subcloud.
    """
    kubectl_keywords = KubectlGetPodsKeywords(subcloud_ssh)
    pods_output = kubectl_keywords.get_pods_all_namespaces()
    pod_count = len(pods_output.get_pods())
    get_logger().log_info(f"Total pods on subcloud: {pod_count}")
    return pod_count


def verify_software_release(ssh_connection: SSHConnection) -> None:
    """
    Verify that the software release image is available on the given system controller.

    Args:
        ssh_connection (SSHConnection): SSH connection to the target system controller.
    """
    release = CloudPlatformVersionManagerClass().get_sw_version()
    path = f"/opt/dc-vault/software/{release}"
    file_keywords = FileKeywords(ssh_connection)
    is_iso_exist = file_keywords.validate_file_exists_with_sudo(f"{path}/*.iso")
    validate_equals(is_iso_exist, True, f"Iso file exists in path {path}.")

    is_sig_exist = file_keywords.validate_file_exists_with_sudo(f"{path}/*.sig")
    validate_equals(is_sig_exist, True, f"Sig file exists in path {path}.")


def update_subcloud_assets(ssh_connection: SSHConnection, subcloud_bootstrap_values: str, subcloud_install_values: str, systemcontroller_gateway_address: str) -> None:
    """
    Update the subcloud assets files before rehome.

    Args:
        ssh_connection (SSHConnection): SSH connection to the target system controller.
        subcloud_bootstrap_values (str): Path to the subcloud bootstrap values file.
        subcloud_install_values (str): Path to the subcloud install values file.
        systemcontroller_gateway_address (str): Gateway address of the system controller.
    """
    yaml_file = HostProfileYamlKeywords(ssh_connection)
    file = yaml_file.download_file(subcloud_bootstrap_values)
    yaml_file.update_yaml_key(file, "systemcontroller_gateway_address", systemcontroller_gateway_address)
    yaml_file.upload_file(file, subcloud_bootstrap_values)
    file = yaml_file.download_file(subcloud_install_values)
    yaml_file.remove_yaml_key(file, "software_version")
    yaml_file.upload_file(file, subcloud_install_values)


def sync_deployment_assets_between_system_controllers(origin_ssh_connection: SSHConnection, destination_ssh_connection: SSHConnection, subcloud_name: str, subcloud_bootstrap_values: str, subcloud_install_values: str) -> None:
    """
    Synchronize deployment assets files for a given subcloud between two system controllers.

    Args:
        origin_ssh_connection (SSHConnection): SSH connection to the origin system controller.
        destination_ssh_connection (SSHConnection): SSH connection to the destination system controller.
        subcloud_name (str): Name of the subcloud whose assets are to be synchronized.
        subcloud_bootstrap_values (str): Path to the subcloud bootstrap values file.
        subcloud_install_values (str): Path to the subcloud install values file.
    """
    SyncDeploymentAssets(origin_ssh_connection).sync_subcloud_assets(subcloud_name, destination_ssh_connection)
    host_name = SystemHostListKeywords(destination_ssh_connection).get_active_controller().get_host_name()
    system_host_route = SystemHostRouteKeywords(destination_ssh_connection).get_system_host_route_list(host_name)
    systemcontroller_gateway_address = system_host_route.get_gateway()[0]
    update_subcloud_assets(destination_ssh_connection, subcloud_bootstrap_values, subcloud_install_values, systemcontroller_gateway_address)


def get_subcloud_in_sync(ssh_connection: SSHConnection, subcloud_name: str) -> None:
    """
    Ensure that the specified subcloud reaches 'in-sync' status.

    Args:
        ssh_connection (SSHConnection): SSH connection to the target system controller.
        subcloud_name (str): Name of the subcloud to make it in-sync.
    """
    file_keywords = FileKeywords(ssh_connection)
    path1 = "/etc/kubernetes/pki/ca.crt"
    path2 = "/etc/kubernetes/pki/ca.key"
    is_crt_exist = file_keywords.validate_file_exists_with_sudo(path1)
    validate_equals(is_crt_exist, True, f"Crt file exists in path {path1}.")
    is_key_exist = file_keywords.validate_file_exists_with_sudo(path2)
    validate_equals(is_key_exist, True, f"Key file exists in path {path2}.")
    file_keywords.concatenate_files_with_sudo(path1, path2, "/tmp/ca.pem")
    dcm_krc_update_strategy = DcmanagerKubeRootcaUpdateStrategyKeywords(ssh_connection)
    dcm_krc_update_strategy.dcmanager_kube_rootca_update_strategy_create(cert_file="/tmp/ca.pem")
    dcm_krc_update_strategy.dcmanager_kube_rootca_update_strategy_apply()
    DcManagerSubcloudListKeywords(ssh_connection).validate_subcloud_sync_status(subcloud_name, expected_sync_status="in-sync")


def perform_rehome_operation(origin_ssh_connection: SSHConnection, destination_ssh_connection: SSHConnection, subcloud_name: str, subcloud_bootstrap_values: str, subcloud_install_values: str) -> None:
    """
    Rehome a subcloud from the origin system controller to the destination system controller.

    Args:
        origin_ssh_connection (SSHConnection): SSH connection to the origin system controller.
        destination_ssh_connection (SSHConnection): SSH connection to the destination system controller.
        subcloud_name (str): Name of the subcloud to be rehomed.
        subcloud_bootstrap_values (str): Path to the subcloud bootstrap values file.
        subcloud_install_values (str): Path to the subcloud install values file.
    """
    # Ensure software image load is available on destination system controller.
    verify_software_release(destination_ssh_connection)

    # Synchronizes subcloud deployments assets between both source and destination system controllers.
    get_logger().log_info(f"Synchronizing subcloud {subcloud_name} deployment assets between source and destination system controllers")
    sync_deployment_assets_between_system_controllers(origin_ssh_connection, destination_ssh_connection, subcloud_name, subcloud_bootstrap_values, subcloud_install_values)

    dcm_sc_list_kw_destination = DcManagerSubcloudListKeywords(destination_ssh_connection)
    dcm_sc_kw_origin = DcManagerSubcloudManagerKeywords(origin_ssh_connection)
    dcm_sc_kw_destination = DcManagerSubcloudManagerKeywords(destination_ssh_connection)

    dcm_sc_kw_origin.get_dcmanager_subcloud_unmanage(subcloud_name, 30)
    DcManagerSubcloudAddKeywords(destination_ssh_connection).dcmanager_subcloud_add_migrate(subcloud_name, bootstrap_values=subcloud_bootstrap_values, install_values=subcloud_install_values)
    dcm_sc_list_kw_destination.validate_subcloud_status(subcloud_name, status="rehoming")
    dcm_sc_list_kw_destination.validate_subcloud_status(subcloud_name, status="complete")
    dcm_sc_kw_destination.get_dcmanager_subcloud_manage(subcloud_name, timeout=30)

    get_logger().log_info(f"Deleting subcloud from {origin_ssh_connection}")
    DcManagerSubcloudDeleteKeywords(origin_ssh_connection).dcmanager_subcloud_delete(subcloud_name)

    get_logger().log_info(f"Getting subcloud {subcloud_name} in-sync on {destination_ssh_connection}")
    get_subcloud_in_sync(destination_ssh_connection, subcloud_name)


def verify_backup_central_duplex(central_ssh: SSHConnection, subcloud_ssh: SSHConnection, subcloud_name: str):
    """
    Verify backup of a subcloud on Central Cloud.

    Args:
        central_ssh (SSHConnection): SSH connection to the active controller.
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.
        subcloud_name (str): subcloud name to backup.
    """
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    HealthKeywords(subcloud_ssh).validate_healty_cluster()
    verify_backup_central(central_ssh, subcloud_name)


@mark.p2
@mark.subcloud_lab_is_duplex
@mark.lab_has_secondary_system_controller
def test_rehome_duplex_subcloud(request):
    """
    Verify rehome one subcloud between two system controllers.

    Test Steps:
        - Get the duplex subcloud.
        - Ensure OIDC app is installed on subcloud before rehoming
        - Count pods on subcloud before rehoming
        - Perform rehoming operation between system controllers
        - Validate OIDC app is still installed after rehoming
        - Count pods on subcloud after rehoming
        - Validate pod counts are the same before and after rehoming
    """
    origin_system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    destination_system_controller_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()
    dcm_sc_list_kw_origin = DcManagerSubcloudListKeywords(origin_system_controller_ssh)

    # Gets the lowest subcloud (the subcloud with the lowest id).
    get_logger().log_info("Getting subcloud with the lowest id")
    duplex_subcloud = dcm_sc_list_kw_origin.get_dcmanager_subcloud_list().get_healthy_subcloud_by_type(LabTypeEnum.DUPLEX.value)
    subcloud_name = duplex_subcloud.get_name()

    # Gets the subcloud bootstrap and install values files
    get_logger().log_info(f"Getting deployment assets for subcloud {subcloud_name}")
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    subcloud_install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()

    # All Validation before rehome operation
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Ensure OIDC app is installed before rehoming
    get_logger().log_info("Ensuring OIDC app is installed before rehoming")
    ensure_oidc_app_installed(subcloud_ssh)

    # Count pods before rehoming
    get_logger().log_info("Counting pods before rehoming")
    pods_before_rehome = count_pods_on_subcloud(subcloud_ssh)

    # Perform rehome operation
    get_logger().log_info(f"Rehoming subcloud {subcloud_name} from {origin_system_controller_ssh} to {destination_system_controller_ssh}")
    perform_rehome_operation(origin_system_controller_ssh, destination_system_controller_ssh, subcloud_name, subcloud_bootstrap_values, subcloud_install_values)

    # Validations after rehome operation
    rehomed_subcloud = DcManagerSubcloudListKeywords(destination_system_controller_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    validate_equals(rehomed_subcloud.get_management(), "managed", f"Subcloud {subcloud_name} is managed.")
    validate_equals(rehomed_subcloud.get_availability(), "online", f"Subcloud {subcloud_name} is online.")
    validate_equals(rehomed_subcloud.get_sync(), "in-sync", f"Subcloud {subcloud_name} is in-sync.")
    get_logger().log_info(f"Rehome operation of subcloud {subcloud_name} completed successfully.")

    # Validate OIDC app is still installed after rehoming
    get_logger().log_info("Validating OIDC app is installed after rehoming")
    validate_oidc_app_installed(subcloud_ssh)

    # Count pods after rehoming
    get_logger().log_info("Counting pods after rehoming")
    pods_after_rehome = count_pods_on_subcloud(subcloud_ssh)
    # Validate pod counts are the same
    validate_equals(pods_before_rehome, pods_after_rehome, "Pod count should be the same before and after rehoming")

    # Verify backup on Central Cloud after rehoming
    request.addfinalizer(teardown_central)
    verify_backup_central_duplex(destination_system_controller_ssh, subcloud_ssh, subcloud_name)
