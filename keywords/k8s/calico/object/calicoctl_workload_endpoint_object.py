"""Object for one row of 'calicoctl get workloadendpoints'."""


class CalicoctlWorkloadEndpointObject:
    """One workload endpoint row of 'calicoctl get workloadendpoints'."""

    def __init__(self, workload: str):
        """Initialize the workload endpoint object.

        Args:
            workload (str): The workload (pod) name.
        """
        self.workload = workload
        self.node = ""
        self.networks = ""
        self.interface = ""

    def get_workload(self) -> str:
        """Get the workload (pod) name.

        Returns:
            str: The workload name.
        """
        return self.workload

    def set_node(self, node: str) -> None:
        """Set the node the workload runs on.

        Args:
            node (str): The node name.
        """
        self.node = node

    def get_node(self) -> str:
        """Get the node the workload runs on.

        Returns:
            str: The node name.
        """
        return self.node

    def set_networks(self, networks: str) -> None:
        """Set the workload networks.

        Args:
            networks (str): Comma-separated CIDRs assigned to the workload.
        """
        self.networks = networks

    def get_networks(self) -> list[str]:
        """Get the workload networks.

        Returns:
            list[str]: The CIDRs assigned to the workload.
        """
        return [network for network in self.networks.split(",") if network]

    def set_interface(self, interface: str) -> None:
        """Set the host-side interface of the workload.

        Args:
            interface (str): The interface name (e.g. 'cali49e236b6105').
        """
        self.interface = interface

    def get_interface(self) -> str:
        """Get the host-side interface of the workload.

        Returns:
            str: The interface name.
        """
        return self.interface

    def __str__(self) -> str:
        """Human-readable representation of the workload endpoint.

        Returns:
            str: The workload, node and networks.
        """
        return f"CalicoctlWorkloadEndpointObject(workload={self.workload}, node={self.node}, networks={self.networks})"
