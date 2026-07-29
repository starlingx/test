import json
from typing import Dict, List, Union


class CephMgrServicesOutput:
    """Parses the output of the 'ceph mgr services' command.

    The command returns a JSON object mapping each enabled mgr service to the
    URL it is served on, for example::

        {
            "restful": "https://controller-0:7999/"
        }

    The set of services is dynamic (it depends on which mgr modules are
    enabled), so this class exposes generic lookup methods rather than
    per-service accessors.
    """

    def __init__(self, ceph_mgr_services_output: Union[str, List[str]]):
        """Constructor.

        Args:
            ceph_mgr_services_output (Union[str, List[str]]): Raw output from
                running the 'ceph mgr services' command.
        """
        content = "\n".join(ceph_mgr_services_output) if isinstance(ceph_mgr_services_output, list) else str(ceph_mgr_services_output)
        self.services: Dict[str, str] = json.loads(content)

    def get_services(self) -> Dict[str, str]:
        """Get all mgr services and their URLs.

        Returns:
            Dict[str, str]: Mapping of service name to service URL.
        """
        return self.services

    def get_service_names(self) -> List[str]:
        """Get the names of all enabled mgr services.

        Returns:
            List[str]: Service names (e.g. ['prometheus', 'restful']).
        """
        return list(self.services.keys())

    def has_service(self, service_name: str) -> bool:
        """Check whether a mgr service is being served.

        Args:
            service_name (str): The service name to check (e.g. 'prometheus').

        Returns:
            bool: True if the service is present, False otherwise.
        """
        return service_name in self.services

    def get_service_url(self, service_name: str) -> str:
        """Get the URL a mgr service is served on.

        Args:
            service_name (str): The service name (e.g. 'prometheus').

        Returns:
            str: The service URL (e.g. 'http://controller-0:9283/').

        Raises:
            ValueError: If the service is not present.
        """
        if service_name not in self.services:
            raise ValueError(f"There is no mgr service named '{service_name}'. Available services: {self.get_service_names()}")
        return self.services[service_name]
