"""Volume service list output parsing and manipulation."""

from typing import Dict, List

from framework.logging.automation_logger import get_logger

from keywords.openstack.resources.services.object.volume_service_object import VolumeServiceObject


class VolumeServiceListOutput:
    """Parses and provides access to a collection of VolumeServiceObjects."""

    def __init__(self, raw_services: List[Dict]) -> None:
        """Initialize VolumeServiceListOutput from raw service dicts.

        Args:
            raw_services (List[Dict]): List of service dictionaries from OpenStack SDK.
        """
        self._services = []
        for raw in raw_services:
            service = VolumeServiceObject()
            service.set_binary(raw.get("binary", ""))
            service.set_host(raw.get("host", ""))
            service.set_zone(raw.get("zone", raw.get("availability_zone", "")))
            service.set_status(raw.get("status", ""))
            service.set_state(raw.get("state", ""))
            service.set_updated_at(raw.get("updated_at", ""))
            self._services.append(service)

    def get_services(self) -> List[VolumeServiceObject]:
        """Get all volume service objects.

        Returns:
            List[VolumeServiceObject]: List of service objects.
        """
        return self._services

    def get_service_by_binary(self, binary: str) -> VolumeServiceObject:
        """Get the first service matching the binary name.

        Args:
            binary (str): Service binary (e.g. 'cinder-volume').

        Returns:
            VolumeServiceObject: Matching service.

        Raises:
            ValueError: If no service with the given binary is found.
        """
        for service in self._services:
            if service.get_binary() == binary:
                return service
        raise ValueError(f"Volume service '{binary}' not found")

    def get_services_by_binary(self, binary: str) -> List[VolumeServiceObject]:
        """Get all services matching the binary name.

        Args:
            binary (str): Service binary (e.g. 'cinder-volume').

        Returns:
            List[VolumeServiceObject]: List of matching services.
        """
        return [s for s in self._services if s.get_binary() == binary]

    def filter_by_backend(self, backend_name: str) -> List[VolumeServiceObject]:
        """Get services whose host contains the given backend name.

        Extracts the backend from the host field using host.split('@')[1].

        Args:
            backend_name (str): Backend name to filter by (e.g. 'ceph-rook-store').

        Returns:
            List[VolumeServiceObject]: Services matching the backend.
        """
        result = []
        for service in self._services:
            host = service.get_host()
            if "@" in host:
                service_backend = host.split("@")[1]
                if service_backend == backend_name:
                    result.append(service)
        return result

    def are_backends_up(self, backend_names: List[str]) -> bool:
        """Check if all services for the given backends are up.

        Args:
            backend_names (List[str]): List of backend names to check.

        Returns:
            bool: True if all matching services have state 'up'.
        """
        for backend in backend_names:
            services = self.filter_by_backend(backend)
            for service in services:
                if service.get_state() != "up":
                    return False
        return True

    def are_backends_down(self, backend_names: List[str]) -> bool:
        """Check if all services for the given backends are down.

        Args:
            backend_names (List[str]): List of backend names to check.

        Returns:
            bool: True if all matching services have state 'down'.
        """
        for backend in backend_names:
            services = self.filter_by_backend(backend)
            for service in services:
                if service.get_state() != "down":
                    return False
        return True

    def get_targeted_volume_services(self, targets: List[str]) -> List[VolumeServiceObject]:
        """Get cinder-volume services matching the target backend list.

        Filters services to only cinder-volume binary, extracts the backend
        name from the host field (host.split('@')[1]), and returns only those
        matching the provided targets.

        Args:
            targets (List[str]): List of backend names to look for
                (e.g. ['ceph-rook-store', 'netapp-nfs', 'netapp-iscsi', 'netapp-fc']).

        Returns:
            List[VolumeServiceObject]: Matching cinder-volume services.
        """
        result = []
        volume_services = self.get_services_by_binary("cinder-volume")
        for service in volume_services:
            host = service.get_host()
            if "@" in host:
                backend = host.split("@")[1]
                if backend in targets:
                    result.append(service)
        return result

    def log_full_service_table(self) -> None:
        """Log the full volume service list as a formatted table.

        Logs binary, host, zone, status, state, and updated_at for every service.
        """
        get_logger().log_info("Volume Service List:")
        get_logger().log_info(
            f"  {'Binary':<20} {'Host':<45} {'Zone':<6} {'Status':<10} {'State':<6} {'Updated At'}"
        )
        get_logger().log_info(f"  {'-' * 120}")
        for service in self._services:
            get_logger().log_info(
                f"  {service.get_binary():<20} {service.get_host():<45} "
                f"{service.get_zone():<6} {service.get_status():<10} "
                f"{service.get_state():<6} {service.get_updated_at()}"
            )

    def get_down_services(self) -> List[VolumeServiceObject]:
        """Get all services that are not up.

        Returns:
            List[VolumeServiceObject]: List of services that are down or disabled.
        """
        return [s for s in self._services if not s.is_up()]

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"VolumeServiceListOutput(count={len(self._services)})"
