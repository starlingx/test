"""Server CRUD keywords via OpenStack SDK."""

import time
from typing import Dict, List, Optional

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.flavors.flavor_keywords import FlavorKeywords
from keywords.openstack.resources.images.image_keywords import ImageKeywords
from keywords.openstack.resources.networks.network_keywords import NetworkKeywords


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
    ) -> Dict:
        """Create a server.

        Auto-discovers image, flavor, and network if not provided using
        ImageKeywords, FlavorKeywords, and NetworkKeywords.

        Args:
            server_name (str): Server name.
            image (Optional[str]): Image name. Auto-discovered if None.
            flavor (Optional[str]): Flavor name. Auto-discovered if None.
            network (Optional[str]): Network name. Auto-discovered if None.

        Returns:
            Dict: Server details.
        """
        if not image:
            image_output = ImageKeywords(self.openstack_connection).list_images()
            image_details = image_output.discover_image()
            image = image_details.get_name()
        if not flavor:
            flavor_output = FlavorKeywords(self.openstack_connection).list_flavors()
            flavor_details = flavor_output.discover_flavor()
            flavor = flavor_details.get_name()
        if not network:
            network_details = NetworkKeywords(self.openstack_connection).discover_internal_network()
            network = network_details["name"]
        get_logger().log_info(f"Creating server '{server_name}' (image={image}, flavor={flavor}, network={network})")
        compute = self.openstack_connection.get_compute()
        image_service = self.openstack_connection.get_image()
        network_service = self.openstack_connection.get_network()
        server = compute.create_server(
            name=server_name,
            image_id=image_service.find_image(image).id,
            flavor_id=compute.find_flavor(flavor).id,
            networks=[{"uuid": network_service.find_network(network).id}],
        )
        return server.to_dict()

    def show_server(self, server_name_or_id: str) -> Dict:
        """Show server details.

        Args:
            server_name_or_id (str): Server name or ID.

        Returns:
            Dict: Server details.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        return compute.get_server(server.id).to_dict()

    def list_servers(self) -> List[Dict]:
        """List all servers.

        Returns:
            List[Dict]: List of server dicts.
        """
        return [s.to_dict() for s in self.openstack_connection.get_compute().servers()]

    def update_server(self, server_name_or_id: str, new_name: Optional[str] = None) -> Dict:
        """Update a server's name.

        Args:
            server_name_or_id (str): Server name or ID.
            new_name (Optional[str]): New server name.

        Returns:
            Dict: Updated server details.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        attrs = {}
        if new_name:
            attrs["name"] = new_name
        updated = compute.update_server(server.id, **attrs)
        return updated.to_dict()

    def set_server_metadata(self, server_name_or_id: str, metadata: Dict[str, str]) -> Dict:
        """Set metadata on a server.

        Args:
            server_name_or_id (str): Server name or ID.
            metadata (Dict[str, str]): Key-value pairs to set.

        Returns:
            Dict: Updated server details.
        """
        compute = self.openstack_connection.get_compute()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        compute.set_server_metadata(server.id, **metadata)
        return self.show_server(server.id)

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

    def wait_for_server_status(self, server_name_or_id: str, expected_status: str, timeout: int = 300, poll_interval: int = 10) -> Dict:
        """Poll until server reaches expected status.

        Args:
            server_name_or_id (str): Server name or ID.
            expected_status (str): Expected status string (e.g. 'ACTIVE').
            timeout (int): Maximum wait time in seconds.
            poll_interval (int): Seconds between polls.

        Returns:
            Dict: Server details once status is reached.

        Raises:
            TimeoutError: If status is not reached within timeout.
        """
        compute = self.openstack_connection.get_compute()
        end_time = time.time() + timeout
        while time.time() < end_time:
            server = compute.find_server(server_name_or_id, ignore_missing=False)
            server = compute.get_server(server.id)
            current_status = server.status.upper()
            if current_status == expected_status.upper():
                get_logger().log_info(f"Server '{server_name_or_id}' reached status '{expected_status}'")
                return server.to_dict()
            if current_status == "ERROR":
                fault = server.to_dict().get("fault", {})
                msg = fault.get("message", "Unknown error") if isinstance(fault, dict) else str(fault)
                raise RuntimeError(f"Server '{server_name_or_id}' entered ERROR state: {msg}")
            get_logger().log_info(f"Server '{server_name_or_id}' status is '{server.status}', waiting for '{expected_status}'...")
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
        server = compute.get_server(server.id)
        return server.status.upper() in ("DELETED", "SOFT_DELETED")

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
