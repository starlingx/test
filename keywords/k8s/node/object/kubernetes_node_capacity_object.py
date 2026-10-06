from typing import Dict

from framework.exceptions.keyword_exception import KeywordException


class KubernetesNodeCapacityObject:
    """
    Class to hold attributes of a Kubernetes Node's Capacity
    """

    def __init__(self):
        """
        Constructor
        """

        self.cpu: int = -1
        self.ephemeral_storage: str = None
        self.hugepages_1gi: str = None
        self.hugepages_2mi: str = None
        self.memory: str = None
        self.pods: int = -1
        self.windriver_isolcpus: int = -1
        self.intel_dummy = -1
        # Allocatable VF count keyed by datanetwork name
        self.sriov_datanetwork_allocatable: Dict[str, int] = {}

    def set_cpu(self, cpu: int):
        """
        Setter for the cpu
        Args:
            cpu:
        """
        self.cpu = cpu

    def get_cpu(self) -> int:
        """
        Getter for the cpu
        Returns: (int)

        """
        return self.cpu

    def set_ephemeral_storage(self, ephemeral_storage: str):
        """
        Setter for the ephemeral_storage
        Args:
            ephemeral_storage:
        """
        self.ephemeral_storage = ephemeral_storage

    def get_ephemeral_storage(self) -> str:
        """
        Getter for the ephemeral_storage
        Returns: (str)

        """
        return self.ephemeral_storage

    def set_hugepages_1gi(self, hugepages_1gi: str):
        """
        Setter for the hugepages_1gi
        Args:
            hugepages_1gi:
        """
        self.hugepages_1gi = hugepages_1gi

    def get_hugepages_1gi(self) -> str:
        """
        Getter for the hugepages_1gi
        Returns: (str)

        """
        return self.hugepages_1gi

    def set_hugepages_2mi(self, hugepages_2mi: str):
        """
        Setter for the hugepages_2mi
        Args:
            hugepages_2mi:
        """
        self.hugepages_2mi = hugepages_2mi

    def get_hugepages_2mi(self) -> str:
        """
        Getter for the hugepages_2mi
        Returns: (str)

        """
        return self.hugepages_2mi

    def set_memory(self, memory: str):
        """
        Setter for the memory
        Args:
            memory:
        """
        self.memory = memory

    def get_memory(self) -> str:
        """
        Getter for the memory
        Returns: (str)

        """
        return self.memory

    def set_pods(self, pods: int):
        """
        Setter for the pods
        Args:
            pods:
        """
        self.pods = pods

    def get_pods(self) -> int:
        """
        Getter for the pods
        Returns: (int)

        """
        return self.pods

    def set_windriver_isolcpus(self, windriver_isolcpus: int):
        """
        Setter for the windriver_isolcpus
        Args:
            isolcpus:
        """
        self.windriver_isolcpus = windriver_isolcpus

    def get_windriver_isolcpus(self) -> int:
        """
        Getter for the windriver_isolcpus
        Returns: (int)

        """
        return self.windriver_isolcpus

    def set_intel_dummy(self, intel_dummy):
        """
        Setter for intel dummy
        Args:
            intel_dummy (): the intel dummy value

        Returns:

        """
        self.intel_dummy = intel_dummy

    def get_intel_dummy(self) -> int:
        """
        Getter for intel dummy
        Returns:

        """
        return self.intel_dummy

    def set_sriov_datanetwork_allocatable(self, datanetwork: str, allocatable: int):
        """
        Set the allocatable VF count for a datanetwork.

        Args:
            datanetwork (str): the datanetwork name (e.g. "group0-data0").
            allocatable (int): the allocatable VF count for that datanetwork.
        """
        self.sriov_datanetwork_allocatable[datanetwork] = allocatable

    def get_sriov_datanetwork_allocatable(self) -> Dict[str, int]:
        """
        Get the full map of datanetwork name to allocatable VF count.

        Returns:
            Dict[str, int]: allocatable VF count keyed by datanetwork name.
        """
        return self.sriov_datanetwork_allocatable

    def get_datanetwork_allocatable(self, datanetwork: str) -> int:
        """
        Get the allocatable VF count for a datanetwork by name.

        The count is looked up generically from the datanetworks the node
        advertises, so any datanetwork exposed by the host is supported
        without a per-name handler.

        Args:
            datanetwork (str): the datanetwork name (e.g. "group1-data2").

        Returns:
            int: the allocatable VF count for the datanetwork.

        Raises:
            KeywordException: if the node does not advertise the datanetwork.
        """
        if datanetwork not in self.sriov_datanetwork_allocatable:
            raise KeywordException(f"Node does not advertise datanetwork {datanetwork}. Available datanetworks: {sorted(self.sriov_datanetwork_allocatable.keys())}")
        return self.sriov_datanetwork_allocatable[datanetwork]
