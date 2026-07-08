import time
from typing import Dict, List, Optional, Tuple

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_management_enum import DcManagerSubcloudListManagementEnum
from keywords.cloud_platform.dcmanager.objects.subcloud_pick_result import SubcloudPickResult
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords, pick_subcloud_with_fallback
from keywords.cloud_platform.deployment_assets.host_profile_yaml_keywords import HostProfileYamlKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sync_files.sync_deployment_assets import SyncDeploymentAssets
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_route_keywords import SystemHostRouteKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords


def determine_rehome_direction(
    cloud_a_ssh: SSHConnection,
    cloud_b_ssh: SSHConnection,
    subcloud_name: str = None,
    load: Optional[str] = None,
) -> Tuple[SSHConnection, SSHConnection, List[str]]:
    """Determine the origin and destination system controllers for a rehome operation.

    When a specific subcloud_name is provided, the origin is the system controller
    that currently owns (lists) that subcloud. When no subcloud_name is provided,
    the origin is the system controller with more online configured subclouds.

    Args:
        cloud_a_ssh (SSHConnection): SSH connection to the first system controller.
        cloud_b_ssh (SSHConnection): SSH connection to the second system controller.
        subcloud_name (str): Optional specific subcloud name. When provided, determines
            direction based on which cloud currently owns this subcloud.
        load (Optional[str]): Optional software version filter for batch mode.
            Accepts "N-1" or an explicit version string. When provided, only
            subclouds running the specified version are considered.
            direction based on which cloud currently owns this subcloud.

    Returns:
        Tuple[SSHConnection, SSHConnection, List[str]]: A tuple of
            (origin_ssh, destination_ssh, subcloud_names) where:
            - origin_ssh: SSH connection to the system controller that currently owns the subclouds
            - destination_ssh: SSH connection to the target system controller for rehoming
            - subcloud_names: List of subcloud names to rehome

    Raises:
        ValueError: If the specified subcloud is not found on either system controller,
            or if no online subclouds are available in batch mode.
    """
    dcm_list_a = DcManagerSubcloudListKeywords(cloud_a_ssh)
    dcm_list_b = DcManagerSubcloudListKeywords(cloud_b_ssh)

    if subcloud_name:
        # Single subcloud mode: find which cloud owns it
        cloud_a_list = dcm_list_a.get_dcmanager_subcloud_list()
        cloud_b_list = dcm_list_b.get_dcmanager_subcloud_list()

        a_has_it = cloud_a_list.is_subcloud_in_output(subcloud_name)
        b_has_it = cloud_b_list.is_subcloud_in_output(subcloud_name)

        if a_has_it and not b_has_it:
            get_logger().log_info(f"Subcloud {subcloud_name} found on Cloud A — Cloud A is origin")
            return cloud_a_ssh, cloud_b_ssh, [subcloud_name]
        elif b_has_it and not a_has_it:
            get_logger().log_info(f"Subcloud {subcloud_name} found on Cloud B — Cloud B is origin")
            return cloud_b_ssh, cloud_a_ssh, [subcloud_name]
        elif a_has_it and b_has_it:
            # Both have it — pick the one where it's online as origin
            sc_a = cloud_a_list.get_subcloud_by_name(subcloud_name)
            sc_b = cloud_b_list.get_subcloud_by_name(subcloud_name)
            if sc_a.get_availability() == "online":
                get_logger().log_info(f"Subcloud {subcloud_name} is online on Cloud A — Cloud A is origin")
                return cloud_a_ssh, cloud_b_ssh, [subcloud_name]
            elif sc_b.get_availability() == "online":
                get_logger().log_info(f"Subcloud {subcloud_name} is online on Cloud B — Cloud B is origin")
                return cloud_b_ssh, cloud_a_ssh, [subcloud_name]
            else:
                raise ValueError(f"Subcloud {subcloud_name} exists on both clouds but is not online on either")
        else:
            raise ValueError(f"Subcloud {subcloud_name} not found on either system controller")

    # Batch mode: use SubcloudPickerKeywords to find online configured subclouds
    try:
        cloud_a_results = SubcloudPickerKeywords(cloud_a_ssh).pick_all(
            availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
            load=load,
            present_in_config=True,
        )
        cloud_a_online = [r.get_name() for r in cloud_a_results]
    except KeywordException:
        cloud_a_online = []

    try:
        cloud_b_results = SubcloudPickerKeywords(cloud_b_ssh).pick_all(
            availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
            load=load,
            present_in_config=True,
        )
        cloud_b_online = [r.get_name() for r in cloud_b_results]
    except KeywordException:
        cloud_b_online = []

    get_logger().log_info(f"Cloud A online subclouds: {cloud_a_online} (count: {len(cloud_a_online)})")
    get_logger().log_info(f"Cloud B online subclouds: {cloud_b_online} (count: {len(cloud_b_online)})")

    if len(cloud_a_online) >= len(cloud_b_online):
        get_logger().log_info("Cloud A selected as origin (has more or equal online subclouds)")
        return cloud_a_ssh, cloud_b_ssh, cloud_a_online
    else:
        get_logger().log_info("Cloud B selected as origin (has more online subclouds)")
        return cloud_b_ssh, cloud_a_ssh, cloud_b_online


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

        validate_equals_with_retry(get_sync, "in-sync", f"Subcloud {subcloud_name} should be in-sync.", timeout=60)


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


