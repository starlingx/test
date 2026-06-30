"""OpenStack environment snapshot keywords for before/after comparison."""

from typing import List

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.environment.object.cinder_service_snapshot_object import CinderServiceSnapshotObject
from keywords.openstack.resources.environment.object.compute_service_snapshot_object import ComputeServiceSnapshotObject
from keywords.openstack.resources.environment.object.hypervisor_snapshot_object import HypervisorSnapshotObject
from keywords.openstack.resources.environment.object.neutron_agent_snapshot_object import NeutronAgentSnapshotObject
from keywords.openstack.resources.environment.object.openstack_environment_snapshot_output import OpenStackEnvironmentSnapshotOutput
from keywords.openstack.resources.environment.object.pod_snapshot_object import PodSnapshotObject


class OpenStackEnvironmentSnapshotKeywords(BaseKeyword):
    """Capture and compare OpenStack environment state for before/after validation.

    Captures OpenStack services, pods, hypervisors, and agents to detect
    unexpected state changes after disruptive operations (reboot, swact, etc.).
    """

    def __init__(self, ssh_connection: SSHConnection, ace_conn: ACEOpenStackConnection):
        """Initialize OpenStackEnvironmentSnapshotKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
            ace_conn (ACEOpenStackConnection): ACE OpenStack connection.
        """
        self.ssh_connection = ssh_connection
        self.ace_conn = ace_conn

    def capture_snapshot(self) -> OpenStackEnvironmentSnapshotOutput:
        """Capture current OpenStack environment state.

        Captures:
            - Nova compute services (host, state, status)
            - Cinder volume services (host, state, status)
            - Neutron agents (host, binary, alive)
            - Hypervisors (name, state, status)
            - OpenStack pod names and statuses

        Returns:
            OpenStackEnvironmentSnapshotOutput: Captured environment state.
        """
        get_logger().log_info("Capturing OpenStack environment snapshot")

        # Nova compute services
        compute_services = []
        for s in self.ace_conn.get_compute().services():
            if s.binary == "nova-compute":
                obj = ComputeServiceSnapshotObject()
                obj.set_host(s.host)
                obj.set_state(s.state)
                obj.set_status(s.status)
                compute_services.append(obj)

        # Cinder volume services
        cinder_services = []
        for s in self.ace_conn.get_block_storage().services():
            if s.binary == "cinder-volume":
                obj = CinderServiceSnapshotObject()
                obj.set_host(s.host)
                obj.set_state(s.state)
                obj.set_status(s.status)
                cinder_services.append(obj)

        # Neutron agents
        neutron_agents = []
        for a in self.ace_conn.get_network().agents():
            obj = NeutronAgentSnapshotObject()
            obj.set_host(a.host)
            obj.set_binary(a.binary)
            obj.set_alive(a.is_alive)
            neutron_agents.append(obj)

        # Hypervisors
        hypervisors = []
        for h in self.ace_conn.get_compute().hypervisors(details=True):
            obj = HypervisorSnapshotObject()
            obj.set_name(h.name)
            obj.set_state(h.state)
            obj.set_status(h.status)
            hypervisors.append(obj)

        # OpenStack pods
        pods = []
        kubectl_kw = KubectlGetPodsKeywords(self.ssh_connection)
        pod_output = kubectl_kw.get_pods(namespace="openstack")
        for pod in pod_output.get_pods():
            obj = PodSnapshotObject()
            obj.set_name(pod.get_name())
            obj.set_status(pod.get_status())
            pods.append(obj)

        get_logger().log_info(
            f"Snapshot captured: {len(compute_services)} compute services, "
            f"{len(cinder_services)} cinder services, "
            f"{len(neutron_agents)} neutron agents, "
            f"{len(hypervisors)} hypervisors, "
            f"{len(pods)} pods"
        )
        return OpenStackEnvironmentSnapshotOutput(
            compute_services=compute_services,
            cinder_services=cinder_services,
            neutron_agents=neutron_agents,
            hypervisors=hypervisors,
            pods=pods,
        )

    def compare_snapshots(self, before: OpenStackEnvironmentSnapshotOutput, after: OpenStackEnvironmentSnapshotOutput) -> List[str]:
        """Compare two snapshots and return all differences.

        Args:
            before (OpenStackEnvironmentSnapshotOutput): Snapshot captured before the operation.
            after (OpenStackEnvironmentSnapshotOutput): Snapshot captured after the operation.

        Returns:
            List[str]: All differences found between snapshots.
        """
        differences: List[str] = []

        # Compare compute services
        before_computes = {s.get_host(): s for s in before.get_compute_services()}
        after_computes = {s.get_host(): s for s in after.get_compute_services()}

        for host, before_svc in before_computes.items():
            if host not in after_computes:
                differences.append(f"nova-compute on {host} disappeared")
            elif before_svc.get_state() == "up" and after_computes[host].get_state() != "up":
                differences.append(f"nova-compute on {host} was up, now {after_computes[host].get_state()}")

        # Compare cinder services
        before_cinder = {s.get_host(): s for s in before.get_cinder_services()}
        after_cinder = {s.get_host(): s for s in after.get_cinder_services()}

        for host, before_svc in before_cinder.items():
            if host not in after_cinder:
                differences.append(f"cinder-volume on {host} disappeared")
            elif before_svc.get_state() == "up" and after_cinder[host].get_state() != "up":
                differences.append(f"cinder-volume on {host} was up, now {after_cinder[host].get_state()}")

        # Compare hypervisors
        before_hyps = {h.get_name(): h for h in before.get_hypervisors()}
        after_hyps = {h.get_name(): h for h in after.get_hypervisors()}

        for name, before_hyp in before_hyps.items():
            if name not in after_hyps:
                differences.append(f"Hypervisor {name} disappeared")
            elif before_hyp.get_state() == "up" and after_hyps[name].get_state() != "up":
                differences.append(f"Hypervisor {name} was up, now {after_hyps[name].get_state()}")

        # Compare neutron agents
        before_agents = {f"{a.get_binary()}@{a.get_host()}": a for a in before.get_neutron_agents()}
        after_agents = {f"{a.get_binary()}@{a.get_host()}": a for a in after.get_neutron_agents()}

        for key, before_agent in before_agents.items():
            if key not in after_agents:
                differences.append(f"Neutron agent {key} disappeared")
            elif before_agent.get_alive() and not after_agents[key].get_alive():
                differences.append(f"Neutron agent {key} was alive, now dead")

        # Compare pods
        before_pods = {p.get_name(): p for p in before.get_pods()}
        after_pods = {p.get_name(): p for p in after.get_pods()}

        for name, before_pod in before_pods.items():
            if before_pod.get_status() in ("Running", "Completed"):
                if name not in after_pods:
                    differences.append(f"Pod {name} (was {before_pod.get_status()}) not found after")
                elif after_pods[name].get_status() not in ("Running", "Completed"):
                    differences.append(f"Pod {name} was {before_pod.get_status()}, now {after_pods[name].get_status()}")

        # Log all differences directly
        if differences:
            get_logger().log_info(f"Environment snapshot: {len(differences)} differences found")
            for diff in differences:
                get_logger().log_info(f"  DIFF: {diff}")
        else:
            get_logger().log_info("Environment snapshot: no differences detected")

        return differences
