from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.cloud_platform.dcmanager.dcmanager_peer_group_association_add_keywords import DcManagerPeerGroupAssociationAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_peer_group_association_list_keywords import DcManagerPeerGroupAssociationListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_peer_group_association_sync_keywords import DcManagerPeerGroupAssociationSyncKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_peer_group_add_keywords import DcManagerSubcloudPeerGroupAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_peer_group_list_keywords import DcManagerSubcloudPeerGroupListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_peer_group_list_subclouds_keywords import DcManagerSubcloudPeerGroupListSubcloudsKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_peer_group_migrate_keywords import DcManagerSubcloudPeerGroupMigrateKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_peer_group_status_keywords import DcManagerSubcloudPeerGroupStatusKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.dcmanager.dcmanager_system_peer_add_keywords import DcManagerSystemPeerAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_system_peer_list_keywords import DcManagerSystemPeerListKeywords
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.openstack.endpoint.objects.openstack_endpoint_list_object_filter import OpenStackEndpointListObjectFilter
from keywords.cloud_platform.openstack.endpoint.openstack_endpoint_list_keywords import OpenStackEndpointListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_route_keywords import SystemHostRouteKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.server.power_keywords import PowerKeywords


def configure_system_peer_site(origin_ssh_connection: SSHConnection, target_ssh_connection: SSHConnection) -> None:
    """Configures a system peer on the target site using details gathered from the origin site.

    This function connects to the origin site via `origin_ssh_connection` to retrieve necessary
    system information (such as UUID, identity endpoint URL, and gateway). It then uses
    `target_ssh_connection` to configure the system peer on the target site.

    Args:
        origin_ssh_connection (SSHConnection): SSH connection to the origin site (the site being peered from).
        target_ssh_connection (SSHConnection): SSH connection to the target site (the site where the peer is added).
    """
    # get the endpoint url
    # openstack endpoint list | grep identity | grep public | grep RegionOne
    os_ep_list_fltr = OpenStackEndpointListObjectFilter().set_region("RegionOne").set_interface("public").set_service_type("identity")
    os_ep_list = OpenStackEndpointListKeywords(origin_ssh_connection).endpoint_list().get_endpoints_list_objects_filtered(os_ep_list_fltr)
    if not os_ep_list:
        raise Exception("No endpoints found in the source site.")
    manager_endpoint_url = os_ep_list[0].get_url()

    peer_controller_gateway_address = SystemHostRouteKeywords(origin_ssh_connection).get_system_host_route_list("controller-0").get_gateway_address()

    peer_uuid = SystemShowKeywords(origin_ssh_connection).system_show().get_system_show_object().get_uuid()

    peer_name = f"{target_ssh_connection.get_name()}-{origin_ssh_connection.get_name()}-system-peer"

    manager_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()

    DcManagerSystemPeerAddKeywords(target_ssh_connection).dcmanager_system_peer_add(peer_uuid, peer_name, manager_endpoint_url, peer_controller_gateway_address, manager_password)


def subcloud_update(controller_ssh: SSHConnection, subcloud_name: str) -> None:
    """Updates the specified subcloud on the source site using its bootstrap address and configuration files.

    Args:
        controller_ssh (SSHConnection): SSH connection to the site's controller.
        subcloud_name (str): Name of the subcloud to update
    """
    # Get the subcloud config
    sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    # Get the subcloud bootstrap address
    boot_add = sc_config.get_first_controller().get_ip()

    # Get the subcloud deployment assets
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
    bootstrap_file = sc_assets.get_bootstrap_file()

    # Update the subcloud details for rehoming purpose.
    # We need to import bootstrap_file first for remove
    DcManagerSubcloudUpdateKeywords(controller_ssh).dcmanager_subcloud_update(subcloud_name, "bootstrap-values", bootstrap_file)
    DcManagerSubcloudUpdateKeywords(controller_ssh).dcmanager_subcloud_update(subcloud_name, "bootstrap-address", boot_add)


