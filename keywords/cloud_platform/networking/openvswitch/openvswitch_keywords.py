"""Keywords for Open vSwitch (OVS) operations.

Provides helper methods for interacting with OVS bridges, ports,
and CRDs via kubectl and ovs-vsctl/ovs-appctl commands.
"""

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
            f"kubectl get pods -n {OVS_NAMESPACE} --no-headers | grep ovs-agent | awk '{{print $1}}'"
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
            f"kubectl exec -n {OVS_NAMESPACE} {ovs_agent_pod} -c {OVS_CONTAINER} -- ovs-vsctl {cmd}"
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
            f"kubectl exec -n {OVS_NAMESPACE} {ovs_agent_pod} -c {OVS_CONTAINER} -- ovs-appctl {cmd}"
        )
        return self._to_str(self.ssh_connection.send(full_cmd))

    def kubectl_apply_yaml(self, yaml_content: str) -> str:
        """Apply a YAML manifest via kubectl.

        Args:
            yaml_content: YAML string to apply.

        Returns:
            str: Command output.
        """
        cmd = export_k8s_config(f"echo '{yaml_content}' | kubectl apply -f -")
        return self._to_str(self.ssh_connection.send(cmd))

    def kubectl_delete_resource(self, resource_type: str, name: str, namespace: str = OVS_NAMESPACE) -> str:
        """Delete a kubernetes resource.

        Args:
            resource_type: Resource type (e.g. ovsbridge, ovsport).
            name: Resource name.
            namespace: Namespace.

        Returns:
            str: Command output.
        """
        cmd = export_k8s_config(f"kubectl delete {resource_type} {name} -n {namespace} --ignore-not-found")
        return self._to_str(self.ssh_connection.send(cmd))

    def get_ovsbridge_status(self, bridge_name: str) -> str:
        """Get OVSBridge CR status reason.

        Args:
            bridge_name: Name of the OVSBridge CR.

        Returns:
            str: Status reason string.
        """
        cmd = export_k8s_config(
            f"kubectl get ovsbridge {bridge_name} -n {OVS_NAMESPACE} -o jsonpath='{{.status.conditions[0].reason}}'"
        )
        return self._to_str(self.ssh_connection.send(cmd)).strip()

    def get_ovsport_names(self) -> str:
        """Get all OVSPort CR names.

        Returns:
            str: Space-separated port names.
        """
        cmd = export_k8s_config(
            f"kubectl get ovsport -n {OVS_NAMESPACE} -o jsonpath='{{.items[*].metadata.name}}'"
        )
        return self._to_str(self.ssh_connection.send(cmd)).strip()

    def exec_on_remote_pod(self, remote_ip: str, password: str, pod_name: str, cmd: str) -> str:
        """Execute a command in a pod on a separate remote host.

        Used for inter-system OVS testing where the peer is an independent
        AIO-SX system (separate cluster, not reachable via local kubectl).
        Connects via SSH hop through the local controller.

        Args:
            remote_ip: IP of the remote host (separate AIO-SX cluster).
            password: SSH password for the remote host.
            pod_name: Pod name on the remote host.
            cmd: Command to execute inside the pod.

        Returns:
            str: Command output.
        """
        full_cmd = (
            f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no sysadmin@{remote_ip} "
            f"\"export KUBECONFIG=/etc/kubernetes/admin.conf && kubectl exec {pod_name} -- {cmd}\""
        )
        raw = self._to_str(self.ssh_connection.send(full_cmd))
        return self._strip_ssh_banner(raw)

    def get_remote_pod_by_prefix(self, remote_ip: str, password: str, pod_prefix: str) -> str:
        """Discover a pod name by prefix on a separate remote host.

        Args:
            remote_ip: IP of the remote host (separate AIO-SX cluster).
            password: SSH password for the remote host.
            pod_prefix: Pod name prefix to search for.

        Returns:
            str: Full pod name.
        """
        full_cmd = (
            f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no sysadmin@{remote_ip} "
            f"\"export KUBECONFIG=/etc/kubernetes/admin.conf && "
            f"kubectl get pods --no-headers -o custom-columns=NAME:.metadata.name | grep {pod_prefix}\""
        )
        raw = self._to_str(self.ssh_connection.send(full_cmd))
        cleaned = self._strip_ssh_banner(raw)
        return cleaned.strip().split("\n")[0].strip()

    @staticmethod
    def _strip_ssh_banner(output: str) -> str:
        """Remove SSH login banner lines from command output.

        StarlingX systems display a mandatory security banner on SSH login
        (configured via /etc/issue.net). This method strips those lines
        when executing commands on remote hosts via SSH hop.

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
