"""Owned cross-node traffic fixtures for policy CHILD_SA consumers."""

import json
import re
from collections.abc import Callable
from pathlib import Path
from shlex import quote
from string import Template
from uuid import uuid4

import yaml

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.cloud_platform.applications.ipsec_policy_keywords import IPsecPolicyKeywords
from keywords.cloud_platform.applications.ipsec_policy_state_keywords import OWNER_LABEL, IPsecPolicyStateKeywords
from keywords.cloud_platform.applications.object.ipsec_policy_traffic_evidence import IPsecPolicyTrafficEvidence
from keywords.cloud_platform.applications.object.ipsec_policy_traffic_input import IPsecPolicyTrafficInput
from keywords.cloud_platform.applications.object.ipsec_policy_traffic_output import IPsecPolicyTrafficOutput
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.get_resource.object.endpoint_slice_list_output import EndpointSliceListOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords
from keywords.k8s.pods.object.pod_json_output import PodJsonOutput
from keywords.linux.hostname_keywords import HostnameKeywords

ENDPOINT_TIMEOUT = 120
TUNNEL_TIMEOUT = 120
COUNTER_TIMEOUT = 30
POLL_INTERVAL = 2
WORKLOAD_LIFETIME = 3600


class IPsecPolicyTrafficKeywords(K8sBaseKeyword):
    """Place explicitly selected clients and servers and verify bounded traffic."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str | None = None):
        """Compose traffic operations with an independently owned recovery state.

        Args:
            ssh_connection (SSHConnection): Controller connection.
            kubeconfig_path (str | None): Optional kubeconfig path.
        """
        super().__init__(ssh_connection, kubeconfig_path)
        self.state = IPsecPolicyStateKeywords(ssh_connection, kubeconfig_path)
        self.policy_keywords = IPsecPolicyKeywords(ssh_connection, kubeconfig_path)
        self.traffic_input = None
        self.cluster_addresses = None

    def get_state_keywords(self) -> IPsecPolicyStateKeywords:
        """Return this fixture's lifecycle operations without a second state.

        Returns:
            IPsecPolicyStateKeywords: The shared fixture lifecycle keyword.
        """
        return self.state

    def capture_state(self, addfinalizer: Callable, exclusive: bool = False) -> None:
        """Capture this fixture's baseline before creating traffic resources.

        Args:
            addfinalizer (Callable): Recovery registration function.
            exclusive (bool): Explicit exclusive disposable-lab assignment.
        """
        self.state.capture_state(addfinalizer, exclusive)

    def create_traffic_fixture(self, traffic_input: IPsecPolicyTrafficInput) -> None:
        """Create owned server/client resources for an explicit scenario input.

        Call capture_state first to register partial-setup recovery.

        Args:
            traffic_input (IPsecPolicyTrafficInput): Image, topology and flow input.
        """
        image = traffic_input.get_image()
        client_node = traffic_input.get_client_node()
        server_node = traffic_input.get_server_node()
        protocol = traffic_input.get_protocol()
        port = traffic_input.get_port()
        family = traffic_input.get_family()
        same_node = traffic_input.get_same_node()

        if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", image):
            raise KeywordException("Configure an immutable Python-capable traffic image")
        if protocol not in ("tcp", "udp") or type(port) is not int or not 1 <= port <= 65535:
            raise KeywordException("Configure TCP/UDP and a valid traffic port")
        addresses = self.policy_keywords.get_eligible_nodes(family)
        if client_node not in addresses.get_node_names() or server_node not in addresses.get_node_names() or (client_node == server_node) != same_node:
            raise KeywordException("Requested node placement does not match eligible topology")
        if self.traffic_input is not None:
            raise KeywordException("Use a separate fixture for each traffic scenario")
        self.traffic_input = traffic_input
        self.cluster_addresses = addresses

        self.state.apply_owned_resource({"apiVersion": "v1", "kind": "Namespace", "metadata": self._get_metadata(self.state.get_run_id(), False)})
        script = Path(__file__).with_name("resources").joinpath("ipsec_policy_traffic.py").read_text()
        self.state.apply_owned_resource({"apiVersion": "v1", "kind": "ConfigMap", "metadata": self._get_metadata(f"{self.state.get_run_id()}-script"), "data": {"traffic.py": script}})
        for role, node in (("server", server_node), ("client", client_node)):
            name = f"{self.state.get_run_id()}-{role}"
            command = ["python3", "/probe/traffic.py", "server", "--family", str(family), "--protocol", protocol, "--port", str(port), "--identity", self.state.get_run_id()] if role == "server" else ["python3", "-c", f"import time; time.sleep({WORKLOAD_LIFETIME})"]
            manifest = self._render_template("ipsec_policy_pod.yaml", metadata=self._get_metadata(name), node=node, lifetime=WORKLOAD_LIFETIME, role=role, image=image, command=command, script_name=f"{self.state.get_run_id()}-script")
            spec = manifest["spec"]
            if role == "server":
                probe = ["python3", "/probe/traffic.py", "client", "--family", str(family), "--protocol", protocol, "--port", str(port), "--identity", self.state.get_run_id(), "--address", "::1" if family == 6 else "127.0.0.1", "--nonce", "readiness", "--count", "1", "--timeout", "1"]
                spec["containers"][0]["readinessProbe"] = {
                    "exec": {"command": probe},
                    "initialDelaySeconds": 1,
                    "periodSeconds": 2,
                    "timeoutSeconds": 2,
                    "failureThreshold": 30,
                }
            self.state.apply_owned_resource(manifest)
        self.state.apply_owned_resource(self._render_template("ipsec_policy_service.yaml", metadata=self._get_metadata(f"{self.state.get_run_id()}-service"), family=f"IPv{family}", server_name=f"{self.state.get_run_id()}-server", protocol=protocol, transport=protocol.upper(), port=port))
        KubectlWaitPodKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).wait_for_pods_ready(quote(f"{OWNER_LABEL}={self.state.get_run_id()}"), quote(self.state.get_run_id()))
        self.wait_for_endpoint()

    @staticmethod
    def _render_template(filename: str, **values) -> dict:
        """Render repository-owned YAML with JSON-quoted input values.

        Args:
            filename (str): Repository template basename.
            **values: Typed substitution values.

        Returns:
            dict: Kubernetes resource manifest.
        """
        template = Path(__file__).with_name("resources").joinpath(filename).read_text()
        return yaml.safe_load(Template(template).substitute({key: json.dumps(value) for key, value in values.items()}))

    def _get_metadata(self, name: str, namespaced: bool = True) -> dict:
        """Build owned fixture metadata.

        Args:
            name (str): Run-prefixed resource name.
            namespaced (bool): Whether the resource belongs to the owned namespace.

        Returns:
            dict: Resource metadata.
        """
        metadata = {"name": name, "labels": {OWNER_LABEL: self.state.get_run_id(), "app": name}}
        if namespaced:
            metadata["namespace"] = self.state.get_run_id()
        return metadata

    def create_service_policy(self) -> None:
        """Create a policy targeting only this run's service and selected port."""
        self.state.apply_owned_resource(self._render_template("ipsec_policy_policy.yaml", metadata=self._get_metadata(f"{self.state.get_run_id()}-policy", False), name=self.state.get_run_id(), service=f"{self.state.get_run_id()}-service", namespace=self.state.get_run_id(), ports=f"{self.traffic_input.get_protocol()}/{self.traffic_input.get_port()}"))

    def wait_for_endpoint(self, timeout: int = ENDPOINT_TIMEOUT) -> str:
        """Resolve one current ready service endpoint with independent pod identity.

        Args:
            timeout (int): Maximum endpoint publication wait.

        Returns:
            str: Verified server pod IP.
        """
        reader = KubectlGetResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())

        def observe_endpoint() -> ValidationResponse:
            """Read fresh server and EndpointSlices for the exact owned service.

            Returns:
                ValidationResponse: Endpoint evidence or a pending observation.
            """
            server = PodJsonOutput(reader.get_resource_field("pod", quote(f"{self.state.get_run_id()}-server"), "{@}", quote(self.state.get_run_id())))
            if server.get_node_name() != self.traffic_input.get_server_node():
                raise KeywordException("Server was placed on the wrong node")
            slices = EndpointSliceListOutput(reader.get_resource_field("endpointslices", "", "{@}", quote(self.state.get_run_id())))
            address = slices.get_ready_endpoint_address(f"{self.state.get_run_id()}-service", server, self.traffic_input.get_port(), self.traffic_input.get_protocol(), self.traffic_input.get_family())
            return ValidationResponse(address is not None, address)

        return validate_equals_with_retry(observe_endpoint, True, "Owned service endpoint matches server pod", timeout=timeout, polling_sleep_time=POLL_INTERVAL)

    def send_traffic(self, count: int = 3) -> IPsecPolicyTrafficOutput:
        """Send bounded requests and reject stale, empty or wrong-peer responses.

        Args:
            count (int): Request count, between one and twenty.

        Returns:
            IPsecPolicyTrafficOutput: Verified per-run traffic response.
        """
        if type(count) is not int or not 1 <= count <= 20:
            raise KeywordException("Traffic count must be between one and twenty")
        address = self.wait_for_endpoint()
        nonce = uuid4().hex
        expected = {"nonce": nonce, "server": self.state.get_run_id(), "protocol": self.traffic_input.get_protocol(), "port": self.traffic_input.get_port(), "count": count, "address": address}
        command = f"python3 /probe/traffic.py client --family {self.traffic_input.get_family()} --protocol {self.traffic_input.get_protocol()} --port {self.traffic_input.get_port()} --identity {quote(self.state.get_run_id())} --address {quote(address)} --nonce {nonce} --count {count}"
        output = KubectlExecInPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).run_pod_exec_cmd(quote(f"{self.state.get_run_id()}-client"), command, options=f"-n {quote(self.state.get_run_id())} -c client")
        return IPsecPolicyTrafficOutput(output, expected)

    def verify_policy_traffic(self, client_connection: SSHConnection) -> IPsecPolicyTrafficEvidence:
        """Require fresh traffic and increasing counters on the exact policy tunnel.

        Args:
            client_connection (SSHConnection): Explicit connection to the client node.

        Returns:
            IPsecPolicyTrafficEvidence: Traffic and matched tunnel evidence.
        """
        if self.traffic_input.get_same_node():
            raise KeywordException("Same-node traffic is not cross-node tunnel proof")
        if HostnameKeywords(client_connection).get_hostname() != self.traffic_input.get_client_node():
            raise KeywordException("SA reader is connected to the wrong node")
        destination = self.wait_for_endpoint()
        reader = KubectlGetResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())
        client = PodJsonOutput(reader.get_resource_field("pod", quote(f"{self.state.get_run_id()}-client"), "{@}", quote(self.state.get_run_id())))
        if client.get_node_name() != self.traffic_input.get_client_node():
            raise KeywordException("Client was placed on the wrong node")
        sources = client.get_pod_ips(self.traffic_input.get_family())
        if len(sources) != 1:
            raise KeywordException("Client lacks an unambiguous address for the requested family")
        flow = (self.cluster_addresses.get_address(self.traffic_input.get_client_node()), self.cluster_addresses.get_address(self.traffic_input.get_server_node()), sources[0], destination, self.traffic_input.get_protocol(), self.traffic_input.get_port())
        # Establish the tunnel before taking a counter baseline. Subsequent traffic
        # must advance that exact association; rekey requires a fresh observation.
        self.send_traffic()

        def observe_tunnels() -> ValidationResponse:
            """Read matching installed policy tunnels after asynchronous reconciliation.

            Returns:
                ValidationResponse: Nonempty tunnel evidence or pending state.
            """
            counters = {sa.get_identity(): sa.get_counters() for sa in self.policy_keywords.read_policy_security_associations(client_connection).get_installed_tunnels() if sa.matches_flow(*flow)}
            return ValidationResponse(bool(counters), counters)

        before = validate_equals_with_retry(observe_tunnels, True, "Installed policy tunnel matches independent flow", timeout=TUNNEL_TIMEOUT, polling_sleep_time=POLL_INTERVAL)
        result = self.send_traffic()

        def observe_counter_progress() -> ValidationResponse:
            """Require fresh outbound counters on a baseline association.

            Returns:
                ValidationResponse: Fresh traffic and matching tunnel counters.
            """
            after = observe_tunnels().get_value_to_return()
            # Ingress/egress policies can use distinct CHILD_SAs. Only outbound
            # counters belong to this egress assertion; echo verifies the response.
            advanced = [identity for identity in before.keys() & after.keys() if all(after[identity][key] > before[identity][key] for key in ("bytes-out", "packets-out"))]
            return ValidationResponse(bool(advanced), IPsecPolicyTrafficEvidence(result, advanced, before, after))

        return validate_equals_with_retry(observe_counter_progress, True, "Policy egress counters advanced without rekey", timeout=COUNTER_TIMEOUT, polling_sleep_time=POLL_INTERVAL)