def perform_batch_rehome_operation(
    origin_ssh_connection: SSHConnection,
    destination_ssh_connection: SSHConnection,
    subclouds: List[Dict[str, str]],
    sync_assets: bool = True,
    release: Optional[str] = None,
) -> None:
    """Rehome multiple subclouds in parallel from origin to destination system controller.

    Triggers all migrate operations first, then polls all subclouds to completion.
    This is significantly faster than sequential rehoming when multiple subclouds
    need to be moved.

    Args:
        origin_ssh_connection (SSHConnection): SSH connection to the origin system controller.
        destination_ssh_connection (SSHConnection): SSH connection to the destination system controller.
        subclouds (List[Dict[str, str]]): List of subcloud descriptors. Each dict must contain:
            - "name": Subcloud name.
            - "bootstrap_values": Path to the subcloud bootstrap values file.
            - "install_values": Path to the subcloud install values file.
        sync_assets (bool): Whether to copy subcloud configuration files between hosts.
        release (Optional[str]): Software release version to pass to the migrate command.
            Required for N-1 subclouds. When None, no --release flag is passed.

    Raises:
        ValueError: If subclouds list is empty.
        Exception: If any subcloud enters a failed state during rehoming.
    """
    if not subclouds:
        raise ValueError("subclouds list must not be empty.")

    subcloud_names = [sc["name"] for sc in subclouds]
    get_logger().log_info(f"Starting batch rehome for subclouds: {subcloud_names}")

    # Phase 1: Verify software release on destination.
    verify_software_release(destination_ssh_connection)

    # Phase 2: Sync deployment assets for all subclouds.
    if sync_assets:
        for sc in subclouds:
            get_logger().log_info(f"Synchronizing deployment assets for subcloud {sc['name']}")
            sync_deployment_assets_between_system_controllers(
                origin_ssh_connection,
                destination_ssh_connection,
                sc["name"],
                sc["bootstrap_values"],
                sc["install_values"],
            )

    dcm_sc_kw_origin = DcManagerSubcloudManagerKeywords(origin_ssh_connection)
    dcm_sc_list_kw_origin = DcManagerSubcloudListKeywords(origin_ssh_connection)
    dcm_sc_list_kw_destination = DcManagerSubcloudListKeywords(destination_ssh_connection)

    # Phase 3: Unmanage all subclouds on origin (skip if already unmanaged).
    for sc in subclouds:
        sc_list_output = dcm_sc_list_kw_origin.get_dcmanager_subcloud_list()
        if sc_list_output.is_subcloud_in_output(sc["name"]):
            sc_obj = sc_list_output.get_subcloud_by_name(sc["name"])
            if sc_obj.get_management() != "unmanaged":
                get_logger().log_info(f"Unmanaging subcloud {sc['name']} on origin")
                dcm_sc_kw_origin.get_dcmanager_subcloud_unmanage(sc["name"], 30)
            else:
                get_logger().log_info(f"Subcloud {sc['name']} is already unmanaged, skipping unmanage step")

    # Phase 4: Trigger migrate for all subclouds (async — does not wait for completion).
    for sc in subclouds:
        get_logger().log_info(f"Triggering migrate for subcloud {sc['name']}")
        DcManagerSubcloudAddKeywords(destination_ssh_connection).dcmanager_subcloud_add_migrate(
            sc["name"],
            bootstrap_values=sc["bootstrap_values"],
            install_values=sc["install_values"],
            release_id=release,
        )

    # Phase 5: Poll all subclouds until they reach 'complete' status.
    get_logger().log_info(f"All migrate commands issued. Waiting for subclouds to complete rehoming: {subcloud_names}")
    _wait_for_batch_rehome_completion(dcm_sc_list_kw_destination, subcloud_names)

    # Phase 6: Post-rehome cleanup — manage on destination, delete from origin.
    for sc_name in subcloud_names:
        get_logger().log_info(f"Post-rehome cleanup for subcloud {sc_name}")
        rehome_operation_cleanup(origin_ssh_connection, destination_ssh_connection, sc_name)

    get_logger().log_info(f"Batch rehome completed successfully for subclouds: {subcloud_names}")


