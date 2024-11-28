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

    def get_entry_pod_cpus(self, entry_id, pod_name) -> list[int]:
        """

        Args:
            entry_id: The ID associated with the CpuManagerStateObject entry. e.g. "0c8f821f-0e23-4722-afdf-badfa276db27"
            pod_name: The name of the pod for which we want to get the associated CPU IDs. e.g. "coredns"

        Returns: The list of CPU IDs associated with the entry-pod combination.
            e.g. For: "0c8f821f-0e23-4722-afdf-badfa276db27":{"coredns":"0-1,28-29"}
                 This function would return [0,1,28,29]

        """

        if not self.entries:
            raise ValueError("Entries are not defined for this CpuManagerStateObject")
        if entry_id not in self.entries:
            raise ValueError(f"{entry_id} is not a valid key in the CpuManagerStateObject entries")

        pod_cpu_dictionary = self.entries[entry_id]
        if pod_name not in pod_cpu_dictionary:
            raise ValueError(f"{pod_name} is not associated with the CpuManagerStateObject entry {entry_id}. The dictionary associated with {entry_id} is {pod_cpu_dictionary}")

        # cpu_entry_string is of the shape: "0-1,28-29"
        cpus = []
        cpu_entry_string = pod_cpu_dictionary[pod_name]
        cpu_range_strings = cpu_entry_string.split(",")
        for cpu_range in cpu_range_strings:

            cpu_range_clean = cpu_range.strip()
            if "-" in cpu_range_clean:
                cpu_range_list = cpu_range_clean.split("-")
                min_cpu = int(cpu_range_list[0])
                max_cpu = int(cpu_range_list[1])
                cpus.extend(range(min_cpu, max_cpu + 1))
            else:
                cpu = int(cpu_range_clean)
                cpus.append(cpu)

        return cpus
