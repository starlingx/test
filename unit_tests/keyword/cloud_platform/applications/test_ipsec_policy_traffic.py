"""Exercise the actual traffic workload locally and fixture failure boundaries."""

import argparse
import importlib.util
import json
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import NonCallableMock, patch

import pytest

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.applications.ipsec_policy_traffic_keywords import IPsecPolicyTrafficKeywords
from keywords.cloud_platform.applications.object.ipsec_policy_traffic_input import IPsecPolicyTrafficInput
from keywords.cloud_platform.applications.object.ipsec_policy_traffic_output import IPsecPolicyTrafficOutput
from keywords.cloud_platform.security.objects.ipsec_policy_sa_output import IPsecPolicySAOutput
from keywords.k8s.get_resource.object.endpoint_slice_list_output import EndpointSliceListOutput
from keywords.k8s.get_resource.object.kubernetes_resource_list_output import KubernetesResourceListOutput
from keywords.k8s.pods.object.pod_json_output import PodJsonOutput

SCRIPT = Path(__file__).resolve().parents[4] / "keywords/cloud_platform/applications/resources/ipsec_policy_traffic.py"


@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_real_echo_and_wrong_identity(protocol):
    """Real sockets establish bounded traffic and reject a wrong peer identity."""
    kind = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM
    with socket.socket(socket.AF_INET, kind) as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    common = ["--family", "4", "--protocol", protocol, "--port", str(port)]
    server_command = [sys.executable, str(SCRIPT), "server", *common, "--identity", "expected", "--lifetime", "20"]
    with ThreadPoolExecutor(max_workers=1) as reader, subprocess.Popen(server_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        try:
            # Windows selectors accept sockets only, so read the pipe on a
            # background thread and put the deadline on the result.
            readiness = reader.submit(process.stdout.readline)
            assert readiness.result(timeout=5).strip() == b"TRAFFIC SERVER READY"
            command = [sys.executable, str(SCRIPT), "client", *common, "--identity", "expected", "--address", "127.0.0.1", "--nonce", "fresh", "--count", "2", "--timeout", "1"]
            response = subprocess.run(command, capture_output=True, text=True, timeout=4)
            assert response.returncode == 0, response.stderr
            assert json.loads(response.stdout)["count"] == 2
            command[command.index("expected")] = "wrong-peer"
            response = subprocess.run(command, capture_output=True, text=True, timeout=4)
            assert response.returncode != 0
            assert "Wrong peer" in response.stderr
        finally:
            # Terminating the child also releases a pending readiness read.
            process.kill()


@pytest.fixture
def fixture():
    """Provide a fixture without performing any controller operations."""
    connection = NonCallableMock()
    connection.get_return_code.return_value = 0
    with patch("keywords.base_keyword.get_logger"), patch("framework.validation.validation.get_logger"):
        yield IPsecPolicyTrafficKeywords(connection, "/config"), connection


@pytest.mark.parametrize("same_node", [True, False])
def test_explicit_node_placement_required(fixture, monkeypatch, same_node):
    """Contradictory same/different-node requests cannot become traffic proof."""
    keyword, connection = fixture
    monkeypatch.setattr(keyword.policy_keywords, "get_eligible_nodes", lambda family: addresses)
    addresses = NonCallableMock()
    addresses.get_node_names.return_value = ("node-a", "node-b")
    server = "node-b" if same_node else "node-a"
    with pytest.raises(KeywordException, match="placement"):
        keyword.create_traffic_fixture(IPsecPolicyTrafficInput("image@sha256:" + "a" * 64, "node-a", server, same_node=same_node))
    connection.send.assert_not_called()


@pytest.mark.parametrize("output", ["", "{}", '{"nonce":"old"}', "not JSON"])
def test_empty_and_stale_client_evidence_rejected(fixture, monkeypatch, output):
    """A zero command status alone cannot establish successful traffic."""
    keyword, _ = fixture
    keyword.traffic_input = IPsecPolicyTrafficInput("image", "node-a", "node-b")
    monkeypatch.setattr(keyword, "wait_for_endpoint", lambda: "192.0.2.1")
    with patch("keywords.cloud_platform.applications.ipsec_policy_traffic_keywords.KubectlExecInPodsKeywords") as execute:
        execute.return_value.run_pod_exec_cmd.return_value = output
        with pytest.raises(KeywordException):
            keyword.send_traffic()


def test_udp_retransmits_timeout_but_stays_bounded():
    """A transient dropped datagram retries; persistent loss still raises."""
    spec = importlib.util.spec_from_file_location("ipsec_traffic_payload", SCRIPT)
    payload = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(payload)
    arguments = argparse.Namespace(family=4, protocol="udp", count=1, timeout=1, address="192.0.2.1", port=18080, nonce="fresh", identity="server")
    response = json.dumps({"nonce": "fresh-0", "server": "server", "protocol": "udp", "port": 18080}).encode()
    with patch.object(payload.socket, "socket") as factory:
        client = factory.return_value.__enter__.return_value
        client.recv.side_effect = [TimeoutError(), response]
        payload.run_client(arguments)
        assert client.sendall.call_count == 2
        client.reset_mock()
        client.recv.side_effect = TimeoutError("persistent loss")
        with pytest.raises(TimeoutError, match="persistent loss"):
            payload.run_client(arguments)
        assert client.sendall.call_count == 3


@pytest.mark.parametrize("protocol,family", [("tcp", 4), ("udp", 6)])
def test_template_fixture_preserves_workload_contract(fixture, monkeypatch, protocol, family):
    """Input beans and YAML templates retain placement, limits and ownership."""
    keyword, _ = fixture
    addresses = NonCallableMock()
    addresses.get_node_names.return_value = ("node-a", "node-b")
    monkeypatch.setattr(keyword.policy_keywords, "get_eligible_nodes", lambda value: addresses)
    manifests = []
    monkeypatch.setattr(keyword.get_state_keywords(), "apply_owned_resource", lambda manifest: manifests.append(manifest))
    monkeypatch.setattr(keyword, "wait_for_endpoint", lambda: "192.0.2.1")
    with patch("keywords.cloud_platform.applications.ipsec_policy_traffic_keywords.KubectlWaitPodKeywords"):
        keyword.create_traffic_fixture(IPsecPolicyTrafficInput("image@sha256:" + "a" * 64, "node-a", "node-b", protocol=protocol, family=family))
        keyword.create_service_policy()
    server, client = [item for item in manifests if item["kind"] == "Pod"]
    assert (server["spec"]["nodeName"], client["spec"]["nodeName"]) == ("node-b", "node-a")
    for pod in (server, client):
        assert pod["spec"]["automountServiceAccountToken"] is False
        assert pod["spec"]["activeDeadlineSeconds"] == 3600
        assert pod["spec"]["containers"][0]["volumeMounts"][0]["readOnly"] is True
        assert pod["spec"]["containers"][0]["resources"]["limits"] == {"cpu": "100m", "memory": "128Mi"}
    assert server["spec"]["containers"][0]["readinessProbe"]["exec"]["command"][2] == "client"
    service = next(item for item in manifests if item["kind"] == "Service")
    assert service["spec"]["ipFamilies"] == [f"IPv{family}"]
    assert service["spec"]["ports"][0]["protocol"] == protocol.upper()
    policy = manifests[-1]
    assert policy["kind"] == "IPsecPolicy"
    assert "namespace" not in policy["metadata"]
    assert policy["spec"]["policies"][0]["serviceports"] == f"{protocol}/18080"


def test_typed_traffic_response_preserves_correlated_fields(fixture, monkeypatch):
    """The real client-response path returns validated getter-based evidence."""
    keyword, _ = fixture
    keyword.traffic_input = IPsecPolicyTrafficInput("image", "node-a", "node-b")
    monkeypatch.setattr(keyword, "wait_for_endpoint", lambda: "192.0.2.1")
    response = {"nonce": "fresh", "server": keyword.get_state_keywords().get_run_id(), "protocol": "tcp", "port": 18080, "count": 3, "address": "192.0.2.1"}
    with patch("keywords.cloud_platform.applications.ipsec_policy_traffic_keywords.uuid4") as nonce, patch("keywords.cloud_platform.applications.ipsec_policy_traffic_keywords.KubectlExecInPodsKeywords") as execute:
        nonce.return_value.hex = "fresh"
        execute.return_value.run_pod_exec_cmd.return_value = [json.dumps(response)]
        output = keyword.send_traffic()
    assert (output.get_nonce(), output.get_protocol(), output.get_port(), output.get_count(), output.get_address()) == ("fresh", "tcp", 18080, 3, "192.0.2.1")


def test_policy_verification_returns_typed_counter_evidence(fixture, monkeypatch):
    """Orchestration retains exact flow matching and fresh counter progression."""
    keyword, connection = fixture
    keyword.traffic_input = IPsecPolicyTrafficInput("image", "node-a", "node-b")
    addresses = NonCallableMock()
    addresses.get_address.side_effect = lambda node: {"node-a": "192.0.2.1", "node-b": "192.0.2.2"}[node]
    keyword.cluster_addresses = addresses
    monkeypatch.setattr(keyword, "wait_for_endpoint", lambda: "10.2.0.3")
    monkeypatch.setattr(keyword, "send_traffic", lambda: IPsecPolicyTrafficOutput(json.dumps({"nonce": "fresh"}), {"nonce": "fresh"}))
    connection.send.return_value = json.dumps({"spec": {"nodeName": "node-a"}, "status": {"podIPs": [{"ip": "10.1.0.7"}]}})
    before = "list-sa event {k8s-node-node-b {state=ESTABLISHED local-host=192.0.2.1 remote-host=192.0.2.2 child-sas {flow {name=tcp_service uniqueid=1 state=INSTALLED mode=TUNNEL local-ts=[10.1.0.0/24[tcp]] remote-ts=[10.2.0.3/32[tcp/18080]] bytes-in=0 packets-in=0 bytes-out=10 packets-out=1}}}}"
    observations = iter([IPsecPolicySAOutput(before), IPsecPolicySAOutput(before.replace("bytes-out=10 packets-out=1", "bytes-out=20 packets-out=2"))])
    monkeypatch.setattr(keyword.policy_keywords, "read_policy_security_associations", lambda client: next(observations))
    with patch("keywords.cloud_platform.applications.ipsec_policy_traffic_keywords.HostnameKeywords") as hostname, patch("keywords.cloud_platform.applications.ipsec_policy_traffic_keywords.validate_equals_with_retry") as retry:
        hostname.return_value.get_hostname.return_value = "node-a"

        def observe(function, *args, **kwargs):
            result = function()
            assert result.get_value_to_validate() is True
            return result.get_value_to_return()

        retry.side_effect = observe
        evidence = keyword.verify_policy_traffic(connection)
    assert evidence.get_traffic().get_nonce() == "fresh"
    association = evidence.get_associations()[0]
    assert evidence.get_before_counters()[association]["packets-out"] == 1
    assert evidence.get_after_counters()[association]["packets-out"] == 2


@pytest.mark.parametrize("mutation,expected", [("none", "10.2.0.3"), ("not-ready", None), ("terminating", None), ("other-service", None), ("ipv6", "2001:db8::3")])
def test_endpoint_output_ready_and_pending(mutation, expected):
    """Endpoint interpretation retains readiness, service and family filtering."""
    address = "2001:db8::3" if mutation == "ipv6" else "10.2.0.3"
    pod = PodJsonOutput({"metadata": {"uid": "server"}, "spec": {"nodeName": "node-b"}, "status": {"podIPs": [{"ip": address}]}})
    endpoint = {"conditions": {"ready": mutation != "not-ready", "terminating": mutation == "terminating"}, "targetRef": {"uid": "server"}, "nodeName": "node-b", "addresses": [address]}
    resource = {"metadata": {"labels": {"kubernetes.io/service-name": "other" if mutation == "other-service" else "service"}}, "ports": [{"port": 18080, "protocol": "TCP"}], "endpoints": [endpoint]}
    output = EndpointSliceListOutput(json.dumps({"items": [resource]}))
    assert output.get_ready_endpoint_address("service", pod, 18080, "tcp", 6 if mutation == "ipv6" else 4) == expected


@pytest.mark.parametrize("mutation,message", [("port", "wrong protocol or port"), ("protocol", "wrong protocol or port"), ("uid", "unexpected peer"), ("node", "unexpected peer"), ("address", "inconsistent endpoint"), ("duplicate", "inconsistent endpoint")])
def test_endpoint_output_rejects_wrong_identity(mutation, message):
    """Wrong peer, transport, address and duplicate evidence cannot satisfy polling."""
    pod = PodJsonOutput({"metadata": {"uid": "server"}, "spec": {"nodeName": "node-b"}, "status": {"podIPs": [{"ip": "10.2.0.3"}]}})
    endpoint = {"conditions": {"ready": True}, "targetRef": {"uid": "other" if mutation == "uid" else "server"}, "nodeName": "other" if mutation == "node" else "node-b", "addresses": ["10.2.0.4" if mutation == "address" else "10.2.0.3"]}
    resource = {"metadata": {"labels": {"kubernetes.io/service-name": "service"}}, "ports": [{"port": 18081 if mutation == "port" else 18080, "protocol": "UDP" if mutation == "protocol" else "TCP"}], "endpoints": [endpoint, endpoint] if mutation == "duplicate" else [endpoint]}
    with pytest.raises(KeywordException, match=message):
        EndpointSliceListOutput(json.dumps({"items": [resource]})).get_ready_endpoint_address("service", pod, 18080, "tcp", 4)


def test_resource_labels_preserve_absence_and_pod_snapshot():
    """Typed snapshots preserve absent labels and isolate mutable input."""
    output = KubernetesResourceListOutput(json.dumps({"items": [{"metadata": {"name": "node-a", "labels": {"agent": "enabled"}}}, {"metadata": {"name": "node-b"}}]}))
    assert output.get_labels("agent") == {"node-a": "enabled", "node-b": None}
    assert output.find_resource("missing") is None
    assert output.find_resource("node-a").get_label("agent") == "enabled"
    source = {"metadata": {"uid": "original"}, "spec": {"nodeName": "node-a"}, "status": {"podIPs": [{"ip": "10.2.0.3"}, {"ip": "2001:db8::3"}]}}
    pod = PodJsonOutput(source)
    source["metadata"]["uid"] = "replacement"
    assert pod.get_uid() == "original"
    assert pod.get_pod_ips(4) == ["10.2.0.3"]
    assert pod.get_pod_ips(6) == ["2001:db8::3"]


def test_traffic_capture_uses_same_state(fixture):
    """Capture and resource creation share a single lifecycle identity."""
    keyword, _ = fixture
    state = keyword.get_state_keywords()
    with patch.object(state, "capture_state") as capture:
        finalizers = []
        keyword.capture_state(finalizers.append, exclusive=True)
        capture.assert_called_once_with(finalizers.append, True)
    assert keyword.get_state_keywords().get_run_id() == state.get_run_id()


def test_endpoint_keyword_reads_fresh_typed_evidence(fixture):
    """The production read-to-parser path resolves an owned endpoint."""
    keyword, connection = fixture
    keyword.traffic_input = IPsecPolicyTrafficInput("image", "node-a", "node-b")
    pod = {"metadata": {"uid": "server"}, "spec": {"nodeName": "node-b"}, "status": {"podIPs": [{"ip": "10.2.0.3"}]}}
    resource = {"metadata": {"labels": {"kubernetes.io/service-name": keyword.get_state_keywords().get_run_id() + "-service"}}, "ports": [{"port": 18080, "protocol": "TCP"}], "endpoints": [{"conditions": {"ready": True}, "targetRef": {"uid": "server"}, "nodeName": "node-b", "addresses": ["10.2.0.3"]}]}
    connection.send.side_effect = [json.dumps(pod), json.dumps({"items": [resource]})]
    assert keyword.wait_for_endpoint() == "10.2.0.3"
