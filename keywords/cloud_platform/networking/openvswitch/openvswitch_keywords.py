"""Keywords for Open vSwitch (OVS) operations.

Provides helper methods for interacting with OVS bridges, ports,
and CRDs via kubectl and ovs-vsctl/ovs-appctl commands.
"""


from config.configuration_manager import ConfigurationManager
from config.ovs.ovs_config import OvsConfig
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_str_contains_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_if_keywords import SystemHostInterfaceKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.network_attachment.kubectl_get_network_attachment_keywords import KubectlGetNetworkAttachmentKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


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

    def get_ovsnodeconfig_reconcile_status(self, name: str, namespace: str = OVS_NAMESPACE) -> str:
        """Get OVSNodeConfig reconcile status.

        Args:
            name: Name of the OVSNodeConfig resource (e.g. controller-0).
            namespace: Namespace.

        Returns:
            str: Reconcile status string ('true' or 'false').
        """
        cmd = export_k8s_config(
            f"kubectl get ovsnodeconfig {name} -n {namespace}"
            " -o jsonpath='{.status.reconciled}'"
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

    def get_remote_ssh(self, remote_ip: str, password: str) -> SSHConnection:
        """Get or create an SSH connection to the remote peer.

        Args:
            remote_ip: IP of the remote host.
            password: SSH password for the remote host.

        Returns:
            SSHConnection: Connection to the remote peer.
        """
        if not hasattr(self, '_remote_ssh_cache'):
            self._remote_ssh_cache = {}
        if remote_ip not in self._remote_ssh_cache:
            self._remote_ssh_cache[remote_ip] = SSHConnectionManager.create_ssh_connection(
                host=remote_ip,
                user="sysadmin",
                password=password,
                name=f"ovs_remote_{remote_ip}",
            )
        return self._remote_ssh_cache[remote_ip]

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
        remote_ssh = self.get_remote_ssh(remote_ip, password)
        kubectl_cmd = (
            f"export KUBECONFIG=/etc/kubernetes/admin.conf"
            f" && kubectl exec {pod_name} -- {cmd}"
        )
        raw = self._to_str(remote_ssh.send(kubectl_cmd))
        return raw

    def get_remote_pod_by_prefix(self, remote_ip: str, password: str, pod_prefix: str) -> str:
        """Discover a pod name by prefix on a separate remote host.

        Args:
            remote_ip: IP of the remote host.
            password: SSH password for the remote host.
            pod_prefix: Pod name prefix to search for.

        Returns:
            str: Full pod name.
        """
        remote_ssh = self.get_remote_ssh(remote_ip, password)
        kubectl_cmd = (
            f"export KUBECONFIG=/etc/kubernetes/admin.conf"
            f" && kubectl get pods --no-headers"
            f" -o custom-columns=NAME:.metadata.name | grep {pod_prefix}"
        )
        raw = self._to_str(remote_ssh.send(kubectl_cmd))
        return raw.strip().split("\n")[0].strip()

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

    def ensure_ovs_setup(self) -> None:
        """Ensure OVS is fully configured before test execution.

        Performs the following checks and configures if needed:
            1. OVS application uploaded and applied (with helm overrides).
            2. NADs created (with trust=on, spoofchk=off).
            3. OVS agent pod running.
            4. OVS bridge and ports created via CRDs.
            5. Bridge IPs assigned (ephemeral, always refreshed).
            6. Remote peer configured (if remote_peer_ip set in config).

        This is a no-op fast path (~2s) if OVS is already configured.
        On a fresh install, performs full provisioning (~5-10 min, excluding
        SR-IOV/lock/unlock which must be done before running tests).

        Raises:
            AssertionError: If setup cannot reach the expected state.
        """

        ovs_config: OvsConfig = ConfigurationManager.get_lab_config().get_ovs_config()
        if ovs_config is None:
            get_logger().log_info("No OVS config in lab config — skipping setup")
            return

        self._ensure_sriov_configured(ovs_config)
        self._ensure_app_applied(ovs_config)
        self._ensure_nads_created(ovs_config)
        self._ensure_agent_running()
        self._ensure_bridge_configured(ovs_config)
        self._assign_bridge_ips(ovs_config)
        self._ensure_remote_peer_setup(ovs_config)


    def _ensure_sriov_configured(self, ovs_config: OvsConfig) -> None:
        """Ensure SR-IOV interfaces are configured on the host.

        Checks if pci-sriov interfaces exist. If not, performs:
        lock → modify interface to pci-sriov with VFs → unlock → wait for available.

        Skips if sriov_interfaces is not configured or interfaces already exist.

        Args:
            ovs_config: OVS configuration from lab config.
        """

        sriov_configs = ovs_config.get_sriov_interfaces()
        if not sriov_configs:
            return

        # Check if SR-IOV interfaces already exist
        if_kw = SystemHostInterfaceKeywords(self.ssh_connection)
        host_name = SystemHostListKeywords(self.ssh_connection).get_active_controller().get_host_name()
        iface_list = if_kw.get_system_host_interface_list(host_name)
        existing_sriov = iface_list.get_interfaces_by_class("pci-sriov")
        existing_sriov_names = [iface.get_name() for iface in existing_sriov]

        needs_config = False
        for sriov_cfg in sriov_configs:
            port_name = sriov_cfg.get_port_name()
            if port_name not in existing_sriov_names:
                needs_config = True
                break

        if not needs_config:
            get_logger().log_info("[setup] SR-IOV interfaces already configured")
            return

        get_logger().log_info("[setup] SR-IOV not configured — lock/configure/unlock")
        lock_kw = SystemHostLockKeywords(self.ssh_connection)

        # Lock host
        lock_kw.lock_host(host_name)
        lock_kw.wait_for_host_locked(host_name)

        # Configure each SR-IOV interface
        for sriov_cfg in sriov_configs:
            port_name = sriov_cfg.get_port_name()
            num_vfs = sriov_cfg.get_num_vfs()
            vf_driver = sriov_cfg.get_vf_driver()
            mtu = sriov_cfg.get_mtu()

            get_logger().log_info(f"[setup] Configuring {port_name} as pci-sriov ({num_vfs} VFs)")
            if_kw.system_host_interface_modify(
                host_name, port_name, "pci-sriov",
                num_vfs=num_vfs, vf_driver=vf_driver, mtu=mtu,
            )

        # Unlock and wait for available
        lock_kw.unlock_host(host_name)
        lock_kw.wait_for_host_unlocked(host_name, unlock_wait_timeout=900)
        get_logger().log_info("[setup] SR-IOV configured — host available")

    def _ensure_app_applied(self, ovs_config: OvsConfig) -> None:
        """Ensure OVS application is uploaded and in applied state.

        Handles the full lifecycle: upload (if needed) → helm override → apply.

        Args:
            ovs_config: OVS configuration from lab config.

        Raises:
            AssertionError: If app cannot reach applied state.
        """

        app_list_kw = SystemApplicationListKeywords(self.ssh_connection)
        app_apply_kw = SystemApplicationApplyKeywords(self.ssh_connection)

        if app_apply_kw.is_already_applied("openvswitch"):
            get_logger().log_info("[setup] OVS app already applied")
            return

        # Check if app is uploaded; if not, upload it
        upload_kw = SystemApplicationUploadKeywords(self.ssh_connection)
        if not upload_kw.is_already_uploaded("openvswitch"):
            app_tar = ovs_config.get_helm_overrides().get("app_tar", "/usr/local/share/applications/helm/openvswitch*.tgz")
            get_logger().log_info(f"[setup] OVS app not uploaded — uploading from {app_tar}")
            upload_input = SystemApplicationUploadInput("openvswitch", app_tar)
            upload_kw.system_application_upload(upload_input, timeout=300)

        # Apply helm overrides if configured
        get_logger().log_info("[setup] Applying OVS app with helm overrides")
        override_file = ovs_config.get_helm_overrides().get("override_file", "")
        if override_file:
            helm_kw = SystemHelmOverrideKeywords(self.ssh_connection)
            override_path = get_stx_resource_path(override_file)
            helm_kw.update_helm_override(
                override_path, "openvswitch", "ovs-agent", OVS_NAMESPACE,
            )

        app_apply_kw.system_application_apply("openvswitch", timeout=600)
        app_list_kw.validate_app_status(
            "openvswitch", "applied", timeout=600, polling_sleep_time=10,
            failure_values=["apply-failed"],
        )
        get_logger().log_info("[setup] OVS app applied successfully")

    def _ensure_nads_created(self, ovs_config: OvsConfig) -> None:
        """Ensure Network Attachment Definitions exist with trust/spoofchk.

        Args:
            ovs_config: OVS configuration from lab config.
        """

        nad_kw = KubectlGetNetworkAttachmentKeywords(self.ssh_connection)
        existing_nads = nad_kw.get_network_attachment_names(OVS_NAMESPACE)
        expected_ports = ovs_config.get_ports()
        missing_nads = [p for p in expected_ports if p not in existing_nads]

        if not missing_nads:
            get_logger().log_info("[setup] NADs already exist")
            return

        get_logger().log_info(f"[setup] Creating NADs: {missing_nads}")
        for port in missing_nads:
            resource_name = f"intel.com/pci_sriov_net_{port}"
            nad_yaml = (
                f"apiVersion: k8s.cni.cncf.io/v1\n"
                f"kind: NetworkAttachmentDefinition\n"
                f"metadata:\n"
                f"  name: {port}\n"
                f"  namespace: {OVS_NAMESPACE}\n"
                f"  annotations:\n"
                f"    k8s.v1.cni.cncf.io/resourceName: {resource_name}\n"
                f"spec:\n"
                f"  config: '{{\"cniVersion\":\"0.3.1\",\"type\":\"sriov\","
                f"\"name\":\"{port}\",\"trust\":\"on\",\"spoofchk\":\"off\"}}'\n"
            )
            self.kubectl_apply_yaml(nad_yaml)

        get_logger().log_info("[setup] NADs created")

    def _ensure_agent_running(self) -> None:
        """Ensure ovs-agent pod is running.

        Raises:
            AssertionError: If ovs-agent pod is not running after timeout.
        """

        pods_kw = KubectlGetPodsKeywords(self.ssh_connection)

        def get_agent_status() -> str:
            pods_output = pods_kw.get_pods(namespace=OVS_NAMESPACE)
            for pod in pods_output.get_pods():
                if "ovs-agent" in pod.get_name():
                    return pod.get_status()
            return "NotFound"

        validate_str_contains_with_retry(
            get_agent_status, "Running",
            "ovs-agent pod should be running",
            timeout=60, polling_sleep_time=10,
        )
        get_logger().log_info("[setup] ovs-agent pod running")

    def _ensure_bridge_configured(self, ovs_config: OvsConfig) -> None:
        """Ensure OVS bridge exists with expected ports via CRDs.

        Args:
            ovs_config: OVS configuration from lab config.

        Raises:
            AssertionError: If bridge does not appear after CRD application.
        """

        bridge_name = ovs_config.get_bridge_name()
        ovs_agent = self.get_ovs_agent_pod()
        bridges = self.ovs_vsctl(ovs_agent, "list-br")

        if bridge_name in bridges:
            get_logger().log_info(f"[setup] Bridge {bridge_name} already exists")
            return

        get_logger().log_info(f"[setup] Bridge {bridge_name} not found — applying CRDs")
        crd_file = ovs_config.get_helm_overrides().get("crd_file", "")
        if not crd_file:
            raise AssertionError(
                f"Bridge {bridge_name} not found and no crd_file configured. "
                "Apply OVS CRDs manually or set ovs.helm_overrides.crd_file in lab config."
            )

        crd_path = get_stx_resource_path(crd_file)
        with open(crd_path, "r") as f:
            crd_yaml = f.read()
        self.kubectl_apply_yaml(crd_yaml)

        def check_bridge() -> str:
            agent = self.get_ovs_agent_pod()
            return self.ovs_vsctl(agent, "list-br")

        validate_str_contains_with_retry(
            check_bridge, bridge_name,
            f"Bridge {bridge_name} should be created after CRD apply",
            timeout=60, polling_sleep_time=5,
        )
        get_logger().log_info(f"[setup] Bridge {bridge_name} created")

    def _assign_bridge_ips(self, ovs_config: OvsConfig) -> None:
        """Assign IP addresses to bridge internal ports (ephemeral).

        Bridge IPs are lost on pod restart, so they are always refreshed.

        Args:
            ovs_config: OVS configuration from lab config.
        """
        ovs_agent = self.get_ovs_agent_pod()
        bridge_name = ovs_config.get_bridge_name()
        bridge_ips = ovs_config.get_bridge_ips()

        for vlan_key, ip in bridge_ips.items():
            if not ip:
                continue
            ip_version = "-6 " if ":" in ip else ""
            prefix = "64" if ":" in ip else "24"

            if vlan_key == "untagged":
                self.exec_in_pod(
                    ovs_agent,
                    f"ip {ip_version}addr add {ip}/{prefix} dev {bridge_name} 2>/dev/null || true",
                )
                self.exec_in_pod(ovs_agent, f"ip link set {bridge_name} up")
            else:
                vlan_id = vlan_key.replace("vlan", "")
                self.ovs_vsctl(
                    ovs_agent,
                    f"--may-exist add-port {bridge_name} {vlan_key} tag={vlan_id}"
                    f" -- set interface {vlan_key} type=internal",
                )
                self.exec_in_pod(
                    ovs_agent,
                    f"ip {ip_version}addr add {ip}/{prefix} dev {vlan_key} 2>/dev/null || true",
                )
                self.exec_in_pod(ovs_agent, f"ip link set {vlan_key} up")

        get_logger().log_info("[setup] Bridge IPs assigned")

    def _ensure_remote_peer_setup(self, ovs_config: OvsConfig) -> None:
        """Ensure the remote peer lab has OVS configured.

        Opens a proper SSHConnection to the remote peer and reuses existing
        keywords to verify/configure OVS (app upload, apply, bridge IPs).

        Skips if no remote_peer_ip is configured in the lab config.

        Args:
            ovs_config: OVS configuration from lab config.
        """
        remote_ip = ovs_config.get_remote_peer_ip()
        if not remote_ip:
            get_logger().log_info("[setup] No remote peer configured — skipping")
            return

        remote_password = ovs_config.get_remote_peer_password()
        get_logger().log_info(f"[setup] Checking remote peer {remote_ip}")

        # Create SSH connection to remote peer
        remote_ssh = SSHConnectionManager.create_ssh_connection(
            host=remote_ip,
            user="sysadmin",
            password=remote_password,
            name="ovs_remote_peer",
        )

        try:
            self._setup_remote_ovs(remote_ssh, ovs_config)
        finally:
            remote_ssh.disconnect()

    def _setup_remote_ovs(self, remote_ssh: SSHConnection, ovs_config: OvsConfig) -> None:
        """Configure OVS on the remote peer using proper keywords.

        Args:
            remote_ssh: SSH connection to the remote peer.
            ovs_config: OVS configuration from lab config.
        """
        # Check if OVS app is already applied on remote
        remote_app_apply_kw = SystemApplicationApplyKeywords(remote_ssh)
        remote_app_list_kw = SystemApplicationListKeywords(remote_ssh)

        if remote_app_apply_kw.is_already_applied("openvswitch"):
            get_logger().log_info("[setup] Remote peer OVS already applied")
        else:
            get_logger().log_info("[setup] Remote peer OVS not applied — configuring")

            # Upload if not present
            remote_upload_kw = SystemApplicationUploadKeywords(remote_ssh)
            if not remote_upload_kw.is_already_uploaded("openvswitch"):
                app_tar = ovs_config.get_helm_overrides().get(
                    "app_tar", "/usr/local/share/applications/helm/openvswitch*.tgz"
                )
                get_logger().log_info(f"[setup] Uploading OVS app on remote: {app_tar}")
                upload_input = SystemApplicationUploadInput("openvswitch", app_tar)
                remote_upload_kw.system_application_upload(upload_input, timeout=300)

            # Apply helm overrides on remote if configured
            override_file = ovs_config.get_helm_overrides().get("override_file", "")
            if override_file:
                remote_helm_kw = SystemHelmOverrideKeywords(remote_ssh)
                override_path = get_stx_resource_path(override_file)
                remote_helm_kw.update_helm_override(
                    override_path, "openvswitch", "ovs-agent", OVS_NAMESPACE,
                )

            # Apply
            remote_app_apply_kw.system_application_apply("openvswitch", timeout=600)
            remote_app_list_kw.validate_app_status(
                "openvswitch", "applied", timeout=600, polling_sleep_time=15,
                failure_values=["apply-failed"],
            )

        # Assign bridge IPs on remote peer (ephemeral — always refresh)
        self._assign_remote_bridge_ips(remote_ssh, ovs_config)
        get_logger().log_info("[setup] Remote peer setup complete")

    def _assign_remote_bridge_ips(self, remote_ssh: SSHConnection, ovs_config: OvsConfig) -> None:
        """Assign bridge IPs on the remote peer (ephemeral, always refresh).

        Args:
            remote_ssh: SSH connection to the remote peer.
            ovs_config: OVS configuration from lab config.
        """
        remote_ovs_kw = OpenvSwitchKeywords(remote_ssh)
        remote_agent = remote_ovs_kw.get_ovs_agent_pod()
        bridge_name = ovs_config.get_bridge_name()
        peer_ips = ovs_config.get_peer_ips()

        for vlan_key, ip in peer_ips.items():
            if not ip:
                continue
            ip_version = "-6 " if ":" in ip else ""
            prefix = "64" if ":" in ip else "24"

            if vlan_key == "untagged":
                remote_ovs_kw.exec_in_pod(
                    remote_agent,
                    f"ip {ip_version}addr add {ip}/{prefix} dev {bridge_name} 2>/dev/null || true",
                )
                remote_ovs_kw.exec_in_pod(remote_agent, f"ip link set {bridge_name} up")
            else:
                vlan_id = vlan_key.replace("vlan", "")
                remote_ovs_kw.ovs_vsctl(
                    remote_agent,
                    f"--may-exist add-port {bridge_name} {vlan_key} tag={vlan_id}"
                    f" -- set interface {vlan_key} type=internal",
                )
                remote_ovs_kw.exec_in_pod(
                    remote_agent,
                    f"ip {ip_version}addr add {ip}/{prefix} dev {vlan_key} 2>/dev/null || true",
                )
                remote_ovs_kw.exec_in_pod(remote_agent, f"ip link set {vlan_key} up")

        get_logger().log_info("[setup] Remote peer bridge IPs assigned")
