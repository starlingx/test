class CpuManagerStateObject:
    """
    Object representation of the contents of the "/var/lib/kubelet/cpu_manager_state" file.
    """

    def __init__(self):
        """
        Constructor
        """

        self.policy_name = None
        self.entries = None
        self.default_cpu_set = ''

    def set_policy_name(self, policy_name: str) -> None:
        """
        Setter for policy_name
        """
        self.policy_name = policy_name

    def get_policy_name(self) -> str:
        """
        Getter for policy_name
        """
        return self.policy_name

    def set_default_cpu_set(self, default_cpu_set: str) -> None:
        """
        Setter for default_cpu_set.

        Args:
            default_cpu_set (str): the defaultCpuSet string from cpu_manager_state (e.g. '0-1,28-29').
        """
        self.default_cpu_set = default_cpu_set

    def get_default_cpu_set(self) -> str:
        """
        Getter for default_cpu_set.

        Returns:
            str: the defaultCpuSet string from cpu_manager_state.
        """
        return self.default_cpu_set

    def set_entries(self, entries: dict) -> None:
        """
        Setter for entries.
        Args:
            entries: A Dictionary of the entries values. e.g.
                    {"0c8f821f-0e23-4722-afdf-badfa276db27":{"coredns":"0-1,28-29"},
                     "277d8f2b-80dc-4e68-8aca-240782131ab1":{"csi-cephfsplugin":"0-1,28-29","csi-provisioner":"0-1,28-29"} ... }
        Returns: None

        """
        self.entries = entries

    def get_entries(self) -> dict:
        """
        Getter for entries.
        Returns: Dictionary of the entries values. e.g.
                {"0c8f821f-0e23-4722-afdf-badfa276db27":{"coredns":"0-1,28-29"},
                 "277d8f2b-80dc-4e68-8aca-240782131ab1":{"csi-cephfsplugin":"0-1,28-29","csi-provisioner":"0-1,28-29"} ... }

        """
        return self.entries

    def parse_cpu_range(self, cpu_str: str) -> list[int]:
        """
        Parse a CPU range string into a list of integer CPU IDs.

        Args:
            cpu_str (str): comma-separated CPU range string (e.g. '0-3,5,7-9').

        Returns:
            list[int]: list of integer CPU IDs represented by the range string.
        """
        result = []
        for part in cpu_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                result.extend(range(int(start), int(end) + 1))
            elif part.isdigit():
                result.append(int(part))
        return result

    def get_entry_pod_cpus(self, entry_id, pod_name) -> list[int]:
        """
        Get the list of CPU IDs assigned to a specific pod in a cpu_manager_state entry.

        Args:
            entry_id: The ID associated with the CpuManagerStateObject entry. e.g. "0c8f821f-0e23-4722-afdf-badfa276db27"
            pod_name: The name of the pod for which we want to get the associated CPU IDs. e.g. "coredns"

        Returns:
            list[int]: The list of CPU IDs associated with the entry-pod combination.
                e.g. For: "0c8f821f-0e23-4722-afdf-badfa276db27":{"coredns":"0-1,28-29"}
                     This function would return [0,1,28,29]

        Raises:
            ValueError: if entries are not defined, entry_id not found, or pod_name not in entry.
        """
        if not self.entries:
            raise ValueError("Entries are not defined for this CpuManagerStateObject")
        if entry_id not in self.entries:
            raise ValueError(f"{entry_id} is not a valid key in the CpuManagerStateObject entries")

        pod_cpu_dictionary = self.entries[entry_id]
        if pod_name not in pod_cpu_dictionary:
            raise ValueError(f"{pod_name} is not associated with the CpuManagerStateObject entry {entry_id}. The dictionary associated with {entry_id} is {pod_cpu_dictionary}")

        cpu_entry_string = pod_cpu_dictionary[pod_name]
        return self.parse_cpu_range(cpu_entry_string)

    def get_container_cpuset(self, container_id: str) -> list[int]:
        """
        Get the list of CPU IDs assigned to a specific container.

        This method looks up the container in the cpu_manager_state entries and returns
        the CPUs assigned to it.

        Args:
            container_id (str): container ID to look up in entries.

        Returns:
            list[int]: list of CPU IDs assigned to the container.

        Raises:
            ValueError: if entries are not defined or container is not found in entries.

        Example:
            Given entries:
            {
                "pod-abc123": {"container1": "2-3", "container2": "4-5"},
                "pod-def456": "6-7"
            }

            get_container_cpuset("pod-abc123") returns [2, 3, 4, 5]
            get_container_cpuset("pod-def456") returns [6, 7]
            get_container_cpuset("unknown") raises ValueError
        """
        if not self.entries:
            raise ValueError("Entries are not defined for this CpuManagerStateObject")
        if container_id not in self.entries:
            raise ValueError(f"{container_id} is not found in the CpuManagerStateObject entries")

        cpuset_str = self.entries[container_id]

        # Handle case where entry is a dictionary (pod with multiple containers)
        if isinstance(cpuset_str, dict):
            cpuset_list = []
            # Aggregate CPUs from all containers in the pod
            for val in cpuset_str.values():
                cpuset_list.extend(self.parse_cpu_range(val))
            return cpuset_list
        # Handle case where entry is a simple string (single CPU range)
        else:
            return self.parse_cpu_range(cpuset_str)
