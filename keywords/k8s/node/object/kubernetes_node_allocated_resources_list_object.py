from keywords.k8s.node.object.kubernetes_node_allocated_resources_object import KubernetesNodeAllocatedResourcesObject
from keywords.k8s.node.object.kubernetes_node_allocated_resources_table_parser import KubectlNodeAllocatedResourcesTableParser


class KubernetesNodeAllocatedResourcesListObject:
    """
    Class to hold the list of Kubernetes Node Allocated Resources as an object.
    This is parsed from the Allocated Resources section from 'kubectl describe node <node_name>'
    """

    def __init__(self, lines):
        """
        Constructor
        Args:
          lines: Raw output lines from the 'kubectl describe node' output.
                  Allocated resources:
                  (Total limits may be over 100 percent, i.e., overcommitted.)
                  Resource           Requests    Limits
                  --------           --------    ------
                  cpu                0 (0%)      2 (9%)
                  memory             388Mi (0%)  2318Mi (2%)
                  ephemeral-storage  0 (0%)      0 (0%)
                  hugepages-1Gi      0 (0%)      0 (0%)
                  hugepages-2Mi      0 (0%)      0 (0%)

        """
        self.cpu: KubernetesNodeAllocatedResourcesObject = None
        self.memory: KubernetesNodeAllocatedResourcesObject = None
        self.ephemeral_storage: KubernetesNodeAllocatedResourcesObject = None
        self.hugepages_1gi: KubernetesNodeAllocatedResourcesObject = None
        self.hugepages_2mi: KubernetesNodeAllocatedResourcesObject = None
        self.windriver_isolcpus: KubernetesNodeAllocatedResourcesObject = None

        # Parse the lines
        self._parse_allocated_resources(lines)

    def _parse_allocated_resources(self, lines) -> None:
        """
        This function will parse the Annotations block which is of the form:

          Allocated resources:
          (Total limits may be over 100 percent, i.e., overcommitted.)
          Resource           Requests    Limits
          --------           --------    ------
          cpu                0 (0%)      2 (9%)
          memory             388Mi (0%)  2318Mi (2%)
          ephemeral-storage  0 (0%)      0 (0%)
          hugepages-1Gi      0 (0%)      0 (0%)
          hugepages-2Mi      0 (0%)      0 (0%)

        Args:
            lines: Lines that form the allocated_resources block.

        """

        # Strip out the lines that aren't part of the table and the line with -------
        table_lines = []
        for line in lines:
            if not ("Allocated resources:" in line or "Total limits may be over 100 percent" in line or "-----" in line):
                table_lines.append(line)

        # Pass the trimmed output through the K8s table parser.
        list_of_dictionaries = KubectlNodeAllocatedResourcesTableParser(table_lines).get_output_values_list()

        # Transform the Dictionary to a list of objects.
        for dictionary in list_of_dictionaries:

            # Extract the dictionary values into an object.
            allocated_resources_object = KubernetesNodeAllocatedResourcesObject()
            allocated_resources_object.set_resource(dictionary["Resource"])
            allocated_resources_object.set_requests(dictionary["Requests"])
            allocated_resources_object.set_limits(dictionary["Limits"])

            # Assign the objects to the field of the same name.
            if allocated_resources_object.get_resource() == "cpu":
                self.cpu = allocated_resources_object
            if allocated_resources_object.get_resource() == "memory":
                self.memory = allocated_resources_object
            if allocated_resources_object.get_resource() == "ephemeral-storage":
                self.ephemeral_storage = allocated_resources_object
            if allocated_resources_object.get_resource() == "hugepages-1Gi":
                self.hugepages_1gi = allocated_resources_object
            if allocated_resources_object.get_resource() == "hugepages-2Mi":
                self.hugepages_2mi = allocated_resources_object
            if allocated_resources_object.get_resource() == "windriver.com/isolcpus":
                self.windriver_isolcpus = allocated_resources_object

    def get_cpu(self) -> KubernetesNodeAllocatedResourcesObject:
        """
        Getter for the cpu
        Returns: (KubernetesNodeAllocatedResourcesObject)

        """
        return self.cpu

    def get_ephemeral_storage(self) -> KubernetesNodeAllocatedResourcesObject:
        """
        Getter for the ephemeral_storage
        Returns: (KubernetesNodeAllocatedResourcesObject)

        """
        return self.ephemeral_storage

    def get_hugepages_1gi(self) -> KubernetesNodeAllocatedResourcesObject:
        """
        Getter for the hugepages_1gi
        Returns: (KubernetesNodeAllocatedResourcesObject)

        """
        return self.hugepages_1gi

    def get_hugepages_2mi(self) -> KubernetesNodeAllocatedResourcesObject:
        """
        Getter for the hugepages_2mi
        Returns: (KubernetesNodeAllocatedResourcesObject)

        """
        return self.hugepages_2mi

    def get_memory(self) -> KubernetesNodeAllocatedResourcesObject:
        """
        Getter for the memory
        Returns: (KubernetesNodeAllocatedResourcesObject)

        """
        return self.memory

    def get_pods(self) -> KubernetesNodeAllocatedResourcesObject:
        """
        Getter for the pods
        Returns: (KubernetesNodeAllocatedResourcesObject)

        """
        return self.pods

    def get_windriver_isolcpus(self) -> KubernetesNodeAllocatedResourcesObject:
        """
        Getter for the windriver_isolcpus
        Returns: (KubernetesNodeAllocatedResourcesObject)

        """
        return self.windriver_isolcpus
