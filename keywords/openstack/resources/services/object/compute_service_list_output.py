"""Compute service list output parsing and manipulation."""

from typing import Dict, List

from framework.logging.automation_logger import get_logger

from keywords.openstack.resources.services.object.compute_service_object import ComputeServiceObject


class ComputeServiceListOutput:
    """Parses and provides access to a collection of ComputeServiceObjects."""

    def __init__(self, raw_services: List[Dict]) -> None:
        """Initialize ComputeServiceListOutput from raw service dicts.

        Args:
            raw_services (List[Dict]): List of service dictionaries from OpenStack SDK.
        """
        self._services = []
        for raw in raw_services:
            service = ComputeServiceObject()
            service.set_binary(raw.get("binary", ""))
            service.set_host(raw.get("host", ""))
            service.set_zone(raw.get("zone", raw.get("availability_zone", "")))
            service.set_status(raw.get("status", ""))
            service.set_state(raw.get("state", ""))
            service.set_updated_at(raw.get("updated_at", ""))
            self._services.append(service)

    def get_services(self) -> List[ComputeServiceObject]:
        """Get all compute service objects.

        Returns:
            List[ComputeServiceObject]: List of service objects.
        """
        return self._services

    def get_services_by_binary(self, binary: str) -> List[ComputeServiceObject]:
        """Get all services matching the binary name.

        Args:
            binary (str): Service binary (e.g. 'nova-compute').

        Returns:
            List[ComputeServiceObject]: List of matching services.
        """
        return [s for s in self._services if s.get_binary() == binary]

    def get_services_by_host(self, host: str) -> List[ComputeServiceObject]:
        """Get all services running on a specific host.

        Args:
            host (str): Host name (e.g. 'controller-0').

        Returns:
            List[ComputeServiceObject]: List of matching services.
        """
        return [s for s in self._services if s.get_host() == host]

    def get_compute_services(self) -> List[ComputeServiceObject]:
        """Get all nova-compute services.

        Returns:
            List[ComputeServiceObject]: List of nova-compute services.
        """
        return self.get_services_by_binary("nova-compute")

    def get_down_services(self) -> List[ComputeServiceObject]:
        """Get all services that are not up.

        Returns:
            List[ComputeServiceObject]: List of services with state != 'up'.
        """
        return [s for s in self._services if s.get_state() != "up"]

    def get_down_compute_services(self) -> List[ComputeServiceObject]:
        """Get nova-compute services that are not up.

        Returns:
            List[ComputeServiceObject]: List of down nova-compute services.
        """
        return [s for s in self.get_compute_services() if s.get_state() != "up"]

    def log_service_table(self) -> None:
        """Log the full compute service list as a formatted table."""
        get_logger().log_info("Compute Service List:")
        get_logger().log_info(
            f"  {'Binary':<20} {'Host':<25} {'Zone':<10} {'Status':<10} {'State':<6} {'Updated At'}"
        )
        get_logger().log_info(f"  {'-' * 100}")
        for service in self._services:
            get_logger().log_info(
                f"  {service.get_binary():<20} {service.get_host():<25} "
                f"{service.get_zone():<10} {service.get_status():<10} "
                f"{service.get_state():<6} {service.get_updated_at()}"
            )

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"ComputeServiceListOutput(count={len(self._services)})"
