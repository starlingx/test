from typing import List

from keywords.k8s.node.object.kubernetes_node_allocated_resources_list_object import KubernetesNodeAllocatedResourcesListObject
from keywords.k8s.node.object.kubernetes_node_capacity_object import KubernetesNodeCapacityObject


class KubectlNodeDescriptionObject:
    """
    Class to hold attributes of a 'kubectl describe node' entry.
    """

    def __init__(self):
        """
        Constructor
        """

        self.name: str = None
        self.roles: str = None
        self.labels: List[str] = None
        self.annotations: List[str] = None
        self.creation_timestamp: str = None
        self.capacity: KubernetesNodeCapacityObject = None
        self.allocatable: KubernetesNodeCapacityObject = None
        self.allocated_resources: KubernetesNodeAllocatedResourcesListObject = None

    def set_name(self, name: str):
        """
        Setter for the name
        Args:
            name: Name of the Node
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for the name of the node.
        Returns: (str) name of the node.

        """
        return self.name

    def set_roles(self, roles: str):
        """
        Setter for the roles
        Args:
            roles: Roles of the Node
        """
        self.roles = roles

    def get_roles(self) -> str:
        """
        Getter for the roles of the node.
        Returns: (str) roles of the node.

        """
        return self.roles

    def set_labels(self, labels: List[str]):
        """
        Setter for the labels
        Args:
            labels: labels of the Node
        """
        self.labels = labels

    def get_labels(self) -> List[str]:
        """
        Getter for the labels of the node.
        Returns: List[str] labels of the node.

        """
        return self.labels

    def set_annotations(self, annotations: List[str]):
        """
        Setter for the annotations
        Args:
            annotations: annotations of the Node
        """
        self.annotations = annotations

    def get_annotations(self) -> List[str]:
        """
        Getter for the annotations of the node.
        Returns: List[str] annotations of the node.

        """
        return self.annotations

    def set_creation_timestamp(self, creation_timestamp: str):
        """
        Setter for the creation_timestamp
        Args:
            creation_timestamp: creation_timestamp of the Node
        """
        self.creation_timestamp = creation_timestamp

    def get_creation_timestamp(self) -> str:
        """
        Getter for the creation_timestamp of the node.
        Returns: (str) creation_timestamp of the node.

        """
        return self.creation_timestamp

    def set_capacity(self, capacity: KubernetesNodeCapacityObject):
        """
        Setter for the capacity
        Args:
            capacity: capacity of the Node
        """
        self.capacity = capacity

    def get_capacity(self) -> KubernetesNodeCapacityObject:
        """
        Getter for the capacity of the node.
        Returns: (str) capacity of the node.

        """
        return self.capacity

    def set_allocatable(self, allocatable: KubernetesNodeCapacityObject):
        """
        Setter for the allocatable
        Args:
            allocatable: allocatable of the Node
        """
        self.allocatable = allocatable

    def get_allocatable(self) -> KubernetesNodeCapacityObject:
        """
        Getter for the allocatable of the node.
        Returns: (str) allocatable of the node.

        """
        return self.allocatable

    def set_allocated_resources(self, allocated_resources: KubernetesNodeAllocatedResourcesListObject):
        """
        Setter for the allocated_resources
        Args:
            allocated_resources: allocated_resources of the Node
        """
        self.allocated_resources = allocated_resources

    def get_allocated_resources(self) -> KubernetesNodeAllocatedResourcesListObject:
        """
        Getter for the allocated_resources of the node.
        Returns: KubernetesNodeAllocatedResourcesListObject of the node.

        """
        return self.allocated_resources
