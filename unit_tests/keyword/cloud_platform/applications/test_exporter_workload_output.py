"""Scheduling and complete readiness checks without a live Kubernetes cluster."""

from copy import deepcopy

import pytest

from keywords.cloud_platform.applications.object.exporter_workload_output import ExporterWorkloadOutput


@pytest.fixture
def workload():
    """Provide one eligible worker and one node excluded by the rendered selector."""
    ds = {"metadata": {"uid": "ds", "generation": 1}, "status": {"observedGeneration": 1, "desiredNumberScheduled": 1, "currentNumberScheduled": 1, "updatedNumberScheduled": 1, "numberReady": 1, "numberAvailable": 1}, "spec": {"template": {"spec": {"nodeSelector": {"exporter": "true"}}}}}
    nodes = [{"metadata": {"name": "worker-0", "labels": {"exporter": "true"}}}, {"metadata": {"name": "controller-0"}}]
    return ExporterWorkloadOutput(ds, nodes)


@pytest.fixture
def pod():
    """Provide one ready pod owned by the expected DaemonSet."""
    return {"metadata": {"uid": "pod", "labels": {"controller-revision-hash": "revision-1"}, "ownerReferences": [{"uid": "ds", "controller": True}]}, "spec": {"nodeName": "worker-0", "containers": [{"name": "exporter"}]}, "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}], "containerStatuses": [{"name": "exporter", "ready": True, "state": {"running": {}}}]}}


def test_exact_coverage(workload, pod):
    """Ready pods do not define expected coverage; scheduling does."""
    assert workload.eligible_nodes() == ("worker-0",)
    assert workload.ready_pods([pod]) == {"worker-0": pod}
    assert workload.ready_pods([]) == {}
    assert workload.ready_pods([pod, deepcopy(pod)]) == {}


@pytest.mark.parametrize("change", ["terminating", "missing_status", "not_ready", "wrong_owner", "wrong_node"])
def test_unready_pods(workload, pod, change):
    """Reject stale or incomplete readiness evidence."""
    if change == "terminating":
        pod["metadata"]["deletionTimestamp"] = "now"
    elif change == "missing_status":
        pod["status"]["containerStatuses"] = []
    elif change == "not_ready":
        pod["status"]["containerStatuses"][0]["ready"] = False
    elif change == "wrong_node":
        pod["spec"]["nodeName"] = "controller-0"
    else:
        pod["metadata"]["ownerReferences"] = []
        with pytest.raises(ValueError):
            workload.ready_pods([pod])
        return
    assert workload.ready_pods([pod]) == {}


def test_no_eligible_nodes_and_unsupported_affinity(workload):
    """Unsupported/empty coverage fails explicitly instead of passing vacuously."""
    workload.daemonset["spec"]["template"]["spec"]["affinity"] = {"nodeAffinity": {"required": "unknown"}}
    with pytest.raises(ValueError):
        workload.eligible_nodes()
    workload.daemonset["spec"]["template"]["spec"] = {"nodeSelector": {"missing": "true"}}
    with pytest.raises(ValueError):
        workload.eligible_nodes()


def test_taint_toleration(workload):
    """Explicit NoSchedule taints require matching rendered tolerations."""
    workload.nodes[0]["spec"] = {"taints": [{"key": "dedicated", "value": "metrics", "effect": "NoSchedule"}]}
    with pytest.raises(ValueError):
        workload.eligible_nodes()
    workload.daemonset["spec"]["template"]["spec"]["tolerations"] = [{"key": "dedicated", "value": "metrics", "effect": "NoSchedule"}]
    assert workload.eligible_nodes() == ("worker-0",)


@pytest.mark.parametrize("change", ["image", "configuration"])
def test_previous_template_is_not_ready(workload, pod, change):
    """Ready old pods must not satisfy a new image or configuration rollout."""
    workload.daemonset["metadata"]["generation"] = 2
    workload.daemonset["spec"]["template"]["spec"]["containers"] = [{"name": "exporter", "image": "exporter:new" if change == "image" else "exporter:unchanged", "env": [{"name": "SETTING", "value": "new"}]}]
    workload.daemonset["status"]["updatedNumberScheduled"] = 0
    assert workload.ready_pods([pod]) == {}
    workload.daemonset["status"]["observedGeneration"] = 2
    assert workload.ready_pods([pod]) == {}
    workload.daemonset["status"]["updatedNumberScheduled"] = 1
    pod["metadata"]["labels"]["controller-revision-hash"] = "revision-2"
    assert workload.ready_pods([pod]) == {"worker-0": pod}


@pytest.mark.parametrize("field", ["desiredNumberScheduled", "currentNumberScheduled", "updatedNumberScheduled", "numberReady", "numberAvailable", "observedGeneration"])
def test_incomplete_controller_status_keeps_waiting(workload, pod, field):
    """Missing controller evidence must not count as a completed rollout."""
    workload.daemonset["status"].pop(field)
    assert workload.ready_pods([pod]) == {}


def test_mixed_pod_revisions_keep_waiting(workload, pod):
    """A mixed pod snapshot cannot establish readiness for the current template."""
    workload.nodes.append({"metadata": {"name": "worker-1", "labels": {"exporter": "true"}}})
    for field in ("desiredNumberScheduled", "currentNumberScheduled", "updatedNumberScheduled", "numberReady", "numberAvailable"):
        workload.daemonset["status"][field] = 2
    second_pod = deepcopy(pod)
    second_pod["metadata"].update(uid="pod-2", labels={"controller-revision-hash": "revision-2"})
    second_pod["spec"]["nodeName"] = "worker-1"
    assert workload.ready_pods([pod, second_pod]) == {}
    pod["metadata"]["labels"]["controller-revision-hash"] = "revision-2"
    assert set(workload.ready_pods([pod, second_pod])) == {"worker-0", "worker-1"}


def test_missing_pod_revision_keeps_waiting(workload, pod):
    """Ready and owned pods still require rollout identity."""
    pod["metadata"].pop("labels")
    assert workload.ready_pods([pod]) == {}
