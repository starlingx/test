"""Exercise endpoint execution and response parsing together."""

import json
import shlex
from unittest.mock import NonCallableMock, patch

import pytest
import yaml

from keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords import APPLICATION_NAME, NodeInterfaceMetricsExporterKeywords


@pytest.fixture
def reader():
    """Provide a reader using a fake SSH transport and disabled keyword logging."""
    connection = NonCallableMock()
    connection.send.return_value = "sample 1\n\n200"
    connection.get_return_code.return_value = 0
    with patch("keywords.base_keyword.get_logger"):
        yield NodeInterfaceMetricsExporterKeywords(connection, "/etc/kubernetes/admin.conf"), connection


@pytest.mark.parametrize("address,authority", [("192.0.2.1", "192.0.2.1"), ("2001:db8::1", "[2001:db8::1]")])
def test_encoded_endpoint(reader, address, authority):
    """Host and unsafe device identifiers survive command construction safely."""
    keyword, connection = reader
    response = keyword.read_endpoint(address, ("metrics", "device", "a/b;$(id)"))
    command = shlex.split(connection.send.call_args.args[0])
    assert command[-1] == f"http://{authority}:9110/metrics/device/a%2Fb%3B%24%28id%29"
    assert response.get_status_code() == 200
    assert response.get_body() == "sample 1\n"
    assert connection.send.call_args.kwargs["command_timeout"] == 40


@pytest.mark.parametrize("status", [404, 405])
def test_http_failure_is_available_to_negative_tests(reader, status):
    """An HTTP rejection remains inspectable rather than becoming a transport error."""
    keyword, connection = reader
    connection.send.return_value = f"rejected\n{status}"
    response = keyword.read_endpoint("192.0.2.1", method="POST")
    assert response.get_status_code() == status
    assert response.get_body() == "rejected"


@pytest.mark.parametrize("code,output", [(7, "\n000"), (28, "partial\n200"), (None, "ok\n200"), (0, "no status"), (0, "\n000")])
def test_failed_or_malformed_response_rejected(reader, code, output):
    """Partial bodies and missing status must never become successful evidence."""
    keyword, connection = reader
    connection.send.return_value = output
    connection.get_return_code.return_value = code
    with pytest.raises(ValueError):
        keyword.read_endpoint("192.0.2.1")


@pytest.mark.parametrize("kwargs", [{"timeout": 0}, {"timeout": True}, {"method": "GET;id"}])
def test_invalid_inputs_do_not_execute(reader, kwargs):
    """Reject unsafe or unbounded inputs before opening an HTTP request."""
    keyword, connection = reader
    with pytest.raises(ValueError):
        keyword.read_endpoint("192.0.2.1", **kwargs)
    connection.send.assert_not_called()


def test_real_ssh_line_output(reader):
    """Exercise the list-of-lines format returned by SSHConnection."""
    keyword, connection = reader
    connection.send.return_value = ['metric{device="eth0"} 1\n', "\n", "200"]
    metrics = keyword.read_metrics("192.0.2.1")
    assert metrics.require_sample("metric", {"device": "eth0"}) == 1


def test_read_metrics_rejects_http_error(reader):
    """A valid-looking body with a failed HTTP status cannot pass a scrape."""
    keyword, connection = reader
    connection.send.return_value = "metric 1\n500"
    with pytest.raises(ValueError, match="HTTP 500"):
        keyword.read_metrics("192.0.2.1")


@pytest.mark.parametrize("digest,expected", [("sha256:" + "a" * 64, True), ("sha256:" + "b" * 64, False)])
def test_candidate_running_digest(reader, monkeypatch, digest, expected):
    """The requested tag/version alone cannot establish candidate identity."""
    keyword, _ = reader
    monkeypatch.setattr(keyword, "application_state", lambda: ("candidate", "applied"))
    monkeypatch.setattr(keyword, "wait_ready", lambda: {"worker-0": {"status": {"containerStatuses": [{"name": "exporter", "imageID": "docker-pullable://registry/image@" + digest}]}}})
    if expected:
        assert keyword.verify_candidate("candidate", {"exporter": "sha256:" + "a" * 64})
    else:
        with pytest.raises(ValueError, match="Wrong candidate image"):
            keyword.verify_candidate("candidate", {"exporter": "sha256:" + "a" * 64})


