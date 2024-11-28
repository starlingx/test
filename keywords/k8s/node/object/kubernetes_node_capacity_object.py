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
        self.intel_pci_sriov_net_group0_data0 = -1
        self.intel_pci_sriov_net_group0_data1 = -1
        self.intel_dummy = -1
        self.intel_pci_sriov_net_sriov_test_datanetwork = -1

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

    def set_intel_pci_sriov_net_group0_data0(self, intel_pci_sriov_net_group0_data0: int):
        """
        Setter for intel_pci_sriov_net_group0_data0
        Args:
            intel_pci_sriov_net_group0_data0 (): the intel_pci_sriov_net_group0_data0 vf value

        Returns:

        """
        self.intel_pci_sriov_net_group0_data0 = intel_pci_sriov_net_group0_data0

    def get_intel_pci_sriov_net_group0_data0(self) -> int:
        """
        Getter for intel_pci_sriov_net_group0_data0
        Returns:

        """
        return self.intel_pci_sriov_net_group0_data0

    def set_intel_pci_sriov_net_group0_data1(self, intel_pci_sriov_net_group0_data1: int):
        """
        Setter for intel_pci_sriov_net_group0_data1
        Args:
            intel_pci_sriov_net_group0_data1 (): the intel_pci_sriov_net_group0_data1 value

        Returns:

        """
        self.intel_pci_sriov_net_group0_data1 = intel_pci_sriov_net_group0_data1

    def get_intel_pci_sriov_net_group0_data1(self) -> int:
        """
        Getter for intel_pci_sriov_net_group0_data1
        Returns:

        """
        return self.intel_pci_sriov_net_group0_data1

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

    def set_intel_pci_sriov_net_sriov_test_datanetwork(self, intel_pci_sriov_net_sriov_test_datanetwork: int):
        """
        Setter for intel_pci_sriov_net_sriov_test_datanetwork
        Args:
            intel_pci_sriov_net_sriov_test_datanetwork (): intel_pci_sriov_net_sriov_test_datanetwork value

        Returns:

        """
        self.intel_pci_sriov_net_sriov_test_datanetwork = intel_pci_sriov_net_sriov_test_datanetwork

    def get_intel_pci_sriov_net_sriov_test_datanetwork(self) -> int:
        """
        Getter for intel_pci_sriov_net_sriov_test_datanetwork
        Returns:

        """
        return self.intel_pci_sriov_net_sriov_test_datanetwork

    def get_datanetwork_allocatable(self, datanetwork: str) -> int:
        """
        Get the datanetwork allocatable based on the datanetwork name
        Args:
            datanetwork (): the datanetwork name

        Returns:

        """
        if datanetwork == 'group0-data0':
            return self.get_intel_pci_sriov_net_group0_data0()
        elif datanetwork in 'group0-data1':
            return self.get_intel_pci_sriov_net_group0_data1()
        elif datanetwork in 'sriov-test-datanetwork':
            return self.get_intel_pci_sriov_net_sriov_test_datanetwork()
        elif datanetwork in 'intel-dummy':
            return self.get_intel_dummy()
        else:
            raise KeywordException(f"No datanetwork method implemented for datanetwork {datanetwork}")
