from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_none, validate_not_equals, validate_not_none
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.rehoming_utils import perform_rehome_operation, sync_deployment_assets_between_system_controllers, verify_subcloud_healthy
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.fm_client_cli_keywords import FaultManagementClientCLIKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.object.fm_client_cli_object import FaultManagementClientCLIObject
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_route_keywords import SystemHostRouteKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


# --- Helper Functions ---


def count_pods_on_subcloud(subcloud_ssh: SSHConnection) -> int:
    """Count the total number of pods running on a subcloud.

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


def validate_updated_host_route(ssh_connection: SSHConnection, subcloud_ssh: SSHConnection, subcloud_name: str, mgmt_floating_address_before_rehome: str, oam_floating_address_before_rehome: str) -> None:
    """Validate that the host route and floating addresses are updated after rehome.

    Args:
        ssh_connection (SSHConnection): SSH connection to the destination system controller.
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.
        subcloud_name (str): Name of the subcloud.
        mgmt_floating_address_before_rehome (str): Management floating address before rehome.
        oam_floating_address_before_rehome (str): OAM floating address before rehome.
    """
    get_logger().log_info(f"Getting subcloud {subcloud_name} management subnet and system controller gateway ip from destination system controller after rehome")
    subcloud_show = DcManagerSubcloudShowKeywords(ssh_connection).get_dcmanager_subcloud_show(subcloud_name)
    mgmt_subnet = subcloud_show.get_management_network()
    gateway_ip = subcloud_show.get_dcmanager_subcloud_show_object().get_systemcontroller_gateway_ip()

    mgmt_subnet = mgmt_subnet.split("/")[0]
    get_logger().log_info(f"Validating system host route for management subnet {mgmt_subnet} has gateway {gateway_ip}")
    host_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    host_route_list = SystemHostRouteKeywords(ssh_connection).get_system_host_route_list(host_name)
    validate_equals(host_route_list.get_gateway_by_network(mgmt_subnet), gateway_ip, f"System host route for management subnet {mgmt_subnet} should have new gateway {gateway_ip}")

    get_logger().log_info("Validating updated floating addresses after rehome")
    sys_addrpool_output = SystemAddrpoolListKeywords(subcloud_ssh).get_system_addrpool_list()
    mgmt_floating_address_after_rehome = sys_addrpool_output.get_system_controller_management_floating_address_from_subcloud()
    oam_floating_address_after_rehome = sys_addrpool_output.get_system_controller_oam_floating_address_from_subcloud()

    sys_addrpool_output = SystemAddrpoolListKeywords(ssh_connection).get_system_addrpool_list()
    mgmt_floating_address_destination = sys_addrpool_output.get_management_floating_address()
    oam_floating_address_destination = sys_addrpool_output.get_oam_floating_address()

    validate_not_equals(mgmt_floating_address_before_rehome, mgmt_floating_address_after_rehome, "System controller management floating address should change in subcloud after rehoming")
    validate_not_equals(oam_floating_address_before_rehome, oam_floating_address_after_rehome, "System controller OAM floating address should change in subcloud after rehoming")

    validate_equals(mgmt_floating_address_after_rehome, mgmt_floating_address_destination, "System controller management floating address on subcloud should match destination system controller after rehoming")
    validate_equals(oam_floating_address_after_rehome, oam_floating_address_destination, "System controller OAM floating address on subcloud should match destination system controller after rehoming")



# --- Single Subcloud Test Cases ---


@mark.p2
@mark.subcloud_lab_is_duplex
@mark.lab_has_secondary_system_controller
def test_rehome_single_duplex_subcloud_n_release():
    """
    Verify rehome of a single duplex subcloud between two system controllers.

    Prerequisites:
        - A healthy duplex subcloud running N release must be online.
        - Controller-0 must be the active controller on the subcloud.

    Setup:
        - Find a healthy duplex subcloud using SubcloudPickerKeywords
        - Determine rehome direction

    Test Steps:
        1. Count pods on subcloud before rehoming
        2. Record floating addresses before rehome
        3. Perform rehoming operation
        4. Validate subcloud is healthy after rehome
        5. Validate updated host route and floating addresses
        6. Validate pod counts are the same before and after rehoming

    Teardown:
        - Ensure subcloud is managed on whichever cloud owns it
    """
    cloud_a_ssh = LabConnectionKeywords().get_active_controller_ssh()
    cloud_b_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()

    # Find a healthy duplex subcloud (with fallback to secondary SC)
    get_logger().log_info("Getting duplex subcloud")
    origin_system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        load="N",
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()

    # Destination is whichever cloud is NOT the origin
    destination_system_controller_ssh = cloud_b_ssh if origin_system_controller_ssh == cloud_a_ssh else cloud_a_ssh


    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    SystemHostSwactKeywords(subcloud_ssh).ensure_duplex_subcloud_c0_is_active(subcloud_name)

    # Get deployment assets
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    subcloud_install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()

    # Count pods before rehoming
    get_logger().log_info("Counting pods before rehoming")
    pods_before_rehome = count_pods_on_subcloud(subcloud_ssh)

    # Record floating addresses before rehome
    sys_addrpool_output = SystemAddrpoolListKeywords(subcloud_ssh).get_system_addrpool_list()
    mgmt_floating_address_before_rehome = sys_addrpool_output.get_system_controller_management_floating_address_from_subcloud()
    oam_floating_address_before_rehome = sys_addrpool_output.get_system_controller_oam_floating_address_from_subcloud()

    # Perform rehome operation
    get_logger().log_info(f"Rehoming subcloud {subcloud_name} from origin to destination")
    perform_rehome_operation(origin_system_controller_ssh, destination_system_controller_ssh, subcloud_name, subcloud_bootstrap_values, subcloud_install_values)

    # Validate after rehome
    get_logger().log_info(f"Validating subcloud {subcloud_name} is healthy after rehome")
    verify_subcloud_healthy(destination_system_controller_ssh, subcloud_name, check_sync=False)

    get_logger().log_info("Validating updated host route and floating addresses after rehome")
    validate_updated_host_route(destination_system_controller_ssh, subcloud_ssh, subcloud_name, mgmt_floating_address_before_rehome, oam_floating_address_before_rehome)

    # Count pods after rehoming
    get_logger().log_info("Counting pods after rehoming")
    pods_after_rehome = count_pods_on_subcloud(subcloud_ssh)
    validate_equals(pods_before_rehome, pods_after_rehome, "Pod count should be the same before and after rehoming")


@mark.p2
@mark.subcloud_lab_is_simplex
@mark.lab_has_secondary_system_controller
def test_rehome_single_simplex_subcloud_n_release():
    """
    Verify rehome of a single simplex subcloud between two system controllers.

    Prerequisites:
        - A healthy simplex subcloud running N release must be online.

    Setup:
        - Find a healthy simplex subcloud using SubcloudPickerKeywords
        - Determine rehome direction

    Test Steps:
        1. Count pods and validate health before rehoming
        2. Perform rehome operation
        3. Validate subcloud is healthy after rehoming
        4. Validate pod counts are the same before and after rehoming

    Teardown:
        - Ensure subcloud is managed on whichever cloud owns it
    """
    cloud_a_ssh = LabConnectionKeywords().get_active_controller_ssh()
    cloud_b_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()

    # Find a healthy simplex subcloud (with fallback to secondary SC)
    get_logger().log_info("Selecting healthy simplex subcloud for rehoming")
    origin_system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        load="N",
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()

    # Destination is whichever cloud is NOT the origin
    destination_system_controller_ssh = cloud_b_ssh if origin_system_controller_ssh == cloud_a_ssh else cloud_a_ssh


    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Get deployment assets
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    subcloud_install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()

    # Pre-rehome validation
    get_logger().log_info("Validating subcloud health and counting pods before rehoming")
    pods_before_rehome = count_pods_on_subcloud(subcloud_ssh)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

    # Perform rehome operation
    get_logger().log_info(f"Rehoming subcloud {subcloud_name} to destination system controller")
    perform_rehome_operation(origin_system_controller_ssh, destination_system_controller_ssh, subcloud_name, subcloud_bootstrap_values, subcloud_install_values)

    # Post-rehome validation
    get_logger().log_info("Validating subcloud health and counting pods after rehoming")
    verify_subcloud_healthy(destination_system_controller_ssh, subcloud_name, check_sync=False)
    pods_after_rehome = count_pods_on_subcloud(subcloud_ssh)
    validate_equals(pods_before_rehome, pods_after_rehome, "Pod count should remain consistent after rehoming")


# --- Negative Test Cases ---


@mark.p2
@mark.subcloud_lab_is_duplex
@mark.lab_has_secondary_system_controller
def test_rehome_duplex_subcloud_fails_when_c1_is_active():
    """
    Verify rehome fails when controller-1 is the active controller on a duplex subcloud.

    Prerequisites:
        - A healthy duplex subcloud must be online.

    Setup:
        - Find a healthy duplex subcloud
        - Swact to controller-1

    Test Steps:
        1. Swact to controller-1 on the subcloud
        2. Count pods before rehoming
        3. Attempt rehome operation (expect failure)
        4. Validate subcloud is still healthy on origin
        5. Validate pod counts unchanged
        6. Swact back to controller-0

    Teardown:
        - Ensure subcloud is managed on whichever cloud owns it
    """
    cloud_a_ssh = LabConnectionKeywords().get_active_controller_ssh()
    cloud_b_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()

    # Find a healthy duplex subcloud (with fallback to secondary SC)
    get_logger().log_info("Getting duplex subcloud")
    origin_system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        load="N",
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()

    # Destination is whichever cloud is NOT the origin
    destination_system_controller_ssh = cloud_b_ssh if origin_system_controller_ssh == cloud_a_ssh else cloud_a_ssh

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Swact to controller-1 on subcloud
    subcloud_active_controller = SystemHostListKeywords(subcloud_ssh).get_active_controller()
    if subcloud_active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(subcloud_ssh).host_swact()

    # Get deployment assets
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    subcloud_install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()

    # Count pods before rehoming
    get_logger().log_info("Counting pods before rehoming")
    pods_before_rehome = count_pods_on_subcloud(subcloud_ssh)

    # Perform rehome operation expecting failure
    get_logger().log_info(f"Rehoming subcloud {subcloud_name} (expecting failure due to c1 active)")
    perform_rehome_operation(origin_system_controller_ssh, destination_system_controller_ssh, subcloud_name, subcloud_bootstrap_values, subcloud_install_values, expect_failure=True)

    # Validate subcloud is still healthy on origin
    get_logger().log_info(f"Validating subcloud {subcloud_name} is healthy after rehome attempt")
    verify_subcloud_healthy(origin_system_controller_ssh, subcloud_name, check_sync=False)

    # Count pods after rehoming
    get_logger().log_info("Counting pods after rehoming")
    pods_after_rehome = count_pods_on_subcloud(subcloud_ssh)
    validate_equals(pods_before_rehome, pods_after_rehome, "Pod count should be the same before and after rehoming")

    # Swact back to controller-0
    SystemHostSwactKeywords(subcloud_ssh).host_swact()
    verify_subcloud_healthy(origin_system_controller_ssh, subcloud_name, check_sync=False)


@mark.p2
@mark.subcloud_lab_is_simplex
@mark.lab_has_secondary_system_controller
def test_rehome_simplex_subcloud_fails_with_alarm_and_succeeds_after_clear(request):
    """
    Verify rehome fails with an active alarm and succeeds after clearing it.

    Prerequisites:
        - A healthy simplex subcloud must be online.

    Setup:
        - Find a healthy simplex subcloud
        - Inject a test alarm

    Test Steps:
        1. Count pods before rehoming
        2. Inject alarm on subcloud
        3. Attempt rehome (expect failure due to alarm)
        4. Clear the alarm
        5. Retry rehome (expect success)
        6. Validate subcloud is healthy
        7. Validate pod counts consistent

    Teardown:
        - Clear injected alarm if still present
    """
    cloud_a_ssh = LabConnectionKeywords().get_active_controller_ssh()
    cloud_b_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()

    # Find a healthy simplex subcloud (with fallback to secondary SC)
    get_logger().log_info("Selecting healthy simplex subcloud for rehoming test")
    origin_system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        load="N",
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()

    # Destination is whichever cloud is NOT the origin
    destination_system_controller_ssh = cloud_b_ssh if origin_system_controller_ssh == cloud_a_ssh else cloud_a_ssh

    # Get deployment assets
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    subcloud_install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Baseline pod count
    get_logger().log_info("Establishing baseline pod count before rehoming")
    pods_before_rehome = count_pods_on_subcloud(subcloud_ssh)

    # Inject alarm
    fm_client_cli_keywords = FaultManagementClientCLIKeywords(subcloud_ssh)
    alarm_list_keywords = AlarmListKeywords(subcloud_ssh)

    get_logger().log_info("Verifying no conflicting alarms exist on subcloud")
    subcloud_alarms = alarm_list_keywords.alarm_list()
    existing_alarm = next((alarm for alarm in subcloud_alarms if alarm.alarm_id == FaultManagementClientCLIObject.DEFAULT_ALARM_ID), None)
    validate_none(existing_alarm, f"Alarm with ID {FaultManagementClientCLIObject.DEFAULT_ALARM_ID} should not exist before test injection")

    fm_client_cli_object = FaultManagementClientCLIObject()
    fm_client_cli_object.set_alarm_id(FaultManagementClientCLIObject.DEFAULT_ALARM_ID)
    fm_client_cli_object.set_entity_id(f"name={subcloud_name}")

    get_logger().log_info(f"Injecting test alarm on subcloud {subcloud_name}")
    fm_client_cli_keywords.raise_alarm(fm_client_cli_object)

    # Register teardown to clear alarm if test fails midway
    def cleanup_alarm():
        get_logger().log_teardown_step(f"Clear injected alarm on subcloud '{subcloud_name}'")
        try:
            fm_client_cli_keywords.delete_alarm(fm_client_cli_object)
        except Exception:
            get_logger().log_info(f"Alarm already cleared or could not be deleted on {subcloud_name}")

    request.addfinalizer(cleanup_alarm)

    # Verify alarm injection
    subcloud_alarms = alarm_list_keywords.alarm_list()
    injected_alarm = next((alarm for alarm in subcloud_alarms if alarm.alarm_id == fm_client_cli_object.get_alarm_id()), None)
    validate_not_none(injected_alarm, f"Injected alarm should be present on subcloud")

    # Sync assets and attempt first rehome (expect failure)
    get_logger().log_info(f"Synchronizing deployment assets for subcloud {subcloud_name}")
    sync_deployment_assets_between_system_controllers(origin_system_controller_ssh, destination_system_controller_ssh, subcloud_name, subcloud_bootstrap_values, subcloud_install_values)

    get_logger().log_info(f"Attempting rehome of {subcloud_name} (expecting failure due to alarm)")
    origin_dcm_sc_kw = DcManagerSubcloudManagerKeywords(origin_system_controller_ssh)
    origin_dcm_sc_kw.get_dcmanager_subcloud_unmanage(subcloud_name, 30)
    DcManagerSubcloudAddKeywords(destination_system_controller_ssh).dcmanager_subcloud_add_migrate(subcloud_name, bootstrap_values=subcloud_bootstrap_values, install_values=subcloud_install_values)

    # Verify rehome failed
    DcManagerSubcloudListKeywords(destination_system_controller_ssh).validate_subcloud_status(subcloud_name, status="rehome-failed")
    get_logger().log_info(f"Rehome failed as expected due to alarm on subcloud {subcloud_name}")

    # Cleanup failed attempt
    origin_dcm_sc_kw.get_dcmanager_subcloud_manage(subcloud_name, timeout=30)
    DcManagerSubcloudListKeywords(origin_system_controller_ssh).validate_subcloud_sync_status(subcloud_name, "in-sync")
    DcManagerSubcloudDeleteKeywords(destination_system_controller_ssh).dcmanager_subcloud_delete(subcloud_name)

    # Clear alarm
    get_logger().log_info(f"Clearing injected alarm from subcloud {subcloud_name}")
    fm_client_cli_keywords.delete_alarm(fm_client_cli_object)

    # Retry rehome (expect success)
    get_logger().log_info(f"Retrying rehome of {subcloud_name} after alarm clearance")
    perform_rehome_operation(origin_system_controller_ssh, destination_system_controller_ssh, subcloud_name, subcloud_bootstrap_values, subcloud_install_values)

    # Post-rehome validation
    get_logger().log_info(f"Validating subcloud {subcloud_name} health after successful rehome")
    verify_subcloud_healthy(destination_system_controller_ssh, subcloud_name, check_sync=False)

    # Final pod count validation
    get_logger().log_info("Performing final pod count validation")
    pods_after_rehome = count_pods_on_subcloud(subcloud_ssh)
    validate_equals(pods_before_rehome, pods_after_rehome, "Pod count must remain consistent before and after successful rehoming")
