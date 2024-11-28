from typing import List

from keywords.k8s.node.object.kubectl_node_description_object import KubectlNodeDescriptionObject
from keywords.k8s.node.object.kubernetes_node_allocated_resources_list_object import KubernetesNodeAllocatedResourcesListObject
from keywords.k8s.node.object.kubernetes_node_capacity_object import KubernetesNodeCapacityObject


class KubectlNodeDescriptionOutput:

    def __init__(self, kubectl_describe_node_output: str):
        """
        Constructor

        Args:
            kubectl_describe_node_output: Raw string output from running a "kubectl describe node" command.

        """

        self.node_description: KubectlNodeDescriptionObject = KubectlNodeDescriptionObject()

        sections_output_mapping = {}
        potential_section_headers = [
            "Name:",
            "Roles:",
            "Labels:",
            "Annotations:",
            "CreationTimestamp:",
            "Taints:",
            "Unschedulable:",
            "Lease:",
            "Conditions:",
            "Addresses:",
            "Capacity:",
            "Allocatable:",
            "System Info:",
            "Non-terminated Pods:",
            "Allocated resources:",
            "Events:",
        ]

        # Split lines into the different sections of the description
        section_lines = []
        for line in kubectl_describe_node_output:

            is_new_section = False

            # We are changing section
            for header in potential_section_headers:
                if header in line:
                    section_lines = [line]
                    sections_output_mapping[header] = section_lines
                    is_new_section = True
                    break

            # Otherwise, append to the current section.
            if not is_new_section:
                section_lines.append(line)

        # Parse each section individually and set the object values.
        for header in sections_output_mapping.keys():

            if header == "Name:":
                value = self._parse_single_value(header, sections_output_mapping[header])
                self.node_description.set_name(value)

            if header == "Roles:":
                value = self._parse_single_value(header, sections_output_mapping[header])
                self.node_description.set_roles(value)

            if header == "Labels:":
                value = self._parse_labels(sections_output_mapping[header])
                self.node_description.set_labels(value)

            if header == "Annotations:":
                value = self._parse_annotations(sections_output_mapping[header])
                self.node_description.set_annotations(value)

            if header == "CreationTimestamp:":
                value = self._parse_single_value(header, sections_output_mapping[header])
                self.node_description.set_creation_timestamp(value)

            if header == "Capacity:":
                value = self._parse_capacity(sections_output_mapping[header])
                self.node_description.set_capacity(value)

            if header == "Allocatable:":
                value = self._parse_capacity(sections_output_mapping[header])
                self.node_description.set_allocatable(value)

            if header == "Allocated resources:":
                value = self._parse_allocated_resources(sections_output_mapping[header])
                self.node_description.set_allocated_resources(value)

    def _parse_single_value(self, header, lines) -> str:
        """
        This function will parse fields that are of the form:

            "key:    value"

        Args:
            lines: Lines associated with this field.

        Returns: String value.
        """

        if len(lines) > 1:
            raise ValueError(f"There should only be one line associated with the '{header}' field.")

        length_of_header = len(header) + 1  # +1 for the colon
        value = lines[0][length_of_header:].strip()
        return value

    def _parse_labels(self, lines) -> List[str]:
        """
        This function will parse the Labels block which is of the form:

        Labels:             beta.kubernetes.io/arch=amd64
                            beta.kubernetes.io/os=linux
                            kubernetes.io/arch=amd64
                            kubernetes.io/hostname=controller-0
                            kubernetes.io/os=linux
                            node-role.kubernetes.io/control-plane=
                            node.kubernetes.io/exclude-from-external-load-balancers=

        Args:
            lines: Lines associated with the labels field.

        Returns: A list of labels
        """

        labels = []
        for line in lines:

            if "Labels:" in line:
                line = line[8:]  # Everything after "Labels:"

            labels.append(line.strip())

        return labels

    def _parse_annotations(self, lines) -> List[str]:
        """
        This function will parse the Annotations block which is of the form:

        Annotations:        csi.volume.kubernetes.io/nodeid: {"cephfs.csi.ceph.com":"controller-0","rbd.csi.ceph.com":"controller-0"}
                            kubeadm.alpha.kubernetes.io/cri-socket: unix:///var/run/containerd/containerd.sock
                            node.alpha.kubernetes.io/ttl: 0
                            projectcalico.org/IPv6Address: abcd::2/64
                            volumes.kubernetes.io/controller-managed-attach-detach: true

        Args:
            lines: Lines associated with the Annotations field.

        Returns: A list of Annotations
        """

        annotations = []
        for line in lines:

            if "Annotations:" in line:
                line = line[12:]  # Everything after "Annotations:"

            annotations.append(line.strip())

        return annotations

    def _parse_capacity(self, lines) -> KubernetesNodeCapacityObject:
        """
        This function will parse the Capacity or the Allocatable section of the node description

        Capacity:
          cpu:                24
          ephemeral-storage:  10218772Ki
          hugepages-1Gi:      0
          hugepages-2Mi:      0
          memory:             129003248Ki
          pods:               110

        Args:
            lines: Lines that form the capacity block.

        Returns: KubernetesNodeCapacityObject

        """

        kubernetes_node_capacity_object = KubernetesNodeCapacityObject()
        for line in lines:

            line = line.strip()
            if "Capacity:" in line or "Allocatable:" in line:
                continue  # This is the header, we don't care about it.

            if "cpu:" in line:
                value = line[len("cpu:") :].strip()
                kubernetes_node_capacity_object.set_cpu(int(value))
            if "ephemeral-storage:" in line:
                value = line[len("ephemeral-storage:") :].strip()
                kubernetes_node_capacity_object.set_ephemeral_storage(value)
            if "hugepages-1Gi:" in line:
                value = line[len("hugepages-1Gi:") :].strip()
                kubernetes_node_capacity_object.set_hugepages_1gi(value)
            if "hugepages-2Mi:" in line:
                value = line[len("hugepages-2Mi:") :].strip()
                kubernetes_node_capacity_object.set_hugepages_2mi(value)
            if "memory:" in line:
                value = line[len("memory:") :].strip()
                kubernetes_node_capacity_object.set_memory(value)
            if "pods:" in line:
                value = line[len("pods:") :].strip()
                kubernetes_node_capacity_object.set_pods(int(value))
            if "windriver.com/isolcpus:" in line:
                value = line[len("windriver.com/isolcpus:") :].strip()
                kubernetes_node_capacity_object.set_windriver_isolcpus(int(value))
            if "intel.com/dummy:" in line:
                value = line[len("intel.com/dummy:") :].strip()
                kubernetes_node_capacity_object.set_intel_dummy(int(value))
            if "intel.com/pci_sriov_net_group0_data0:" in line:
                value = line[len("intel.com/pci_sriov_net_group0_data0:") :].strip()
                kubernetes_node_capacity_object.set_intel_pci_sriov_net_group0_data0(int(value))
            if "intel.com/pci_sriov_net_group0_data1:" in line:
                value = line[len("intel.com/pci_sriov_net_group0_data1:") :].strip()
                kubernetes_node_capacity_object.set_intel_pci_sriov_net_group0_data1(int(value))
            if "intel.com/pci_sriov_net_sriov_test_datanetwork:" in line:
                value = line[len("intel.com/pci_sriov_net_sriov_test_datanetwork:") :].strip()
                kubernetes_node_capacity_object.set_intel_pci_sriov_net_sriov_test_datanetwork(int(value))

        return kubernetes_node_capacity_object

    def _parse_allocated_resources(self, lines) -> KubernetesNodeAllocatedResourcesListObject:
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

        Returns:
            KubernetesNodeAllocatedResourcesListObject
        """

        allocated_resources_list = KubernetesNodeAllocatedResourcesListObject(lines)
        return allocated_resources_list

    def get_node_description(self) -> KubectlNodeDescriptionObject:
        """
        Getter for the node description object extracted from the output.
        Returns: KubectlNodeDescriptionObject

        """
        return self.node_description
