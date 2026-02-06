from typing import List


class KubeCpusetsObject:
    """Represents a container from kube-cpusets output."""

    def __init__(self):
        """Initialize KubeCpusetsObject."""
        self.namespace: str = None
        self.pod_name: str = None
        self.container_name: str = None
        self.container_id: str = None
        self.state: str = None
        self.qos: str = None
        self.shares: int = None
        self.group: str = None
        self.cpus: str = None

    def set_namespace(self, namespace: str) -> None:
        """Set namespace.

        Args:
            namespace (str): Namespace value.
        """
        self.namespace = namespace

    def get_namespace(self) -> str:
        """Get namespace.

        Returns:
            str: Namespace value.
        """
        return self.namespace

    def set_pod_name(self, pod_name: str) -> None:
        """Set pod name.

        Args:
            pod_name (str): Pod name value.
        """
        self.pod_name = pod_name

    def get_pod_name(self) -> str:
        """Get pod name.

        Returns:
            str: Pod name value.
        """
        return self.pod_name

    def set_container_name(self, container_name: str) -> None:
        """Set container name.

        Args:
            container_name (str): Container name value.
        """
        self.container_name = container_name

    def get_container_name(self) -> str:
        """Get container name.

        Returns:
            str: Container name value.
        """
        return self.container_name

    def set_container_id(self, container_id: str) -> None:
        """Set container ID.

        Args:
            container_id (str): Container ID value.
        """
        self.container_id = container_id

    def get_container_id(self) -> str:
        """Get container ID.

        Returns:
            str: Container ID value.
        """
        return self.container_id

    def set_state(self, state: str) -> None:
        """Set state.

        Args:
            state (str): State value.
        """
        self.state = state

    def get_state(self) -> str:
        """Get state.

        Returns:
            str: State value.
        """
        return self.state

    def set_qos(self, qos: str) -> None:
        """Set QoS.

        Args:
            qos (str): QoS value.
        """
        self.qos = qos

    def get_qos(self) -> str:
        """Get QoS.

        Returns:
            str: QoS value.
        """
        return self.qos

    def set_shares(self, shares: int) -> None:
        """Set shares.

        Args:
            shares (int): Shares value.
        """
        self.shares = shares

    def get_shares(self) -> int:
        """Get shares.

        Returns:
            int: Shares value.
        """
        return self.shares

    def set_group(self, group: str) -> None:
        """Set group.

        Args:
            group (str): Group value.
        """
        self.group = group

    def get_group(self) -> str:
        """Get group.

        Returns:
            str: Group value.
        """
        return self.group

    def set_cpus(self, cpus: str) -> None:
        """Set CPUs.

        Args:
            cpus (str): CPUs value.
        """
        self.cpus = cpus

    def get_cpus(self) -> str:
        """Get CPUs.

        Returns:
            str: CPUs value.
        """
        return self.cpus

    def get_cpu_list(self) -> List[int]:
        """Parse CPU string and return list of individual CPU numbers.

        Parses the cpus field which contains CPU assignments in various formats including
        ranges (e.g., "1-31"), comma-separated values (e.g., "0,32"), and combinations.
        The string may also include node information which is ignored during parsing.

        Returns:
            List[int]: List of individual CPU numbers assigned to this container.
                      Returns empty list if cpus field is None or empty.

        Examples:
            >>> obj = KubeCpusetsObject()
            >>> obj.set_cpus("node 0 0,32")
            >>> obj.get_cpu_list()
            [0, 32]

            >>> obj.set_cpus("node 0 1-31,33-63")
            >>> obj.get_cpu_list()
            [1, 2, 3, ..., 31, 33, 34, ..., 63]

        """
        if not self.cpus:
            return []

        cpu_list = []
        # Remove "node X" prefix if present
        cpu_str = self.cpus
        if cpu_str.startswith("node "):
            parts = cpu_str.split(maxsplit=2)
            cpu_str = parts[2] if len(parts) > 2 else ""

        # Split by comma first to handle "1-31,33-63"
        for part in cpu_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-")
                cpu_list.extend(range(int(start), int(end) + 1))
            elif part.isdigit():
                cpu_list.append(int(part))

        return cpu_list