def _wait_for_batch_rehome_completion(
    dcm_sc_list_kw: DcManagerSubcloudListKeywords,
    subcloud_names: List[str],
    timeout: int = 4800,
    polling_sleep_time: int = 60,
) -> None:
    """Poll subclouds until all reach a terminal state (complete or failed).

    Waits for every subcloud to finish before reporting results. If any subcloud
    fails, the function still waits for the remaining ones to reach a terminal
    state, then raises with a summary of successes and failures.

    Args:
        dcm_sc_list_kw (DcManagerSubcloudListKeywords): Keywords instance for the destination system controller.
        subcloud_names (List[str]): Names of subclouds to monitor.
        timeout (int): Maximum seconds to wait for all subclouds to finish.
        polling_sleep_time (int): Seconds between polling attempts.

    Raises:
        Exception: If any subcloud ends in a failed state (after all others finish).
        TimeoutError: If not all subclouds reach a terminal state within timeout.
    """
    failed_statuses = [
        "bootstrap-failed",
        "install-failed",
        "create-failed",
        "config-failed",
        "pre-enroll-failed",
        "enroll-failed",
        "pre-init-enroll-failed",
        "init-enroll-failed",
        "rehome-failed",
    ]
    pending = set(subcloud_names)
    completed = []
    failed = []
    end_time = time.time() + timeout

    while pending and time.time() < end_time:
        sc_list_output = dcm_sc_list_kw.get_dcmanager_subcloud_list()
        finished_this_round = []

        for sc_name in pending:
            if not sc_list_output.is_subcloud_in_output(sc_name):
                continue
            sc_obj = sc_list_output.get_subcloud_by_name(sc_name)
            status = sc_obj.get_deploy_status()

            if status == "complete":
                get_logger().log_info(f"Subcloud {sc_name} rehome completed successfully")
                completed.append(sc_name)
                finished_this_round.append(sc_name)
            elif status in failed_statuses:
                get_logger().log_info(f"Subcloud {sc_name} rehome failed with status: {status}")
                failed.append((sc_name, status))
                finished_this_round.append(sc_name)

        for sc_name in finished_this_round:
            pending.remove(sc_name)

        if pending:
            get_logger().log_info(f"Still waiting for subclouds: {sorted(pending)}")
            time.sleep(polling_sleep_time)

    if pending:
        msg = f"Subclouds did not reach terminal state within {timeout}s: {sorted(pending)}"
        get_logger().log_error(msg)
        raise TimeoutError(msg)

    # Report results
    get_logger().log_info(f"Batch rehome results: {len(completed)} completed, {len(failed)} failed")
    if completed:
        get_logger().log_info(f"Completed: {completed}")
    if failed:
        failed_summary = ", ".join([f"{name} ({status})" for name, status in failed])
        raise Exception(f"Batch rehome failed for: {failed_summary}")


def perform_rehome_operation(
    origin_ssh_connection: SSHConnection,
    destination_ssh_connection: SSHConnection,
    subcloud_name: str,
    subcloud_bootstrap_values: str,
    subcloud_install_values: str,
    expect_failure: bool = False,
    sync_assets: bool = True,
    release: Optional[str] = None,
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
        release (Optional[str]): Software release version to pass to the migrate command.
            Required for N-1 subclouds. When None, no --release flag is passed.
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

    # Only unmanage if the subcloud is currently managed
    subcloud = DcManagerSubcloudListKeywords(origin_ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    if subcloud.get_management() == "managed":
        dcm_sc_kw_origin.get_dcmanager_subcloud_unmanage(subcloud_name, 30)
    else:
        get_logger().log_info(f"Subcloud {subcloud_name} is already unmanaged, skipping unmanage step")
    DcManagerSubcloudAddKeywords(destination_ssh_connection).dcmanager_subcloud_add_migrate(
        subcloud_name,
        bootstrap_values=subcloud_bootstrap_values,
        install_values=subcloud_install_values,
        release_id=release,
    )
    if expect_failure:
        dcm_sc_list_kw_destination.validate_subcloud_status(subcloud_name, status="rehome-failed")
        get_logger().log_info("Rehome failed as expected")
        rehome_operation_cleanup(destination_ssh_connection, origin_ssh_connection, subcloud_name)
    else:
        dcm_sc_list_kw_destination.validate_subcloud_status(subcloud_name, status="rehoming")
        dcm_sc_list_kw_destination.validate_subcloud_status(subcloud_name, status="complete")
        rehome_operation_cleanup(origin_ssh_connection, destination_ssh_connection, subcloud_name)
