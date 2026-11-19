"""Output object for 'calicoctl get workloadendpoints'."""

from keywords.k8s.calico.object.calicoctl_workload_endpoint_object import CalicoctlWorkloadEndpointObject
from keywords.k8s.calico.object.calicoctl_workload_endpoints_table_parser import CalicoctlWorkloadEndpointsTableParser


class CalicoctlWorkloadEndpointsOutput:
    """Parsed output of 'calicoctl get workloadendpoints'."""

    def __init__(self, raw_output: str | list[str]):
        """Parse the raw calicoctl workload endpoints output.

        Args:
            raw_output (str | list[str]): Raw SSH command output.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else str(raw_output)
        lines = [line for line in content.splitlines() if line.strip()]

        self.workload_endpoints: list[CalicoctlWorkloadEndpointObject] = []
        if not lines:
            return
        for row in CalicoctlWorkloadEndpointsTableParser(lines).get_output_values_list():
            endpoint = CalicoctlWorkloadEndpointObject(row.get("WORKLOAD", ""))
            endpoint.set_node(row.get("NODE", ""))
            endpoint.set_networks(row.get("NETWORKS", ""))
            endpoint.set_interface(row.get("INTERFACE", ""))
            self.workload_endpoints.append(endpoint)

    def get_workload_endpoints(self) -> list[CalicoctlWorkloadEndpointObject]:
        """Get all workload endpoints.

        Returns:
            list[CalicoctlWorkloadEndpointObject]: The parsed workload endpoints.
        """
        return self.workload_endpoints

    def get_workload_endpoint(self, workload: str) -> CalicoctlWorkloadEndpointObject:
        """Get the workload endpoint of a given workload.

        Args:
            workload (str): The workload (pod) name.

        Returns:
            CalicoctlWorkloadEndpointObject: The matching workload endpoint.

        Raises:
            ValueError: If no workload endpoint exists for that workload.
        """
        for endpoint in self.workload_endpoints:
            if endpoint.get_workload() == workload:
                return endpoint
        raise ValueError(f"No workload endpoint found for workload '{workload}'.")

    def has_workload_endpoint(self, workload: str) -> bool:
        """Check whether a workload has a workload endpoint.

        Args:
            workload (str): The workload (pod) name.

        Returns:
            bool: True if a workload endpoint exists for that workload.
        """
        return any(endpoint.get_workload() == workload for endpoint in self.workload_endpoints)

    def __str__(self) -> str:
        """Human-readable representation of the workload endpoints.

        Returns:
            str: The workload names.
        """
        return f"CalicoctlWorkloadEndpointsOutput(workloads={[endpoint.get_workload() for endpoint in self.workload_endpoints]})"
