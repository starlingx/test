"""Object for the Envoy proxy Service created for a Gateway."""


class EnvoyServiceObject:
    """The Service that exposes the Envoy proxy of one Gateway."""

    def __init__(self, name: str, cluster_ip: str, node_ports: dict[int, int]):
        """Initialize the Envoy Service.

        Args:
            name (str): The Service name.
            cluster_ip (str): The Service ClusterIP.
            node_ports (dict[int, int]): Service port mapped to its NodePort.
        """
        self.name = name
        self.cluster_ip = cluster_ip
        self.node_ports = node_ports

    def get_name(self) -> str:
        """Get the Service name.

        Returns:
            str: The Service name.
        """
        return self.name

    def get_cluster_ip(self) -> str:
        """Get the Service ClusterIP.

        Returns:
            str: The ClusterIP.
        """
        return self.cluster_ip

    def get_node_port(self, port: int) -> int:
        """Get the NodePort allocated for a Service port.

        Args:
            port (int): The Service port (e.g. 80).

        Returns:
            int: The NodePort.

        Raises:
            ValueError: If the Service has no NodePort for that port.
        """
        if port not in self.node_ports:
            raise ValueError(f"Envoy Service {self.name} has no NodePort for port {port}; ports: {self.node_ports}")
        return self.node_ports[port]

    def __str__(self) -> str:
        """Human-readable representation of the Envoy Service.

        Returns:
            str: The Service name, ClusterIP and NodePorts.
        """
        return f"EnvoyServiceObject(name={self.name}, cluster_ip={self.cluster_ip}, node_ports={self.node_ports})"
