"""Router list output parsing and access."""

from typing import Dict, List

from keywords.openstack.resources.networks.object.router_object import RouterObject


class RouterListOutput:
    """Parses and provides access to a collection of RouterObjects."""

    def __init__(self, raw_routers: List[Dict]) -> None:
        """Initialize RouterListOutput from raw router dicts.

        Args:
            raw_routers (List[Dict]): Raw router dicts from the
                openstacksdk Network resource.
        """
        self._routers: List[RouterObject] = []
        for raw in raw_routers:
            router = RouterObject()
            router.set_id(raw.get("id", ""))
            router.set_name(raw.get("name", ""))
            router.set_status(raw.get("status", ""))
            router.set_admin_state_up(raw.get("is_admin_state_up", raw.get("admin_state_up", True)))
            self._routers.append(router)

    def get_routers(self) -> List[RouterObject]:
        """Get all parsed router objects.

        Returns:
            List[RouterObject]: All routers in this output.
        """
        return self._routers

    def get_router_by_name(self, name: str) -> RouterObject:
        """Get a router by name.

        Args:
            name (str): Router name.

        Returns:
            RouterObject: Matching router.

        Raises:
            ValueError: If no router with the given name is found.
        """
        for router in self._routers:
            if router.get_name() == name:
                return router
        raise ValueError(f"Router '{name}' not found")

    def is_router_present(self, name: str) -> bool:
        """Check whether a router with the given name exists in this output.

        Args:
            name (str): Router name.

        Returns:
            bool: True if a matching router is present.
        """
        for router in self._routers:
            if router.get_name() == name:
                return True
        return False

    def __object_to_string__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Summary string for logs and debugging.
        """
        return f"RouterListOutput(count={len(self._routers)})"
