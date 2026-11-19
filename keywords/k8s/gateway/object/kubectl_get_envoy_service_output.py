"""Output object for 'kubectl get services -l <owning gateway label> -o yaml' in the Envoy namespace."""

import yaml

from keywords.k8s.gateway.object.envoy_service_object import EnvoyServiceObject


class KubectlGetEnvoyServiceOutput:
    """Parsed output of the Services selected by a Gateway's owning-gateway label."""

    def __init__(self, raw_output: str | list[str]):
        """Parse the raw Service list YAML output.

        Args:
            raw_output (str | list[str]): Raw SSH command output.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else raw_output
        data = yaml.safe_load(content) or {}
        self.services = [self.build_envoy_service_object_from_dict(item) for item in data.get("items") or []]

    @staticmethod
    def build_envoy_service_object_from_dict(service_dict: dict) -> EnvoyServiceObject:
        """Build an Envoy Service object from one parsed Service.

        Args:
            service_dict (dict): One parsed Service item.

        Returns:
            EnvoyServiceObject: The Envoy Service.
        """
        spec = service_dict.get("spec") or {}
        node_ports = {port["port"]: port["nodePort"] for port in spec.get("ports") or [] if port.get("nodePort")}
        return EnvoyServiceObject((service_dict.get("metadata") or {}).get("name"), spec.get("clusterIP"), node_ports)

    def get_envoy_service(self) -> EnvoyServiceObject:
        """Get the single Envoy Service of the Gateway.

        Returns:
            EnvoyServiceObject: The Envoy Service.

        Raises:
            ValueError: If the selector matched no Service or more than one.
        """
        if len(self.services) != 1:
            raise ValueError(f"Expected exactly one Envoy Service for the Gateway, found {[str(service) for service in self.services]}")
        return self.services[0]

    def __str__(self) -> str:
        """Human-readable representation of the selected Services.

        Returns:
            str: The selected Services.
        """
        return f"KubectlGetEnvoyServiceOutput(services={[str(service) for service in self.services]})"