def test_host_inventory_reads_actual_node_connection(reader):
    """Independent inventory uses the supplied host connection and validates its exit."""
    keyword, _ = reader
    node = NonCallableMock()
    node.send.side_effect = [json.dumps([{"ifname": "eth0", "flags": ["UP"]}]), "/sys/devices/0000:01:00.0\nvirtfn0 /sys/devices/0000:01:01.0"]
    node.get_return_code.return_value = 0
    assert keyword.interface_inventory(node)["eth0"]["vfs"]["0"] == "0000:01:01.0"
    assert node.send.call_args_list[0].args[0] == "ip -d -j link show"
    node.send.side_effect = None
    node.get_return_code.return_value = 1
    with pytest.raises(AssertionError):
        keyword.interface_inventory(node)


def test_controller_inventory_readiness_wiring(reader):
    """Run real scheduling and readiness parsing through controller JSON reads."""
    keyword, connection = reader
    ds = {"metadata": {"uid": "ds", "generation": 1}, "status": {"observedGeneration": 1, "desiredNumberScheduled": 1, "currentNumberScheduled": 1, "updatedNumberScheduled": 1, "numberReady": 1, "numberAvailable": 1}, "spec": {"selector": {"matchLabels": {"app": "nime-app"}}, "template": {"spec": {"nodeSelector": {"exporter": "true"}}}}}
    nodes = [{"metadata": {"name": "worker-0", "labels": {"exporter": "true"}}}]
    pod = {"metadata": {"name": "nime-1", "namespace": APPLICATION_NAME, "uid": "pod", "labels": {"controller-revision-hash": "revision-1"}, "ownerReferences": [{"uid": "ds", "controller": True}]}, "spec": {"nodeName": "worker-0", "containers": [{"name": "exporter"}]}, "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}], "containerStatuses": [{"name": "exporter", "restartCount": 0, "ready": True, "state": {"running": {}}}]}}

    def send(command, **kwargs):
        """Return the requested controller resource snapshot."""
        if "get daemonsets" in command:
            return [json.dumps({"items": [ds]})]
        if "get nodes" in command:
            return [json.dumps({"items": nodes})]
        if "get pods" in command:
            return [json.dumps({"items": [pod]})]
        raise AssertionError(command)

    connection.send.side_effect = send
    path = "keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords.SystemHostListKeywords"
    with patch(path) as inventory, patch("framework.validation.validation.get_logger"):
        host = NonCallableMock()
        host.get_host_name.return_value = "worker-0"
        inventory.return_value.get_system_host_list.return_value.get_hosts.return_value = [host]
        assert keyword.wait_ready(timeout=0)["worker-0"]["metadata"]["uid"] == "pod"


@pytest.mark.parametrize("enabled", [True, False])
def test_chart_enablement_from_real_cli_table(reader, enabled):
    """Parse the real Helm table through the shared keyword and output object."""
    keyword, connection = reader
    connection.send.return_value = [
        "+--------------------+---------------------------------+\n",
        "| Property           | Value                           |\n",
        "+--------------------+---------------------------------+\n",
        f"| attributes         | enabled: {str(enabled).lower():<22}|\n",
        "| combined_overrides | None                            |\n",
        "| name               | node-interface-metrics-exporter |\n",
        "| namespace          | node-interface-metrics-exporter |\n",
        "| system_overrides   | None                            |\n",
        "| user_overrides     | None                            |\n",
        "+--------------------+---------------------------------+\n",
    ]
    assert keyword.chart_enabled() is enabled


@pytest.mark.parametrize("attributes", ["enabled: 'true'", "enabled: true\nunknown: true", "[enabled]", "enabled: ["])
def test_invalid_chart_attributes_rejected(reader, attributes):
    """Normalizing YAML must retain strict attribute validation."""
    keyword, _ = reader
    path = "keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords.SystemHelmOverrideKeywords"
    with patch(path) as helm:
        helm.return_value.get_system_helm_override_show.return_value.get_helm_override_show.return_value.get_attributes.return_value = attributes
        with pytest.raises((ValueError, yaml.YAMLError)):
            keyword.chart_enabled()
