"""Keywords for Open vSwitch (OVS) operations.

Provides helper methods for interacting with OVS bridges, ports,
and CRDs via kubectl and ovs-vsctl/ovs-appctl commands.
"""

from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


OVS_NAMESPACE = "openvswitch"
OVS_CONTAINER = "ovs-vswitchd"


class OpenvSwitchKeywords(BaseKeyword):
    """Keywords for interacting with OVS operator and virtual switch."""

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    @staticmethod
    def _to_str(output):
        """Convert SSH output to string."""
        if isinstance(output, list):
            return "\n".join(output)
        return output

    def get_ovs_agent_pod(self) -> str:
        """Get the ovs-agent-operator pod name.

        Returns:
            str: The pod name.
        """
        output = self.ssh_connection.send(export_k8s_config(
            f"kubectl get pods -n {OVS_NAMESPACE} --no-headers"
            " | grep ovs-agent | awk '{print $1}'"
        ))
        raw = self._to_str(output)
        return raw.strip().split("\n")[0].strip()

    def ovs_vsctl(self, ovs_agent_pod: str, cmd: str) -> str:
        """Run ovs-vsctl command inside the ovs-vswitchd container.

        Args:
            ovs_agent_pod: Name of the ovs-agent pod.
            cmd: ovs-vsctl subcommand to execute.

        Returns:
            str: Command output.
        """
        full_cmd = export_k8s_config(
            f"kubectl exec -n {OVS_NAMESPACE} {ovs_agent_pod}"
            f" -c {OVS_CONTAINER} -- ovs-vsctl {cmd}"
        )
        return self._to_str(self.ssh_connection.send(full_cmd))

    def ovs_appctl(self, ovs_agent_pod: str, cmd: str) -> str:
        """Run ovs-appctl command inside the ovs-vswitchd container.

        Args:
            ovs_agent_pod: Name of the ovs-agent pod.
            cmd: ovs-appctl subcommand to execute.

        Returns:
            str: Command output.
        """
        full_cmd = export_k8s_config(
            f"kubectl exec -n {OVS_NAMESPACE} {ovs_agent_pod}"
            f" -c {OVS_CONTAINER} -- ovs-appctl {cmd}"
        )
        return self._to_str(self.ssh_connection.send(full_cmd))

    def exec_in_pod(self, ovs_agent_pod: str, cmd: str, container: str = OVS_CONTAINER) -> str:
        """Execute an arbitrary command inside the OVS agent pod container.

        Args:
            ovs_agent_pod: Name of the ovs-agent pod.
            cmd: Command to execute.
            container: Container name (default: ovs-vswitchd).

        Returns:
            str: Command output.
        """
        full_cmd = export_k8s_config(
            f"kubectl exec -n {OVS_NAMESPACE} {ovs_agent_pod}"
            f" -c {container} -- {cmd}"
        )
        return self._to_str(self.ssh_connection.send(full_cmd))

    def kubectl_apply_yaml(self, yaml_content: str) -> str:
        """Apply a YAML manifest via kubectl.

        Captures stderr so that admission webhook denial messages are
        available in the output for validation.

        Args:
            yaml_content: YAML string to apply.

        Returns:
            str: Command output (includes stderr).
        """
        cmd = export_k8s_config(
            f"echo '{yaml_content}' | kubectl apply -f - 2>&1"
        )
        return self._to_str(self.ssh_connection.send(cmd))

    def get_ovs_crd_names(self, resource_type: str, namespace: str = OVS_NAMESPACE) -> list:
        """Get names of OVS CRD resources.

        Args:
            resource_type: CRD type (e.g. ovsnodeconfig, ovsbridge, ovsaccess).
            namespace: Namespace.

        Returns:
            list: List of resource names.
        """
        cmd = export_k8s_config(
            f"kubectl get {resource_type} -n {namespace}"
            " --no-headers -o custom-columns=NAME:.metadata.name"
        )
        output = self._to_str(self.ssh_connection.send(cmd))
        return [name.strip() for name in output.strip().split("\n") if name.strip()]

    def patch_ovs_crd(self, resource_type: str, name: str, namespace: str, patch: str) -> str:
        """Attempt to patch an OVS CRD resource (expected to be denied).

        Used for testing admission webhook denials. Captures stderr so
        the denial message can be validated by the test.

        Args:
            resource_type: CRD type (e.g. ovsnodeconfig).
            name: Resource name.
            namespace: Namespace.
            patch: JSON patch string.

        Returns:
            str: Command output (typically contains denial message).
        """
        cmd = export_k8s_config(
            f"kubectl patch {resource_type} {name} -n {namespace}"
            f" --type=merge -p '{patch}' 2>&1"
        )
        return self._to_str(self.ssh_connection.send(cmd))

    def get_ovsbridge_status(self, bridge_name: str) -> str:
        """Get OVSBridge CR status reason.

        Args:
            bridge_name: Name of the OVSBridge CR.

        Returns:
            str: Status reason string.
        """
        cmd = export_k8s_config(
            f"kubectl get ovsbridge {bridge_name} -n {OVS_NAMESPACE}"
            " -o jsonpath='{.status.conditions[0].reason}'"
        )
        return self._to_str(self.ssh_connection.send(cmd)).strip()

    def get_ovsport_names(self) -> str:
        """Get all OVSPort CR names.

        Returns:
            str: Space-separated port names.
        """
        cmd = export_k8s_config(
            f"kubectl get ovsport -n {OVS_NAMESPACE}"
            " -o jsonpath='{.items[*].metadata.name}'"
        )
        return self._to_str(self.ssh_connection.send(cmd)).strip()

    def exec_on_remote_pod(self, remote_ip: str, password: str, pod_name: str, cmd: str) -> str:
        """Execute a command in a pod on a separate remote host.

        Used for inter-system OVS testing where the peer is an independent
        AIO-SX system (separate cluster, not reachable via local kubectl).

        Args:
            remote_ip: IP of the remote host.
            password: SSH password for the remote host.
            pod_name: Pod name on the remote host.
            cmd: Command to execute inside the pod.

        Returns:
            str: Command output.
        """
        full_cmd = (
            f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no"
            f" sysadmin@{remote_ip}"
            f" \"export KUBECONFIG=/etc/kubernetes/admin.conf"
            f" && kubectl exec {pod_name} -- {cmd}\""
        )
        raw = self._to_str(self.ssh_connection.send(full_cmd))
        return self._strip_ssh_banner(raw)

    def get_remote_pod_by_prefix(self, remote_ip: str, password: str, pod_prefix: str) -> str:
        """Discover a pod name by prefix on a separate remote host.

        Args:
            remote_ip: IP of the remote host.
            password: SSH password for the remote host.
            pod_prefix: Pod name prefix to search for.

        Returns:
            str: Full pod name.
        """
        full_cmd = (
            f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no"
            f" sysadmin@{remote_ip}"
            f" \"export KUBECONFIG=/etc/kubernetes/admin.conf"
            f" && kubectl get pods --no-headers"
            f" -o custom-columns=NAME:.metadata.name | grep {pod_prefix}\""
        )
        raw = self._to_str(self.ssh_connection.send(full_cmd))
        cleaned = self._strip_ssh_banner(raw)
        return cleaned.strip().split("\n")[0].strip()

    @staticmethod
    def _strip_ssh_banner(output: str) -> str:
        """Remove SSH login banner lines from command output.

        Args:
            output: Raw command output that may contain banner text.

        Returns:
            str: Output with banner lines removed.
        """
        banner_markers = [
            "Release ", "W A R N I N G", "THIS IS A PRIVATE",
            "This computer system", "network devices",
            "(specifically including", "are provided only",
            "All computer systems", "ensure that their use",
            "for management of", "facilitate protection",
            "procedures, survivability", "attacks by authorized",
            "security of the system", "recorded, copied",
            "personal information", "of this system",
            "Unauthorized use", "Evidence of any",
            "for administrative", "constitutes consent",
            "Monitoring includes", "Uses of this system",
            "--------",
        ]
        lines = output.split("\n")
        filtered = [l for l in lines if not any(m in l for m in banner_markers)]
        return "\n".join(filtered)

    def get_bfd_config(self, ovs_agent_pod: str, interface: str) -> str:
        """Get BFD configuration for an interface.

        Args:
            ovs_agent_pod: Name of the ovs-agent pod.
            interface: Interface name.

        Returns:
            str: BFD configuration string.
        """
        return self.ovs_vsctl(ovs_agent_pod, f"get interface {interface} bfd")

    def get_bfd_status(self, ovs_agent_pod: str, interface: str) -> str:
        """Get BFD status for an interface.

        Args:
            ovs_agent_pod: Name of the ovs-agent pod.
            interface: Interface name.

        Returns:
            str: BFD status string.
        """
        return self.ovs_vsctl(ovs_agent_pod, f"get interface {interface} bfd_status")

    def verify_connectivity(self, ovs_agent_pod: str, target_ip: str, bridge_name: str = "", ipv6: bool = False) -> str:
        """Verify IP connectivity using ip neighbor solicitation.

        Since the ovs-agent pod does not have ping/ping6 utilities,
        uses ip neigh after NDP/ARP probe to check reachability.

        Args:
            ovs_agent_pod: Name of the ovs-agent pod.
            target_ip: Target IP to verify reachability.
            bridge_name: Bridge interface to probe on (from config if empty).
            ipv6: Whether target is IPv6 (auto-detected from ':' in IP).

        Returns:
            str: Output containing 'reply' on success, 'timeout' otherwise.
        """
        if not bridge_name:
            bridge_name = ConfigurationManager.get_lab_config().get_ovs_config().get_bridge_name()

        is_ipv6 = ipv6 or ":" in target_ip
        if is_ipv6:
            cmd = (
                f"ip -6 neigh add {target_ip} dev {bridge_name} nud probe 2>/dev/null; "
                f"ip -6 neigh show {target_ip}"
                " | grep -q 'REACHABLE\\|STALE\\|DELAY' && echo reply || echo timeout"
            )
        else:
            cmd = (
                f"ip neigh add {target_ip} dev {bridge_name} nud probe 2>/dev/null; "
                f"ip neigh show {target_ip}"
                " | grep -q 'REACHABLE\\|STALE\\|DELAY' && echo reply || echo timeout"
            )
        return self.exec_in_pod(ovs_agent_pod, f"sh -c '{cmd}'")

    def verify_connectivity_from_remote(self, remote_ip: str, password: str, pod_name: str, target_ip: str) -> str:
        """Verify connectivity by pinging from a remote traffic pod.

        Args:
            remote_ip: IP of the remote host.
            password: SSH password for the remote host.
            pod_name: Pod name on the remote host.
            target_ip: Target IP to ping.

        Returns:
            str: Ping output (check for '0% packet loss' or 'bytes from').
        """
        ping_cmd = "ping6" if ":" in target_ip else "ping"
        return self.exec_on_remote_pod(
            remote_ip, password, pod_name,
            f"{ping_cmd} -c 3 -W 2 {target_ip}"
        )

    def add_vlan_internal_port(self, ovs_agent_pod: str, bridge: str, vlan_name: str, vlan_id: int, host_ip: str) -> None:
        """Create OVS internal port with VLAN tag and assign IP.

        Args:
            ovs_agent_pod: Name of the ovs-agent pod.
            bridge: Bridge name to add port to.
            vlan_name: Name for the internal port.
            vlan_id: VLAN tag ID.
            host_ip: IP address to assign to the port.
        """
        self.ovs_vsctl(
            ovs_agent_pod,
            f"add-port {bridge} {vlan_name} tag={vlan_id}"
            f" -- set interface {vlan_name} type=internal"
        )
        ip_version = "-6 " if ":" in host_ip else ""
        prefix = "64" if ":" in host_ip else "24"
        self.exec_in_pod(
            ovs_agent_pod,
            f"ip {ip_version}addr add {host_ip}/{prefix} dev {vlan_name} 2>/dev/null || true"
        )
        self.exec_in_pod(ovs_agent_pod, f"ip link set {vlan_name} up")
