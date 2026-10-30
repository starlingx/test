"""Exercise shared DaemonSet waits through real resource and pod parsing."""

import json
from copy import deepcopy
from unittest.mock import NonCallableMock, patch

import pytest

from keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords import NodeInterfaceMetricsExporterKeywords
from keywords.k8s.daemonsets.kubectl_get_daemonsets_keywords import KubectlGetDaemonsetsKeywords
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords


@pytest.fixture
def daemonset_reader():
    """Provide a complete workload and checked SSH resource responses."""
    daemonset = {"metadata": {"uid": "ds", "generation": 2}, "status": {"observedGeneration": 2, "desiredNumberScheduled": 1, "currentNumberScheduled": 1, "updatedNumberScheduled": 1, "numberReady": 1, "numberAvailable": 1}, "spec": {"selector": {"matchLabels": {"app": "test"}}, "template": {"spec": {"nodeSelector": {"workload": "true"}}}}}
    nodes = [{"metadata": {"name": "worker-0", "labels": {"workload": "true"}}}]
    pod = {"metadata": {"name": "test-1", "namespace": "test", "uid": "pod", "labels": {"controller-revision-hash": "revision-2"}, "ownerReferences": [{"uid": "ds", "controller": True}]}, "spec": {"nodeName": "worker-0", "containers": [{"name": "test"}]}, "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}], "containerStatuses": [{"name": "test", "restartCount": 0, "ready": True, "state": {"running": {}}}]}}
    connection = NonCallableMock()
    connection.get_return_code.return_value = 0

    def send(command, **kwargs):
        """Return raw JSON using the real SSH line-list contract."""
        if "get daemonsets" in command:
            result = daemonset if "get daemonsets test-ds " in command else {"items": [daemonset]}
        elif "get nodes" in command:
            result = {"items": nodes}
        elif "get pods" in command:
            result = {"items": [pod]}
        else:
            raise AssertionError(command)
        return [json.dumps(result)]

    connection.send.side_effect = send
    with patch("keywords.base_keyword.get_logger"), patch("framework.validation.validation.get_logger"):
        yield KubectlWaitPodKeywords(connection, "/custom/config"), connection, daemonset, nodes, pod


@pytest.mark.parametrize("daemonset_name", [None, "test-ds"])
def test_wait_reads_named_or_unique_daemonset(daemonset_reader, daemonset_name):
    """Default collection and named-object responses preserve full readiness checks."""
    keyword, connection, _, _, pod = daemonset_reader
    assert keyword.wait_for_daemonset_ready("test", daemonset_name, timeout=0) == {"worker-0": pod}
    commands = [call.args[0] for call in connection.send.call_args_list]
    assert all("/custom/config" in command for command in commands)
    assert "-n test" in commands[0]
    assert "app=test" in commands[-1]


@pytest.mark.parametrize("transition", ["unobserved_generation", "old_template", "missing_node", "unready_container"])
def test_wait_refreshes_workload_until_current_rollout(daemonset_reader, transition):
    """Poll stale and incomplete evidence again instead of returning a false pass."""
    keyword, _, daemonset, nodes, pod = daemonset_reader
    read_snapshot = KubectlGetDaemonsetsKeywords(keyword.ssh_connection, "/custom/config").get_daemonset_workload
    pending = deepcopy(daemonset)
    if transition == "unobserved_generation":
        pending["status"]["observedGeneration"] = 1
    elif transition == "old_template":
        pending["status"]["updatedNumberScheduled"] = 0
    elif transition == "missing_node":
        nodes.append({"metadata": {"name": "worker-1", "labels": {"workload": "true"}}})
        for field in ("desiredNumberScheduled", "currentNumberScheduled", "updatedNumberScheduled", "numberReady", "numberAvailable"):
            pending["status"][field] = 2
    else:
        pod["status"]["containerStatuses"][0]["ready"] = False

    snapshots = []

    def read_workload(*args):
        """Provide a pending snapshot followed by freshly collected ready evidence."""
        snapshot = read_snapshot("test")
        snapshots.append(snapshot)
        if len(snapshots) == 1:
            snapshot.daemonset = pending
        else:
            nodes[:] = nodes[:1]
            pod["status"]["containerStatuses"][0]["ready"] = True
            snapshot = read_snapshot("test")
        return snapshot

    with patch("framework.validation.validation.sleep"), patch("keywords.k8s.pods.kubectl_wait_pod_keywords.KubectlGetDaemonsetsKeywords") as reader:
        reader.return_value.get_daemonset_workload.side_effect = read_workload
        assert keyword.wait_for_daemonset_ready("test", timeout=5) == {"worker-0": pod}
    assert len(snapshots) == 2


def test_incomplete_rollout_times_out(daemonset_reader):
    """Do not replace bounded convergence with a successful pod-only wait."""
    keyword, _, daemonset, _, _ = daemonset_reader
    daemonset["status"]["updatedNumberScheduled"] = 0
    with pytest.raises(TimeoutError):
        keyword.wait_for_daemonset_ready("test", timeout=0)


def test_resource_failure_is_not_retried_as_pending(daemonset_reader):
    """Preserve command failures instead of interpreting them as empty pods."""
    keyword, connection, _, _, _ = daemonset_reader
    connection.get_return_code.return_value = 1
    with pytest.raises(AssertionError):
        keyword.wait_for_daemonset_ready("test", timeout=0)


def test_exporter_delegates_with_fresh_inventory_validation(daemonset_reader):
    """Keep exporter platform checks on every shared readiness observation."""
    _, connection, _, _, _ = daemonset_reader
    exporter = NodeInterfaceMetricsExporterKeywords(connection, "/custom/config")
    path = "keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords"
    with patch(path + ".KubectlWaitPodKeywords") as wait, patch.object(exporter, "workload") as read_workload, patch(path + ".SystemHostListKeywords") as hosts:
        hosts.return_value.get_system_host_list.return_value.get_hosts.return_value = [NonCallableMock(get_host_name=lambda: "worker-0")]
        pods = {"worker-0": {"metadata": {"uid": "current"}}}
        wait.return_value.wait_for_daemonset_ready.return_value = pods
        assert exporter.wait_ready(timeout=17) == pods
        wait.assert_called_once_with(connection, "/custom/config")
        wait.return_value.wait_for_daemonset_ready.assert_called_once()
        call = wait.return_value.wait_for_daemonset_ready.call_args
        assert call.args == ("node-interface-metrics-exporter",)
        assert call.kwargs["timeout"] == 17
        read_workload.assert_called_once_with()


def test_exporter_rejects_nodes_outside_platform_inventory(daemonset_reader):
    """The shared wait must still enforce the exporter's independent host inventory."""
    _, connection, _, _, _ = daemonset_reader
    exporter = NodeInterfaceMetricsExporterKeywords(connection, "/custom/config")
    path = "keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords.SystemHostListKeywords"
    with patch(path) as hosts:
        hosts.return_value.get_system_host_list.return_value.get_hosts.return_value = []
        with pytest.raises(ValueError, match="platform host inventory"):
            exporter.wait_ready(timeout=0)


@pytest.mark.parametrize("all_pods", [True, False])
def test_existing_pod_waits_keep_their_commands(daemonset_reader, all_pods):
    """The new DaemonSet operation must not change existing pod-only behavior."""
    keyword, connection, _, _, _ = daemonset_reader
    connection.send.side_effect = None
    with patch("keywords.k8s.pods.kubectl_wait_pod_keywords.get_logger"):
        if all_pods:
            keyword.wait_for_all_pods_ready("test", timeout=19)
            expected = "kubectl wait --for=condition=Ready pod --all -n test --timeout=19s"
        else:
            keyword.wait_for_pods_ready("app=test", "test", timeout=19)
            expected = "kubectl wait --for=condition=Ready pod -l app=test -n test --timeout=19s"
    assert expected in connection.send.call_args.args[0]


@pytest.mark.parametrize("daemonsets", [[], [{}, {}]])
def test_ambiguous_or_missing_daemonset_rejected(daemonset_reader, daemonsets):
    """Require an explicit single workload rather than accepting empty coverage."""
    keyword, connection, _, _, _ = daemonset_reader
    connection.send.side_effect = None
    connection.send.return_value = [json.dumps({"items": daemonsets})]
    with pytest.raises(ValueError, match="exactly one DaemonSet"):
        keyword.wait_for_daemonset_ready("test", timeout=0)
