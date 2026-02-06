from typing import List

from keywords.k8s.kube_cpusets.object.kube_cpusets_object import KubeCpusetsObject
from keywords.k8s.kube_cpusets.object.kube_cpusets_table_parser import KubeCpusetsTableParser


class KubeCpusetsOutput:
    """Parses kube-cpusets command output."""

    def __init__(self, output: str):
        """Initialize KubeCpusetsOutput.

        Args:
            output (str): Raw output from kube-cpusets command.
        """
        self.containers: List[KubeCpusetsObject] = []
        self._parse_output(output)

    def _parse_output(self, output: str) -> None:
        """Parse kube-cpusets output.

        Args:
            output (str): Raw output from kube-cpusets command.
        """
        lines = output.split("\n")
        table_start = next((i for i, line in enumerate(lines) if "Per-container cpusets:" in line), -1)
        table_end = next((i for i, line in enumerate(lines) if "Logical cpusets usage per numa node:" in line), len(lines))

        if table_start == -1:
            return

        table_output = "\n".join(lines[table_start + 1 : table_end])
        parser = KubeCpusetsTableParser(table_output)
        values = parser.get_output_values_list()

        for value in values:
            container = KubeCpusetsObject()
            container.set_namespace(value.get("namespace", ""))
            container.set_pod_name(value.get("pod.name", ""))
            container.set_container_name(value.get("container.name", ""))
            container.set_container_id(value.get("container.id", ""))
            container.set_state(value.get("state", ""))
            container.set_qos(value.get("QoS", ""))
            container.set_shares(int(value.get("shares", 0)))
            container.set_group(value.get("group", ""))
            container.set_cpus(value.get("cpus", ""))
            self.containers.append(container)

    def get_containers(self) -> List[KubeCpusetsObject]:
        """Get all containers.

        Returns:
            List[KubeCpusetsObject]: List of container objects.
        """
        return self.containers

    def get_containers_by_namespace(self, namespace: str) -> List[KubeCpusetsObject]:
        """Get containers by namespace.

        Args:
            namespace (str): Namespace to filter by.

        Returns:
            List[KubeCpusetsObject]: Filtered list of containers.
        """
        return [c for c in self.containers if c.get_namespace() == namespace]

    def get_containers_by_pod_name(self, pod_name: str) -> List[KubeCpusetsObject]:
        """Get containers by pod name pattern.

        Args:
            pod_name (str): Pod name pattern to match.

        Returns:
            List[KubeCpusetsObject]: Filtered list of containers.
        """
        return [c for c in self.containers if pod_name in c.get_pod_name()]

    def get_containers_by_group(self, group: str) -> List[KubeCpusetsObject]:
        """Get containers by group.

        Args:
            group (str): Group to filter by.

        Returns:
            List[KubeCpusetsObject]: Filtered list of containers.
        """
        return [c for c in self.containers if c.get_group() == group]
