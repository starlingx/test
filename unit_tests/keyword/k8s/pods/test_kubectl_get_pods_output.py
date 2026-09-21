import json

import pytest
from keywords.k8s.pods.object.kubectl_get_pods_output import KubectlGetPodsOutput


def _json_pod(name, container_restarts=None, init_restarts=None, include_status=True):
    """Build a single kubectl pod JSON item with the given restart counts.

    Args:
        name (str): Pod name.
        container_restarts (list): restartCount values for app (regular) containers.
        init_restarts (list): restartCount values for init containers.
        include_status (bool): When False, omit the status block entirely.

    Returns:
        dict: A kubectl '-o json' pod item.
    """
    item = {
        "metadata": {"name": name, "namespace": "test-ns"},
        "spec": {"nodeName": "controller-0", "containers": [{"image": "img:1"}]},
    }
    if include_status:
        status = {"phase": "Running", "podIP": "127.0.0.1"}
        if container_restarts is not None:
            status["containerStatuses"] = [{"ready": True, "restartCount": r} for r in container_restarts]
        if init_restarts is not None:
            status["initContainerStatuses"] = [{"restartCount": r} for r in init_restarts]
        item["status"] = status
    return item


def _pods_json(items):
    """Wrap pod items into a kubectl '-o json' list document string."""
    return json.dumps({"apiVersion": "v1", "kind": "List", "items": items})


def test_json_output_populates_app_container_restart_count():
    """A JSON-sourced pod sums its app (regular) container restartCount values."""
    output = KubectlGetPodsOutput(_pods_json([_json_pod("pod-a", container_restarts=[2])]), source="json")
    assert output.get_pod("pod-a").get_restart_count() == 2


def test_json_output_multiple_pods_track_counts_independently():
    """Each pod in a multi-item JSON snapshot carries its own counts."""
    output = KubectlGetPodsOutput(
        _pods_json(
            [
                _json_pod("pod-a", container_restarts=[2]),
                _json_pod("pod-b", container_restarts=[0], init_restarts=[4]),
                _json_pod("pod-c", container_restarts=[1, 1]),
            ]
        ),
        source="json",
    )
    assert output.get_pod("pod-a").get_restart_count() == 2
    assert output.get_pod("pod-b").get_restart_count() == 0
    assert output.get_pod("pod-b").get_init_restart_count() == 4
    assert output.get_pod("pod-c").get_restart_count() == 2


def test_json_output_tracks_app_and_init_restarts_separately():
    """App (regular) and init restart counts are stored separately.

    Init containers run once at startup, so their count is startup history,
    not steady-state stability. A pod with 1 app-container and 2+3+0 init restarts
    reports 1 from get_restart_count() and 5 from get_init_restart_count().
    """
    output = KubectlGetPodsOutput(_pods_json([_json_pod("rest-service", container_restarts=[1], init_restarts=[2, 3, 0])]), source="json")
    pod = output.get_pod("rest-service")
    assert pod.get_restart_count() == 1
    assert pod.get_init_restart_count() == 5


def test_json_output_missing_status_blocks_yields_zero():
    """A pod with no containerStatuses/initContainerStatuses reports 0, not an error."""
    output = KubectlGetPodsOutput(_pods_json([_json_pod("pod-fresh")]), source="json")
    pod = output.get_pod("pod-fresh")
    assert pod.get_restart_count() == 0
    assert pod.get_init_restart_count() == 0


def test_json_output_no_status_block_yields_zero():
    """A pod item with no status block at all reports 0 restarts."""
    output = KubectlGetPodsOutput(_pods_json([_json_pod("pod-nostatus", include_status=False)]), source="json")
    pod = output.get_pod("pod-nostatus")
    assert pod.get_restart_count() == 0
    assert pod.get_init_restart_count() == 0


def test_json_output_container_status_missing_restart_count_fails_loud():
    """A present container status missing the required restartCount key fails loud.

    restartCount is a required field on a k8s container status. An empty
    containerStatuses list is the legitimate not-started case (sums to 0), but a
    status that is present yet missing restartCount is malformed input - it must
    raise rather than silently count 0 and undercount restarts.
    """
    malformed = {
        "metadata": {"name": "pod-malformed", "namespace": "test-ns"},
        "spec": {"containers": [{"image": "img:1"}]},
        "status": {"phase": "Running", "containerStatuses": [{"ready": True}]},
    }
    with pytest.raises(KeyError):
        KubectlGetPodsOutput(_pods_json([malformed]), source="json")


def test_table_source_restart_count_accessors_raise():
    """Table-sourced pods raise on restart-count access (not silent None).

    Restart counts are only meaningful from JSON. Accessing them on a
    table-sourced pod is a keyword-bypass mistake and must fail loud, pointing
    at the JSON source, rather than returning None and poisoning comparisons.
    """
    table = (
        "NAME                READY   STATUS    RESTARTS       AGE\n",
        "pod-a               1/1     Running   0              18d\n",
    )
    output = KubectlGetPodsOutput(table, source="table")
    pod = output.get_pod("pod-a")

    with pytest.raises(ValueError, match="not available"):
        pod.get_restart_count()
    with pytest.raises(ValueError, match="not available"):
        pod.get_init_restart_count()

    # The raw table RESTARTS string remains available for table-source callers.
    assert pod.get_restarts() == "0"


def test_get_total_restart_count_app_only_by_default():
    """get_total_restart_count() returns app-container restarts only by default.

    Init restarts are startup history, not steady-state stability, so they are
    excluded unless explicitly requested.
    """
    output = KubectlGetPodsOutput(_pods_json([_json_pod("rest-service", container_restarts=[1], init_restarts=[2, 3, 0])]), source="json")
    assert output.get_pod("rest-service").get_total_restart_count() == 1


def test_get_total_restart_count_include_init_adds_init():
    """include_init=True adds init-container restarts (1 app + 5 init = 6)."""
    output = KubectlGetPodsOutput(_pods_json([_json_pod("rest-service", container_restarts=[1], init_restarts=[2, 3, 0])]), source="json")
    assert output.get_pod("rest-service").get_total_restart_count(include_init=True) == 6


def test_get_total_restart_count_table_source_raises():
    """A table-sourced pod raises: the combine delegates to the getters, which fail loud.

    get_total_restart_count() has no counts of its own; it calls get_restart_count()
    (and, with include_init, get_init_restart_count()), so a table-sourced pod raises
    ValueError rather than returning a misleading number.
    """
    table = (
        "NAME                READY   STATUS    RESTARTS       AGE\n",
        "pod-a               1/1     Running   0              18d\n",
    )
    pod = KubectlGetPodsOutput(table, source="table").get_pod("pod-a")

    with pytest.raises(ValueError, match="not available"):
        pod.get_total_restart_count()
    with pytest.raises(ValueError, match="not available"):
        pod.get_total_restart_count(include_init=True)
