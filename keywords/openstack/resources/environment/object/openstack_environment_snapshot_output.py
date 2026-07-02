"""Output object for OpenStack environment snapshot."""

from typing import List

from keywords.openstack.resources.environment.object.cinder_service_snapshot_object import CinderServiceSnapshotObject
from keywords.openstack.resources.environment.object.compute_service_snapshot_object import ComputeServiceSnapshotObject
from keywords.openstack.resources.environment.object.hypervisor_snapshot_object import HypervisorSnapshotObject
from keywords.openstack.resources.environment.object.neutron_agent_snapshot_object import NeutronAgentSnapshotObject
from keywords.openstack.resources.environment.object.pod_snapshot_object import PodSnapshotObject


class OpenStackEnvironmentSnapshotOutput:
    """Holds captured OpenStack environment state."""

    def __init__(self, compute_services: List[ComputeServiceSnapshotObject], cinder_services: List[CinderServiceSnapshotObject], neutron_agents: List[NeutronAgentSnapshotObject], hypervisors: List[HypervisorSnapshotObject], pods: List[PodSnapshotObject]):
        """Initialize OpenStackEnvironmentSnapshotOutput.

        Args:
            compute_services (List[ComputeServiceSnapshotObject]): Nova compute service states.
            cinder_services (List[CinderServiceSnapshotObject]): Cinder volume service states.
            neutron_agents (List[NeutronAgentSnapshotObject]): Neutron agent states.
            hypervisors (List[HypervisorSnapshotObject]): Hypervisor states.
            pods (List[PodSnapshotObject]): OpenStack pod states.
        """
        self._compute_services = compute_services
        self._cinder_services = cinder_services
        self._neutron_agents = neutron_agents
        self._hypervisors = hypervisors
        self._pods = pods

    def get_compute_services(self) -> List[ComputeServiceSnapshotObject]:
        """Get Nova compute service states.

        Returns:
            List[ComputeServiceSnapshotObject]: List of compute service objects.
        """
        return self._compute_services

    def get_cinder_services(self) -> List[CinderServiceSnapshotObject]:
        """Get Cinder volume service states.

        Returns:
            List[CinderServiceSnapshotObject]: List of cinder service objects.
        """
        return self._cinder_services

    def get_neutron_agents(self) -> List[NeutronAgentSnapshotObject]:
        """Get Neutron agent states.

        Returns:
            List[NeutronAgentSnapshotObject]: List of neutron agent objects.
        """
        return self._neutron_agents

    def get_hypervisors(self) -> List[HypervisorSnapshotObject]:
        """Get hypervisor states.

        Returns:
            List[HypervisorSnapshotObject]: List of hypervisor objects.
        """
        return self._hypervisors

    def get_pods(self) -> List[PodSnapshotObject]:
        """Get OpenStack pod states.

        Returns:
            List[PodSnapshotObject]: List of pod objects.
        """
        return self._pods
