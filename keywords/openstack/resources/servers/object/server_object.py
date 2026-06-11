"""Server object representation."""

from typing import Dict, List, Optional


class ServerObject:
    """Represents a single OpenStack Nova server.

    Mirrors the parser-then-typed-object pattern used elsewhere under
    ``keywords/openstack/resources/`` (FlavorObject, NetworkObject, etc.):
    keyword methods return wrappers like this instead of raw SDK dicts so
    tests get a stable, type-safe surface even if the upstream SDK shape
    changes.
    """

    def __init__(self) -> None:
        """Initialize an empty ServerObject."""
        self._properties: dict = {}

    def set_property(self, key: str, value: object) -> None:
        """Set a property value.

        Args:
            key (str): Property name.
            value (object): Property value.
        """
        self._properties[key] = value

    def get_property(self, key: str) -> object:
        """Get a property value.

        Args:
            key (str): Property name.

        Returns:
            object: Property value, or None if not set.
        """
        return self._properties.get(key)

    def get_id(self) -> str:
        """Get the server ID.

        Returns:
            str: Server UUID, or empty string if unset.
        """
        return self._properties.get("id", "")

    def set_id(self, server_id: str) -> None:
        """Set the server ID.

        Args:
            server_id (str): Server UUID.
        """
        self._properties["id"] = server_id

    def get_name(self) -> str:
        """Get the server name.

        Returns:
            str: Server name, or empty string if unset.
        """
        return self._properties.get("name", "")

    def set_name(self, name: str) -> None:
        """Set the server name.

        Args:
            name (str): Server name.
        """
        self._properties["name"] = name

    def get_status(self) -> str:
        """Get the server status (uppercase, e.g. ACTIVE / SHUTOFF / ERROR).

        Returns:
            str: Server status, or empty string if unset.
        """
        return (self._properties.get("status") or "").upper()

    def set_status(self, status: str) -> None:
        """Set the server status.

        Args:
            status (str): Server status string.
        """
        self._properties["status"] = status

    def get_image_id(self) -> str:
        """Get the boot image ID, if any.

        Returns:
            str: Image UUID, or empty string if booted from volume.
        """
        image = self._properties.get("image")
        if isinstance(image, dict):
            return image.get("id", "") or ""
        if isinstance(image, str):
            return image
        return ""

    def set_image(self, image: object) -> None:
        """Set the image attribute (raw SDK shape: dict or string).

        Args:
            image (object): Image dict or ID string from the SDK.
        """
        self._properties["image"] = image

    def get_flavor_id(self) -> str:
        """Get the flavor ID.

        Returns:
            str: Flavor UUID, or empty string if unset.
        """
        flavor = self._properties.get("flavor")
        if isinstance(flavor, dict):
            return flavor.get("id", flavor.get("original_name", "")) or ""
        if isinstance(flavor, str):
            return flavor
        return ""

    def get_flavor_name(self) -> str:
        """Get the flavor name (original_name on modern API).

        Returns:
            str: Flavor name, or empty string if unset.
        """
        flavor = self._properties.get("flavor")
        if isinstance(flavor, dict):
            return flavor.get("original_name", flavor.get("name", "")) or ""
        return ""

    def set_flavor(self, flavor: object) -> None:
        """Set the flavor attribute.

        Args:
            flavor (object): Flavor dict or ID string from the SDK.
        """
        self._properties["flavor"] = flavor

    def get_metadata(self) -> Dict[str, str]:
        """Get the server metadata dict.

        Returns:
            Dict[str, str]: Server metadata key/value pairs.
        """
        return dict(self._properties.get("metadata") or {})

    def set_metadata(self, metadata: Dict[str, str]) -> None:
        """Set the server metadata dict.

        Args:
            metadata (Dict[str, str]): Metadata key/value pairs.
        """
        self._properties["metadata"] = dict(metadata or {})

    def get_addresses(self) -> Dict[str, list]:
        """Get the addresses dict (keyed by network name).

        Returns:
            Dict[str, list]: Addresses keyed by network name.
        """
        return dict(self._properties.get("addresses") or {})

    def set_addresses(self, addresses: Dict[str, list]) -> None:
        """Set the addresses dict.

        Args:
            addresses (Dict[str, list]): Addresses keyed by network name.
        """
        self._properties["addresses"] = dict(addresses or {})

    def get_fault(self) -> Optional[Dict]:
        """Get the fault dict (present when status is ERROR).

        Returns:
            Optional[Dict]: Fault dict, or None.
        """
        fault = self._properties.get("fault")
        return dict(fault) if isinstance(fault, dict) else None

    def set_fault(self, fault: Optional[Dict]) -> None:
        """Set the fault dict.

        Args:
            fault (Optional[Dict]): Fault dict.
        """
        self._properties["fault"] = fault

    def get_availability_zone(self) -> str:
        """Get the availability zone.

        Returns:
            str: Availability zone, or empty string if unset.
        """
        return self._properties.get("availability_zone", "") or ""

    def get_host(self) -> str:
        """Get the compute host (admin-only attribute, may be empty).

        Returns:
            str: Compute hostname.
        """
        return self._properties.get("compute_host") or self._properties.get("hypervisor_hostname") or self._properties.get("OS-EXT-SRV-ATTR:host") or ""

    def get_security_groups(self) -> List[str]:
        """Get the list of attached security group names.

        Returns:
            List[str]: Security group names.
        """
        sgs = self._properties.get("security_groups") or []
        result = []
        for sg in sgs:
            if isinstance(sg, dict):
                name = sg.get("name")
                if name:
                    result.append(name)
            elif isinstance(sg, str):
                result.append(sg)
        return result

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"ServerObject(name={self.get_name()}, id={self.get_id()}, " f"status={self.get_status()}, flavor={self.get_flavor_name()})"
