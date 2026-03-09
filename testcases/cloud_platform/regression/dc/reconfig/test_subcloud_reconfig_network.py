from pytest import mark, fail

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_network_object import DcManagerSubcloudNetworkObject
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.dcmanager.deployment_assets_keywords import DeploymentAssestsKeywords
from keywords.cloud_platform.system.host.system_host_if_keywords import SystemHostInterfaceKeywords
from keywords.cloud_platform.system.interface.system_interface_network_keywords import SystemInterfaceNetworkKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.network.system_network_keywords import SystemNetworkKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_reconfig_one_subcloud_network(request):
    """
    Execute a subcloud network reconfiguration

    Test Steps:
        - Swact to controller-0 if necessary
        - Modify bootstrap YAML to enable admin network configuration
        - Configure subcloud admin network interface and address pool
        - Create admin network and assign interface
        - Update subcloud network configuration via dcmanager
    """

    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Swact to controller-0 if necessary.")
    active_system_controller = SystemHostListKeywords(system_controller_ssh).get_active_controller()
    standby_system_controller = SystemHostListKeywords(system_controller_ssh).get_standby_controller()
    if active_system_controller.get_host_name() != "controller-0":
        SystemHostSwactKeywords(system_controller_ssh).host_swact()
        SystemHostSwactKeywords(system_controller_ssh).wait_for_swact(active_system_controller, standby_system_controller)

    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name_list = lab_config.get_subcloud_names()
    if len(subcloud_name_list) == 0:
        fail("None subcloud found in config file.")

    subcloud_name = subcloud_name_list[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_standby_controller = SystemHostListKeywords(subcloud_ssh).get_standby_controller()
    subcloud_active_controller = SystemHostListKeywords(subcloud_ssh).get_active_controller()

    subcloud_bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()

    # Modify the bootstrap values YAML file
    get_logger().log_info(f"Creating backup for {subcloud_bootstrap_values}")
    FileKeywords(system_controller_ssh).copy_file(subcloud_bootstrap_values, f"{subcloud_bootstrap_values}.backup")

    get_logger().log_test_case_step("Modifying bootstrap values to handle admin.")
    assets_keywords = DeploymentAssestsKeywords(system_controller_ssh)
    assets_keywords.modify_yaml_to_admin_network_config(subcloud_bootstrap_values)

    admin_network = assets_keywords.get_values_by_key_prefix(subcloud_bootstrap_values, "admin", "network").get_network_object()
    admin_subnet = admin_network.get_subnet()
    admin_subnet_prefix = admin_network.get_subnet_prefix()
    admin_start_address = admin_network.get_start_address()
    admin_end_address = admin_network.get_end_address()
    admin_gateway_address = admin_network.get_gateway_address()

    # Validate admin variables are not None
    if None in [admin_start_address, admin_end_address, admin_gateway_address, admin_subnet]:
        fail("One or more admin network values are None. Check YAML configuration.")

    is_ipv6 = ":" in str(admin_gateway_address)

    def teardown():
        get_logger().log_teardown_step("Restore bootstrap values file data.")
        FileKeywords(system_controller_ssh).move_file(f"{subcloud_bootstrap_values}.backup", f"{subcloud_bootstrap_values}")

        get_logger().log_teardown_step("Retrieve management network values.")
        mgmt_network = assets_keywords.get_values_by_key_prefix(f"{subcloud_bootstrap_values}", "management", "network").get_network_object()

        update_network_values = DcManagerSubcloudNetworkObject(
            management_subnet=mgmt_network.get_subnet(),
            management_gateway_address=mgmt_network.get_gateway_address(),
            management_start_address=mgmt_network.get_start_address(),
            management_end_address=mgmt_network.get_end_address(),
            bootstrap_address=subcloud_ssh.host,
            sysadmin_password=subcloud_ssh.password
        )

        subcloud_mgmt_network = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_management_network()
        subcloud_subnet = mgmt_network.get_subnet()

        # if subcloud management network is not the same as in bootstrap, it means that subcloud network was
        # updated in system controller, therefore we need to update back to the original network.
        get_logger().log_teardown_step(f"Verifying if subcloud network values were updated in controller-0. {subcloud_name} management subnet: {subcloud_mgmt_network} - subcloud network subnet in system controller: {subcloud_subnet}")
        if subcloud_mgmt_network != subcloud_subnet:
            get_logger().log_info("Subcloud network was updated in system controller, updating back to original values.")

            if DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_management() == "managed":
                get_logger().log_teardown_step(f"Unmanaging subcloud {subcloud_name}")
                DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)

            get_logger().log_teardown_step("Updating subcloud back to management network.")
            DcManagerSubcloudUpdateKeywords(system_controller_ssh).dcmanager_subcloud_update_network(subcloud_name, update_network_values)

            get_logger().log_teardown_step(f"Managing {subcloud_name}.")
            DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

    request.addfinalizer(teardown)

    # TODO: Retrieve interface name from lab config file.
    get_logger().log_info("Retrieve interface name.")
    selected_interface_name = "enp2s3"

    # Subcloud active controller should be controller-0
    if subcloud_active_controller.get_host_name() != "controller-0":
        get_logger().log_info("Swacting to subcloud controller-0.")
        SystemHostSwactKeywords(subcloud_ssh).host_swact()
        SystemHostSwactKeywords(subcloud_ssh).wait_for_swact(subcloud_active_controller, subcloud_standby_controller)

    subcloud_active_controller = SystemHostListKeywords(subcloud_ssh).get_active_controller()
    subcloud_standby_controller = SystemHostListKeywords(subcloud_ssh).get_standby_controller()

    for controller in [subcloud_standby_controller.get_host_name(), subcloud_active_controller.get_host_name()]:

        # Lock subcloud standby controller
        get_logger().log_test_case_step(f"Locking {controller}")
        SystemHostLockKeywords(subcloud_ssh).lock_host(controller)

        # Modify host interface to platform class
        get_logger().log_test_case_step("Modifying admin interface to platform class")
        SystemHostInterfaceKeywords(subcloud_ssh).system_host_interface_modify(controller, selected_interface_name, "platform")

        # Unlock host
        get_logger().log_test_case_step(f"Unlocking {controller}")
        SystemHostLockKeywords(subcloud_ssh).unlock_host(controller)

        # Swact to standby subcloud controller. Second loop will swact back to controller-0.
        get_logger().log_test_case_step(f"Network added to {controller}. Swacting to {SystemHostListKeywords(subcloud_ssh).get_standby_controller().get_host_name()}")

        # Capture current controller states before swact
        current_active = SystemHostListKeywords(subcloud_ssh).get_active_controller()
        current_standby = SystemHostListKeywords(subcloud_ssh).get_standby_controller()
        
        SystemHostSwactKeywords(subcloud_ssh).host_swact()
        SystemHostSwactKeywords(subcloud_ssh).wait_for_swact(current_active, current_standby)

    # 3. Add address pool
    get_logger().log_test_case_step("Adding admin address pool")
    SystemAddrpoolListKeywords(subcloud_ssh).add_addrpool_from_bootstrap_yaml_values(admin_start_address, admin_gateway_address, admin_subnet, admin_subnet_prefix, is_ipv6)

    # 4. Add network
    get_logger().log_test_case_step("Adding admin network")
    admin_network_uuid = SystemAddrpoolListKeywords(subcloud_ssh).get_system_addrpool_list().get_uuid_by_name("admin")
    SystemNetworkKeywords(subcloud_ssh).network_add("admin", "admin", False, admin_network_uuid)

    # 5. Assign interface to network
    get_logger().log_test_case_step("Assigning interface to network")
    SystemInterfaceNetworkKeywords(subcloud_ssh).interface_network_assign(subcloud_active_controller.get_host_name(), selected_interface_name, "admin")
    SystemInterfaceNetworkKeywords(subcloud_ssh).interface_network_assign(subcloud_standby_controller.get_host_name(), selected_interface_name, "admin")

    if DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_management() == "managed":
        get_logger().log_test_case_step(f"Unmanage {subcloud_name}")
        DcManagerSubcloudManagerKeywords(system_controller_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)

    get_logger().log_test_case_step("Updating subcloud network config on system controller")
    network_attr = DcManagerSubcloudNetworkObject(
        management_subnet=f"{admin_subnet}/{admin_subnet_prefix}",
        management_gateway_address=admin_gateway_address,
        management_start_address=admin_start_address,
        management_end_address=admin_end_address,
        bootstrap_address=subcloud_ssh.host,
        sysadmin_password=subcloud_ssh.password
    )
    DcManagerSubcloudUpdateKeywords(system_controller_ssh).dcmanager_subcloud_update_network(subcloud_name, network_attr=network_attr)
