from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_route_keywords import SystemHostRouteKeywords


@mark.p2
@mark.lab_has_subcloud
@mark.lab_has_secondary_system_controller
def test_rehome_one_subcloud_admin_network_subcloud(request):
    """
    Execute a subcloud rehome

    Test Steps:
        - Ensure both initial and target system controllers have the same date.
        - Deploy a subcloud with admin network
        - Unmanage the subcloud to be rehomed.
        - Shutdown both initial controller and subcloud
        - run dcmanager subcloud migration command.

    """

    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()

    origin_system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    destination_system_controller_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(origin_system_controller_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    subcloud_hostname = SystemHostListKeywords(subcloud_ssh).get_active_controller().get_host_name()

    subcloud_bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    subcloud_install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()

    network_list = SystemHostRouteKeywords(subcloud_ssh).get_system_host_route_list_networks(subcloud_hostname)
    subcloud_admin_gateway_address = SystemAddrpoolListKeywords(subcloud_ssh).get_system_addrpool_list().get_admin_gateway_address()
    old_subcloud_oam_subnet = SystemAddrpoolListKeywords(subcloud_ssh).get_system_addrpool_list().get_floating_address_by_name("system-controller-oam-subnet")
    old_subcloud_subnet = SystemAddrpoolListKeywords(subcloud_ssh).get_system_addrpool_list().get_floating_address_by_name("system-controller-subnet")

    if not subcloud_admin_gateway_address:
        fail("Subcloud has no admin gateway address")

    get_logger().log_info(f"Running rehome command on {destination_system_controller_ssh}")
    DcManagerSubcloudAddKeywords(destination_system_controller_ssh).dcmanager_subcloud_add_migrate(subcloud_name, bootstrap_values=subcloud_bootstrap_values, install_values=subcloud_install_values)
    DcManagerSubcloudListKeywords(destination_system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name, status="rehoming")
    DcManagerSubcloudListKeywords(destination_system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name, status="complete")

    new_subcloud_oam_subnet = SystemAddrpoolListKeywords(subcloud_ssh).get_system_addrpool_list().get_floating_address_by_name("system-controller-oam-subnet")
    new_subcloud_subnet = SystemAddrpoolListKeywords(subcloud_ssh).get_system_addrpool_list().get_floating_address_by_name("system-controller-subnet")

    validate_not_equals(old_subcloud_oam_subnet, new_subcloud_oam_subnet, "Validate subcloud system-controller-oam-subnet changed.")
    validate_not_equals(old_subcloud_subnet, new_subcloud_subnet, "Validate subcloud system-controller-subnet changed.")

    get_logger().log_info(f"Deleting subcloud from {origin_system_controller_ssh}")
    DcManagerSubcloudManagerKeywords(origin_system_controller_ssh).get_dcmanager_subcloud_unmanage(subcloud_name=subcloud_name, timeout=30)
    DcManagerSubcloudDeleteKeywords(origin_system_controller_ssh).dcmanager_subcloud_delete(subcloud_name=subcloud_name)

    get_logger().log_info(f"Running rehome command on {origin_system_controller_ssh}")
    DcManagerSubcloudAddKeywords(origin_system_controller_ssh).dcmanager_subcloud_add_migrate(subcloud_name, bootstrap_values=subcloud_bootstrap_values, install_values=subcloud_install_values)
    dcmanager_subcloud_list_keywords.validate_subcloud_status(subcloud_name=subcloud_name, status="rehoming")
    dcmanager_subcloud_list_keywords.validate_subcloud_status(subcloud_name=subcloud_name, status="complete")

    get_logger().log_info(f"Deleting subcloud from {destination_system_controller_ssh}")
    DcManagerSubcloudDeleteKeywords(destination_system_controller_ssh).dcmanager_subcloud_delete(subcloud_name=subcloud_name)

    validate_equals(len(network_list), 1, "Validate system host route list only has one route.")
