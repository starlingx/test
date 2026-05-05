from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.deployment_assets.host_profile_yaml_keywords import HostProfileYamlKeywords
from keywords.cloud_platform.sync_files.sync_deployment_assets import SyncDeploymentAssets
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_route_keywords import SystemHostRouteKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords


def verify_subcloud_healthy(ssh_connection: SSHConnection, subcloud_name: str, check_sync: bool = True) -> None:
    """
    Verify that the specified subcloud is healthy.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud.
        check_sync (bool): Whether to check subcloud sync state.
    """
    subcloud = DcManagerSubcloudListKeywords(ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    validate_equals(subcloud.get_management(), "managed", f"Subcloud {subcloud_name} is managed.")

    def get_availability():
        subcloud = DcManagerSubcloudListKeywords(ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
        return subcloud.get_availability()

    validate_equals_with_retry(get_availability, "online", f"Subcloud {subcloud_name} is online.")

    if check_sync:

        def get_sync():
            subcloud = DcManagerSubcloudListKeywords(ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
            return subcloud.get_sync()

        validate_equals_with_retry(get_sync, "in-sync", f"Subcloud {subcloud_name} is in-sync.", timeout=60)


def update_subcloud_assets(
    ssh_connection: SSHConnection,
    subcloud_bootstrap_values: str,
    subcloud_install_values: str,
    systemcontroller_gateway_address: str,
) -> None:
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


def sync_deployment_assets_between_system_controllers(
    origin_ssh_connection: SSHConnection,
    destination_ssh_connection: SSHConnection,
    subcloud_name: str,
    subcloud_bootstrap_values: str,
    subcloud_install_values: str,
) -> None:
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
    update_subcloud_assets(
        destination_ssh_connection,
        subcloud_bootstrap_values,
        subcloud_install_values,
        systemcontroller_gateway_address,
    )


def rehome_operation_cleanup(
    remove_subcloud_ssh: SSHConnection,
    keep_subcloud_ssh: SSHConnection,
    subcloud_name: str,
) -> None:
    """
    Cleanup after rehome operation. Remove from one system DB and manage and check sync in the other

    Args:
        remove_subcloud_ssh (SSHConnection): SSH connection to the system controller that will keep the subcloud.
        keep_subcloud_ssh (SSHConnection): SSH connection to the system controller that needs the subcloud removed.
        subcloud_name (str): Name of the subcloud that was rehomed.
    """
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(keep_subcloud_ssh)
    dcm_sc_kw = DcManagerSubcloudManagerKeywords(keep_subcloud_ssh)

    dcm_sc_list_kw.validate_subcloud_availability_status(subcloud_name)
    dcm_sc_kw.get_dcmanager_subcloud_manage(subcloud_name, timeout=30)

    get_logger().log_info(f"Deleting subcloud from {remove_subcloud_ssh}")
    DcManagerSubcloudDeleteKeywords(remove_subcloud_ssh).dcmanager_subcloud_delete(subcloud_name)


def perform_rehome_operation(
    origin_ssh_connection: SSHConnection,
    destination_ssh_connection: SSHConnection,
    subcloud_name: str,
    subcloud_bootstrap_values: str,
    subcloud_install_values: str,
    expect_failure: bool = False,
    sync_assets: bool = True,
) -> None:
    """
    Rehome a subcloud from the origin system controller to the destination system controller.

    Args:
        origin_ssh_connection (SSHConnection): SSH connection to the origin system controller.
        destination_ssh_connection (SSHConnection): SSH connection to the destination system controller.
        subcloud_name (str): Name of the subcloud to be rehomed.
        subcloud_bootstrap_values (str): Path to the subcloud bootstrap values file.
        subcloud_install_values (str): Path to the subcloud install values file.
        expect_failure (bool): Is the rehome expected to fail.
        sync_assets (bool): Whether to copy subcloud configuration files from one host to the other.
    """
    # Ensure software image load is available on destination system controller.
    verify_software_release(destination_ssh_connection)

    # Synchronizes subcloud deployments assets between both source and destination system controllers.
    get_logger().log_info(f"Synchronizing subcloud {subcloud_name} deployment assets between source and destination system controllers")
    if sync_assets:
        sync_deployment_assets_between_system_controllers(
            origin_ssh_connection,
            destination_ssh_connection,
            subcloud_name,
            subcloud_bootstrap_values,
            subcloud_install_values,
        )

    dcm_sc_list_kw_destination = DcManagerSubcloudListKeywords(destination_ssh_connection)
    dcm_sc_kw_origin = DcManagerSubcloudManagerKeywords(origin_ssh_connection)

    dcm_sc_kw_origin.get_dcmanager_subcloud_unmanage(subcloud_name, 30)
    DcManagerSubcloudAddKeywords(destination_ssh_connection).dcmanager_subcloud_add_migrate(
        subcloud_name,
        bootstrap_values=subcloud_bootstrap_values,
        install_values=subcloud_install_values,
    )
    if expect_failure:
        dcm_sc_list_kw_destination.validate_subcloud_status(subcloud_name, status="rehome-failed")
        get_logger().log_info("Rehome failed as expected")
        rehome_operation_cleanup(destination_ssh_connection, origin_ssh_connection, subcloud_name)
    else:
        dcm_sc_list_kw_destination.validate_subcloud_status(subcloud_name, status="rehoming")
        dcm_sc_list_kw_destination.validate_subcloud_status(subcloud_name, status="complete")
        rehome_operation_cleanup(origin_ssh_connection, destination_ssh_connection, subcloud_name)
