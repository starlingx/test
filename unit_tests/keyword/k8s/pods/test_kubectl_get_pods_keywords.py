"""Unit tests for KubectlGetPodsKeywords.get_pod_restart_count.

Verifies the restart-count keyword without a live cluster: it fetches pods as
JSON via get_pods_json(), then reads the target pod's restart count from the
parsed object - app (regular) container restarts by default, plus init-container
restarts when include_init is True. A non-callable mocked SSH connection is
used because BaseKeyword.__getattribute__ wraps callable attributes with its
keyword-logging hook.

The base keyword logs every keyword call, so each test patches the logger to
avoid requiring a configured logger.
"""

import json
from unittest.mock import NonCallableMagicMock, patch

import pytest
from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection

from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


def _pods_list_json(items: list) -> str:
    """Wrap pod items into a kubectl 'get pods -o json' List document string."""
    return json.dumps({"apiVersion": "v1", "kind": "List", "items": items})


def _pod_item(name: str, container_restarts: list, init_restarts: list = None) -> dict:
    """Build a single kubectl pod JSON item with the given restart counts."""
    status = {"phase": "Running", "containerStatuses": [{"ready": True, "restartCount": r} for r in container_restarts]}
    if init_restarts is not None:
        status["initContainerStatuses"] = [{"restartCount": r} for r in init_restarts]
    return {"metadata": {"name": name, "namespace": "test-ns"}, "spec": {"containers": [{"image": "img:1"}]}, "status": status}


REST_SERVICE_LIST = _pods_list_json([_pod_item("rest-service", container_restarts=[1], init_restarts=[2, 3, 0])])


def build_mock_ssh_connection(return_value: str) -> NonCallableMagicMock:
    """Build a non-callable mocked SSH connection.

    A non-callable mock is required because BaseKeyword.__getattribute__ wraps
    callable attributes with its keyword-logging hook.

    Args:
        return_value (str): The value the mocked send() should return.

    Returns:
        NonCallableMagicMock: The mocked SSH connection reporting success.
    """
    ssh_connection = NonCallableMagicMock(spec=SSHConnection)
    ssh_connection.send.return_value = return_value
    ssh_connection.get_return_code.return_value = 0
    return ssh_connection


@patch("keywords.base_keyword.get_logger")
def test_get_pod_restart_count_issues_o_json_command(mock_get_logger):
    """The keyword fetches pods via 'kubectl get pods -n <ns> -o json'."""
    ssh_connection = build_mock_ssh_connection(REST_SERVICE_LIST)
    keyword = KubectlGetPodsKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    keyword.get_pod_restart_count("rest-service", "test-ns")

    sent_command = ssh_connection.send.call_args[0][0]
    assert "get pods" in sent_command
    assert "-n test-ns" in sent_command
    assert "-o json" in sent_command


@patch("keywords.base_keyword.get_logger")
def test_get_pod_restart_count_app_containers_only_by_default(mock_get_logger):
    """Counts app (regular) containers only by default (init restarts are startup history)."""
    ssh_connection = build_mock_ssh_connection(REST_SERVICE_LIST)
    keyword = KubectlGetPodsKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    assert keyword.get_pod_restart_count("rest-service", "test-ns") == 1


@patch("keywords.base_keyword.get_logger")
def test_get_pod_restart_count_include_init_adds_init_restarts(mock_get_logger):
    """With include_init=True the keyword adds init-container restarts (1 + 5 = 6)."""
    ssh_connection = build_mock_ssh_connection(REST_SERVICE_LIST)
    keyword = KubectlGetPodsKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    assert keyword.get_pod_restart_count("rest-service", "test-ns", include_init=True) == 6


@patch("keywords.base_keyword.get_logger")
def test_get_pod_restart_count_running_pod_with_no_restarts_is_zero(mock_get_logger):
    """A running pod whose containers report restartCount 0 yields 0 (the genuine-zero case)."""
    list_json = _pods_list_json([_pod_item("steady-pod", container_restarts=[0, 0])])
    ssh_connection = build_mock_ssh_connection(list_json)
    keyword = KubectlGetPodsKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    assert keyword.get_pod_restart_count("steady-pod", "test-ns") == 0


@patch("keywords.base_keyword.get_logger")
def test_get_pod_restart_count_no_container_statuses_sums_to_zero(mock_get_logger):
    """A pod whose containers have not started (e.g. Pending) has no containerStatuses, sums to 0.

    This 0 is a "no data" value, not a health assertion - it means "nothing has started yet",
    not "stable". It is distinct from a crash-looping pod, which HAS started and whose restarts
    are counted (see the crashloop test). Callers baselining a stability signal must ensure the
    containers have come up first (see get_pod_restart_count docstring).
    """
    list_json = _pods_list_json([_pod_item("pending-pod", container_restarts=[])])
    ssh_connection = build_mock_ssh_connection(list_json)
    keyword = KubectlGetPodsKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    assert keyword.get_pod_restart_count("pending-pod", "test-ns") == 0


@patch("keywords.base_keyword.get_logger")
def test_get_pod_restart_count_crashloop_pod_reports_its_restarts(mock_get_logger):
    """A crash-looping pod has started and its high restart count is reported correctly.

    A CrashLoopBackOff pod's phase is Running and its container has a real restart history;
    this is exactly the instability signal a stability check wants, so it must be counted,
    not treated as "unhealthy, skip".
    """
    list_json = _pods_list_json([_pod_item("crashloop-pod", container_restarts=[17])])
    ssh_connection = build_mock_ssh_connection(list_json)
    keyword = KubectlGetPodsKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    assert keyword.get_pod_restart_count("crashloop-pod", "test-ns") == 17


@patch("keywords.base_keyword.get_logger")
def test_get_pod_restart_count_selects_the_named_pod(mock_get_logger):
    """The keyword returns the count for the requested pod, not another one."""
    list_json = _pods_list_json(
        [
            _pod_item("other-pod", container_restarts=[9]),
            _pod_item("rest-service", container_restarts=[1]),
        ]
    )
    ssh_connection = build_mock_ssh_connection(list_json)
    keyword = KubectlGetPodsKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    assert keyword.get_pod_restart_count("rest-service", "test-ns") == 1


@patch("keywords.base_keyword.get_logger")
def test_get_pod_restart_count_pod_not_found_raises(mock_get_logger):
    """A pod absent from the snapshot raises KeywordException (via get_pod)."""
    list_json = _pods_list_json([_pod_item("other-pod", container_restarts=[0])])
    ssh_connection = build_mock_ssh_connection(list_json)
    keyword = KubectlGetPodsKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    with pytest.raises(KeywordException, match="no pod with the name"):
        keyword.get_pod_restart_count("missing-pod", "test-ns")
