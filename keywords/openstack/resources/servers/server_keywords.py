"""Server CRUD keywords via OpenStack SDK."""

import time
from typing import List, Optional

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.flavors.flavor_keywords import FlavorKeywords
from keywords.openstack.resources.images.image_keywords import ImageKeywords
from keywords.openstack.resources.networks.network_keywords import NetworkKeywords
from keywords.openstack.resources.servers.object.server_interface_list_output import ServerInterfaceListOutput
from keywords.openstack.resources.servers.object.server_list_output import ServerListOutput


class ServerKeywords(BaseKeyword):
    """CRUD operations for Nova servers via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize ServerKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def create_server(
        self,
        server_name: str,
        image: Optional[str] = None,
        flavor: Optional[str] = None,
        network: Optional[str] = None,
        availability_zone: Optional[str] = None,
        block_device_mapping_v2: Optional[List[dict]] = None,
    ) -> ServerListOutput:
        """Create a server.

        Auto-discovers image, flavor, and network if not provided using
        ImageKeywords, FlavorKeywords, and NetworkKeywords.

        Args:
            server_name (str): Server name.
            image (Optional[str]): Image name. Auto-discovered if None.
            flavor (Optional[str]): Flavor name. Auto-discovered if None.
            network (Optional[str]): Network name. Auto-discovered if None.
            availability_zone (Optional[str]): Availability zone (e.g. 'nova:controller-0').
            block_device_mapping_v2 (Optional[List[dict]]): Block device mappings for boot-from-volume.

        Returns:
            ServerListOutput: Created server output.
        """
        if not flavor:
            flavor_output = FlavorKeywords(self.openstack_connection).list_flavors()
            flavor_details = flavor_output.discover_flavor()
            flavor = flavor_details.get_name()
        if not network:
            network_details = NetworkKeywords(self.openstack_connection).discover_internal_network()
            network = network_details.get_name()

        compute = self.openstack_connection.get_compute()
        image_service = self.openstack_connection.get_image()
        network_service = self.openstack_connection.get_network()

        boot_from_volume = block_device_mapping_v2 and any(
            bdm.get("boot_index") == 0 for bdm in block_device_mapping_v2
        )

        image_id = None
        if not boot_from_volume:
            if not image:
                image_output = ImageKeywords(self.openstack_connection).list_images()
                image_details = image_output.discover_image()
                image = image_details.get_name()
            image_id = image_service.find_image(image).id

        get_logger().log_info(
            f"Creating server '{server_name}' (image={image}, flavor={flavor}, "
            f"network={network}, az={availability_zone})"
        )

        flavor_id = compute.find_flavor(flavor).id
        network_id = network_service.find_network(network).id
        
        server = compute.create_server(
            name=server_name,
            flavor_id=flavor_id,
            networks=[{"uuid": network_id}],
            image_id=image_id,
            availability_zone=availability_zone,
            block_device_mapping=block_device_mapping_v2,
        )
        return ServerListOutput([server.to_dict()])

    def get_server(self, server_name_or_id: str) -> ServerListOutput:
        """Get server details as a typed object.

        Args:
            server_name_or_id (str): Server name or ID.

        Returns:
            ServerListOutput: Parsed server output with all fields populated.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        server_detail = compute.get_server(server.id)
        return ServerListOutput([server_detail.to_dict()])

    def list_servers(self) -> ServerListOutput:
        """List all servers.

        Returns:
            ServerListOutput: Parsed server collection.
        """
        raw = [s.to_dict() for s in self.openstack_connection.get_compute().servers()]
        return ServerListOutput(raw)

    def update_server(self, server_name_or_id: str, new_name: Optional[str] = None) -> ServerListOutput:
        """Update a server's name.

        Args:
            server_name_or_id (str): Server name or ID.
            new_name (Optional[str]): New server name.

        Returns:
            ServerListOutput: Updated server output.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        attrs = {}
        if new_name:
            attrs["name"] = new_name
        updated = compute.update_server(server.id, **attrs)
        return ServerListOutput([updated.to_dict()])

    def set_server_metadata(self, server_name_or_id: str, metadata: dict) -> ServerListOutput:
        """Set metadata on a server.

        Args:
            server_name_or_id (str): Server name or ID.
            metadata (dict): Key-value pairs to set.

        Returns:
            ServerListOutput: Updated server output.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        compute.set_server_metadata(server.id, **metadata)
        return self.get_server(server.id)

    def delete_server(self, server_name_or_id: str) -> None:
        """Delete a server and wait for removal.

        Args:
            server_name_or_id (str): Server name or ID.
        """
        get_logger().log_info(f"Deleting server '{server_name_or_id}'")
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        compute.delete_server(server.id)
        compute.wait_for_delete(server)

    def wait_for_server_status(
        self,
        server_name_or_id: str,
        expected_status: str,
        timeout: int = 300,
        poll_interval: int = 10,
    ) -> ServerListOutput:
        """Poll until server reaches expected status.

        Args:
            server_name_or_id (str): Server name or ID.
            expected_status (str): Expected status string (e.g. 'ACTIVE').
            timeout (int): Maximum wait time in seconds.
            poll_interval (int): Seconds between polls.

        Returns:
            ServerListOutput: Server output once status is reached.

        Raises:
            TimeoutError: If status is not reached within timeout.
            RuntimeError: If server enters ERROR state.
        """
        compute = self.openstack_connection.get_compute()
        end_time = time.time() + timeout
        while time.time() < end_time:
            server = compute.find_server(server_name_or_id, ignore_missing=False)
            server_detail = compute.get_server(server.id)
            current_status = server_detail.status.upper()
            if current_status == expected_status.upper():
                get_logger().log_info(f"Server '{server_name_or_id}' reached status '{expected_status}'")
                return ServerListOutput([server_detail.to_dict()])
            if current_status == "ERROR":
                fault = server_detail.to_dict().get("fault", {})
                msg = fault.get("message", "Unknown error") if isinstance(fault, dict) else str(fault)
                raise RuntimeError(f"Server '{server_name_or_id}' entered ERROR state: {msg}")
            get_logger().log_info(f"Server '{server_name_or_id}' status is '{server_detail.status}', waiting for '{expected_status}'...")
            time.sleep(poll_interval)
        raise TimeoutError(f"Server '{server_name_or_id}' did not reach '{expected_status}' within {timeout}s")

    def is_server_gone(self, server_name_or_id: str) -> bool:
        """Check if a server no longer exists.

        Args:
            server_name_or_id (str): Server name or ID.

        Returns:
            bool: True if server is not found or is in a deleted state.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id)
        if server is None:
            return True
        server_detail = compute.get_server(server.id)
        return server_detail.status.upper() in ("DELETED", "SOFT_DELETED")

    def cleanup_server(self, server_name_or_id: str) -> None:
        """Safely delete a server if it exists. Does not raise on failure.

        Args:
            server_name_or_id (str): Server name or ID.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=True)
        if server is None:
            get_logger().log_info(f"Server '{server_name_or_id}' already gone, skipping cleanup")
            return
        try:
            compute.delete_server(server.id)
            compute.wait_for_delete(server)
            get_logger().log_info(f"Cleaned up server: {server_name_or_id}")
        except Exception as e:
            get_logger().log_warning(f"Server cleanup failed for '{server_name_or_id}': {e}")

    def verify_servers_evacuated(
        self,
        server_ids: List[str],
        rebooted_host: str,
    ) -> None:
        """Verify servers evacuated from a rebooted host and are ACTIVE.

        Checks that each server has status ACTIVE and is no longer on the
        rebooted host.

        Args:
            server_ids (List[str]): List of server IDs to verify.
            rebooted_host (str): Hostname of the host that was rebooted.

        Raises:
            AssertionError: If any server is not ACTIVE or still on rebooted host.
        """
        for server_id in server_ids:
            server_output = self.get_server(server_id)
            server_obj = server_output.get_servers()[0]
            validate_equals(
                server_obj.get_status(), "ACTIVE",
                f"Server {server_obj.get_name()} is ACTIVE after evacuation",
            )
            validate_not_equals(
                server_obj.get_host(), rebooted_host,
                f"Server {server_obj.get_name()} evacuated from {rebooted_host}",
            )
            get_logger().log_info(f"{server_obj.get_name()}: evacuated {rebooted_host} -> {server_obj.get_host()}")

    def live_migrate_server(self, server_name_or_id: str, destination_host: str = None) -> None:
        """Live-migrate a server to another host without downtime.

        Args:
            server_name_or_id (str): Server name or ID to migrate.
            destination_host (str): Target compute host. If None, Nova scheduler picks.

        Raises:
            RuntimeError: If server enters ERROR state after migration.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        get_logger().log_info(
            f"Live-migrating server '{server_name_or_id}' to host '{destination_host or 'auto'}'"
        )
        compute.live_migrate_server(server.id, host=destination_host)

    def attach_interface(
        self,
        server_name_or_id: str,
        network_name_or_id: Optional[str] = None,
        port_id: Optional[str] = None,
    ) -> ServerInterfaceListOutput:
        """Attach a network interface to a server.

        Exactly one of network_name_or_id or port_id must be provided.

        Args:
            server_name_or_id (str): Server name or ID.
            network_name_or_id (Optional[str]): Network to attach via auto-created port.
            port_id (Optional[str]): Pre-existing port ID to attach.

        Returns:
            ServerInterfaceListOutput: Parsed interface attachment output.

        Raises:
            ValueError: If neither or both of network and port are provided.
        """
        if (network_name_or_id is None) == (port_id is None):
            raise ValueError("Provide exactly one of network_name_or_id or port_id")
        compute = self.openstack_connection.get_compute()
        network_service = self.openstack_connection.get_network()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        if network_name_or_id is not None:
            network = network_service.find_network(network_name_or_id, ignore_missing=False)
            get_logger().log_info(f"Attaching network '{network_name_or_id}' to server '{server_name_or_id}'")
            attachment = compute.create_server_interface(server.id, net_id=network.id)
        else:
            get_logger().log_info(f"Attaching port '{port_id}' to server '{server_name_or_id}'")
            attachment = compute.create_server_interface(server.id, port_id=port_id)
        return ServerInterfaceListOutput([attachment.to_dict()])

    def detach_interface(self, server_name_or_id: str, port_id: str) -> None:
        """Detach a network interface from a server.

        Args:
            server_name_or_id (str): Server name or ID.
            port_id (str): Port ID to detach.
        """
        get_logger().log_info(f"Detaching port '{port_id}' from server '{server_name_or_id}'")
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        compute.delete_server_interface(port_id, server=server.id)

    def list_interfaces(self, server_name_or_id: str) -> ServerInterfaceListOutput:
        """List interfaces attached to a server.

        Args:
            server_name_or_id (str): Server name or ID.

        Returns:
            ServerInterfaceListOutput: Parsed interface collection.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        raw = [i.to_dict() for i in compute.server_interfaces(server.id)]
        return ServerInterfaceListOutput(raw)

