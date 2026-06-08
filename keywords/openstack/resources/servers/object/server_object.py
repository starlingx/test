"""Object representing a Nova server."""


class ServerObject:
    """Holds the parsed fields from a Nova server."""

    def __init__(self):
        """Initialize ServerObject with explicit fields."""
        self.id = None
        self.name = None
        self.status = None
        self.host = None
        self.availability_zone = None
        self.flavor_id = None
        self.image_id = None
        self.addresses = None
        self.created_at = None
        self.updated_at = None
        self.tenant_id = None
        self.user_id = None
        self.key_name = None
        self.metadata = None

    def set_id(self, server_id: str) -> None:
        """Set the server ID.

        Args:
            server_id (str): Server ID.
        """
        self.id = server_id

    def get_id(self) -> str:
        """Get the server ID.

        Returns:
            str: Server ID.
        """
        return self.id

    def set_name(self, name: str) -> None:
        """Set the server name.

        Args:
            name (str): Server name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the server name.

        Returns:
            str: Server name.
        """
        return self.name

    def set_status(self, status: str) -> None:
        """Set the server status.

        Args:
            status (str): Server status (e.g. 'ACTIVE', 'BUILD', 'ERROR').
        """
        self.status = status

    def get_status(self) -> str:
        """Get the server status.

        Returns:
            str: Server status.
        """
        return self.status

    def set_host(self, host: str) -> None:
        """Set the compute host.

        Args:
            host (str): Hostname of the compute node.
        """
        self.host = host

    def get_host(self) -> str:
        """Get the compute host.

        Returns:
            str: Hostname of the compute node.
        """
        return self.host

    def set_availability_zone(self, availability_zone: str) -> None:
        """Set the availability zone.

        Args:
            availability_zone (str): Availability zone name.
        """
        self.availability_zone = availability_zone

    def get_availability_zone(self) -> str:
        """Get the availability zone.

        Returns:
            str: Availability zone name.
        """
        return self.availability_zone

    def set_flavor_id(self, flavor_id: str) -> None:
        """Set the flavor ID.

        Args:
            flavor_id (str): Flavor ID.
        """
        self.flavor_id = flavor_id

    def get_flavor_id(self) -> str:
        """Get the flavor ID.

        Returns:
            str: Flavor ID.
        """
        return self.flavor_id

    def set_image_id(self, image_id: str) -> None:
        """Set the image ID.

        Args:
            image_id (str): Image ID.
        """
        self.image_id = image_id

    def get_image_id(self) -> str:
        """Get the image ID.

        Returns:
            str: Image ID.
        """
        return self.image_id

    def set_addresses(self, addresses: dict) -> None:
        """Set the server addresses.

        Args:
            addresses (dict): Network-to-addresses mapping.
        """
        self.addresses = addresses

    def get_addresses(self) -> dict:
        """Get the server addresses.

        Returns:
            dict: Network-to-addresses mapping.
        """
        return self.addresses or {}

    def set_created_at(self, created_at: str) -> None:
        """Set the creation timestamp.

        Args:
            created_at (str): Creation timestamp.
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """Get the creation timestamp.

        Returns:
            str: Creation timestamp.
        """
        return self.created_at

    def set_updated_at(self, updated_at: str) -> None:
        """Set the update timestamp.

        Args:
            updated_at (str): Update timestamp.
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """Get the update timestamp.

        Returns:
            str: Update timestamp.
        """
        return self.updated_at

    def set_tenant_id(self, tenant_id: str) -> None:
        """Set the tenant/project ID.

        Args:
            tenant_id (str): Tenant ID.
        """
        self.tenant_id = tenant_id

    def get_tenant_id(self) -> str:
        """Get the tenant/project ID.

        Returns:
            str: Tenant ID.
        """
        return self.tenant_id

    def set_user_id(self, user_id: str) -> None:
        """Set the user ID.

        Args:
            user_id (str): User ID.
        """
        self.user_id = user_id

    def get_user_id(self) -> str:
        """Get the user ID.

        Returns:
            str: User ID.
        """
        return self.user_id

    def set_key_name(self, key_name: str) -> None:
        """Set the keypair name.

        Args:
            key_name (str): Keypair name.
        """
        self.key_name = key_name

    def get_key_name(self) -> str:
        """Get the keypair name.

        Returns:
            str: Keypair name.
        """
        return self.key_name

    def set_metadata(self, metadata: dict) -> None:
        """Set the server metadata.

        Args:
            metadata (dict): Key-value metadata.
        """
        self.metadata = metadata

    def get_metadata(self) -> dict:
        """Get the server metadata.

        Returns:
            dict: Key-value metadata.
        """
        return self.metadata or {}

    def get_first_ip(self, ip_version: int = 4) -> str:
        """Get the first IP address matching the specified version.

        Args:
            ip_version (int): IP version to look for (4 or 6).

        Returns:
            str: IP address, or empty string if not found.
        """
        for addr_list in self.get_addresses().values():
            for addr in addr_list:
                if addr.get("version") == ip_version:
                    return addr["addr"]
        return ""

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable server summary.
        """
        return f"[ID: {self.get_id()}, Name: {self.get_name()}, Status: {self.get_status()}, Host: {self.get_host()}]"