@mark.p0
@mark.lab_has_subcloud
@mark.lab_has_secondary_system_controller
def test_geo_redundancy():
    """
    Test to verify the geo-redundancy setup rehoming subcloud from one site to another
    Assuming the Site A is the Source site from which subcloud will move,
    and Site B is the Destination site where the subcloud will be moved.
    """
    src_site_ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
    dest_site_ssh_conn = LabConnectionKeywords().get_secondary_active_controller_ssh()

    # Assign site names to SSH connections
    src_site_ssh_conn.set_name(ConfigurationManager.get_lab_config().get_lab_name())
    dest_site_ssh_conn.set_name(ConfigurationManager.get_lab_config().get_secondary_system_controller_config().get_lab_name())

    get_logger().log_test_case_step("Source site: Retrieve subcloud name for rehoming")
    subcloud_name = DcManagerSubcloudListKeywords(src_site_ssh_conn).get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id().get_name()

    get_logger().log_test_case_step("Source site: Update subcloud bootstrap values")
    subcloud_update(src_site_ssh_conn, subcloud_name)

    # get Site B Destination info and add system-peer in Site A source
    get_logger().log_test_case_step("Source site: Add system-peer in Site A (source) using Site B (destination) details and list system peers")
    configure_system_peer_site(dest_site_ssh_conn, src_site_ssh_conn)
    DcManagerSystemPeerListKeywords(src_site_ssh_conn).get_dcmanager_system_peer_list()

    # get Site A Destination info and add system-peer in Site B Destination
    get_logger().log_test_case_step("Destination site: Add system-peer in Site B (destination) using Site A (source) details and list system peers")
    configure_system_peer_site(src_site_ssh_conn, dest_site_ssh_conn)
    DcManagerSystemPeerListKeywords(dest_site_ssh_conn).get_dcmanager_system_peer_list()

    get_logger().log_test_case_step("Source site: Add subcloud peer group (derived from source site name) and list subcloud peer groups")
    peer_group_name = f"{src_site_ssh_conn.get_name()}--subcloud-peer-group"
    DcManagerSubcloudPeerGroupAddKeywords(src_site_ssh_conn).dcmanager_subcloud_peer_group_add(peer_group_name)
    DcManagerSubcloudPeerGroupListKeywords(src_site_ssh_conn).get_dcmanager_subcloud_peer_group_list()

    get_logger().log_test_case_step("Source site: Retrieve subcloud peer group ID and Update subcloud with peer group ID")
    src_subcloud_peer_group_id = DcManagerSubcloudPeerGroupListKeywords(src_site_ssh_conn).get_dcmanager_subcloud_peer_group_list().get_latest_subcloud_peer_group_id()
    DcManagerSubcloudUpdateKeywords(src_site_ssh_conn).dcmanager_subcloud_update(subcloud_name, "peer-group", src_subcloud_peer_group_id)

    # Add peer group association using subcloud peer group ID, system peer ID, and peer group priority
    get_logger().log_test_case_step("Source site: Retrieve system peer ID, add peer group association with priority 1, and list peer group associations")
    system_peer_id = DcManagerSystemPeerListKeywords(src_site_ssh_conn).get_dcmanager_system_peer_list().get_latest_system_peer_id()
    DcManagerPeerGroupAssociationAddKeywords(src_site_ssh_conn).dcmanager_peer_group_association_add(src_subcloud_peer_group_id, system_peer_id, 1)
    pga_id = DcManagerPeerGroupAssociationListKeywords(src_site_ssh_conn).get_dcmanager_peer_group_association_list().get_latest_peer_group_association_id()
    DcManagerPeerGroupAssociationSyncKeywords(src_site_ssh_conn).dcmanager_peer_group_association_sync(pga_id)

    get_logger().log_test_case_step("Destination site: List subcloud peer groups, peer group associations, and all subclouds")
    DcManagerSubcloudPeerGroupListKeywords(dest_site_ssh_conn).get_dcmanager_subcloud_peer_group_list()
    DcManagerPeerGroupAssociationListKeywords(dest_site_ssh_conn).get_dcmanager_peer_group_association_list()
    DcManagerSubcloudListKeywords(dest_site_ssh_conn).get_dcmanager_subcloud_list_all()

    get_logger().log_test_case_step("Destination site: Retrieve subcloud peer group ID and validate associated subclouds")
    dest_subcloud_peer_group_id = DcManagerSubcloudPeerGroupListKeywords(dest_site_ssh_conn).get_dcmanager_subcloud_peer_group_list().get_latest_subcloud_peer_group_id()
    validate_equals(src_subcloud_peer_group_id, dest_subcloud_peer_group_id, f"Subcloud peer group ID {dest_subcloud_peer_group_id} is present on the destination site after association")
    spgs_list = DcManagerSubcloudPeerGroupListSubcloudsKeywords(dest_site_ssh_conn).get_dcmanager_subcloud_peer_group_list_subclouds(dest_subcloud_peer_group_id)
    validate_str_contains("\n".join(spgs_list.dcmanager_output), subcloud_name, "Subclouds found under the subcloud peer group that was added in the source site and is now visible on the destination site after association")

    get_logger().log_test_case_step("Power off source site and check for alarms generate in destination site")
    PowerKeywords(src_site_ssh_conn).power_off("controller-0")
    PowerKeywords(src_site_ssh_conn).power_off("controller-1")
    AlarmListKeywords(dest_site_ssh_conn).alarm_list()

    get_logger().log_test_case_step("Destination site: Migrate subcloud peer group and validate if the subcloud is rehomed")
    password = ConfigurationManager.get_lab_config().get_secondary_system_controller_config().get_admin_credentials().get_password()
    DcManagerSubcloudPeerGroupMigrateKeywords(dest_site_ssh_conn).dcmanager_subcloud_peer_group_migrate(dest_subcloud_peer_group_id, password)
    DcManagerSubcloudPeerGroupStatusKeywords(dest_site_ssh_conn).get_dcmanager_subcloud_peer_group_status(dest_subcloud_peer_group_id)
    DcManagerSubcloudListKeywords(dest_site_ssh_conn).get_dcmanager_subcloud_list()
    DcManagerSubcloudListKeywords(dest_site_ssh_conn).validate_subcloud_status(subcloud_name, "rehoming")
    DcManagerSubcloudListKeywords(dest_site_ssh_conn).validate_subcloud_status(subcloud_name, "complete")
    DcManagerSubcloudListKeywords(dest_site_ssh_conn).validate_subcloud_availability_status(subcloud_name)
    DcManagerSubcloudListKeywords(dest_site_ssh_conn).get_dcmanager_subcloud_list_all()
    DcManagerSubcloudPeerGroupListSubcloudsKeywords(dest_site_ssh_conn).get_dcmanager_subcloud_peer_group_list_subclouds(dest_subcloud_peer_group_id)
    spg_status = DcManagerSubcloudPeerGroupStatusKeywords(dest_site_ssh_conn).get_dcmanager_subcloud_peer_group_status(dest_subcloud_peer_group_id)

    validate_not_equals(spg_status.get_dcmanager_subcloud_peer_group_status_object().get_complete(), 0, f"Subcloud peer group {dest_subcloud_peer_group_id} is migrated and subcloud is rehomed")
