"""Unit tests for KubectlGetResourceKeywords.is_namespace_empty.

The keyword runs 'kubectl get all -n <namespace>' and reads the namespace as empty only when
kubectl reports 'No resources found'. These tests mock the SSH connection, so no live cluster
is required. A non-callable mocked SSH connection is used because BaseKeyword.__getattribute__
wraps callable attributes with its keyword-logging hook.
"""

from unittest.mock import NonCallableMagicMock, patch

import pytest

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords

NAMESPACE = "intel-power"

EMPTY_OUTPUT = [f"No resources found in {NAMESPACE} namespace.\n"]

POPULATED_OUTPUT = [
    "NAME                                     READY   STATUS    RESTARTS   AGE\n",
    "pod/controller-manager-5d9c8f7b6c-abcde   1/1     Running   0          5m\n",
]


def build_mock_ssh_connection(return_value: list, return_code: int = 0) -> NonCallableMagicMock:
    """Build a non-callable mocked SSH connection.

    Args:
        return_value (list): The value the mocked send() should return.
        return_code (int): The return code reported for the last command.

    Returns:
        NonCallableMagicMock: The mocked SSH connection.
    """
    ssh_connection = NonCallableMagicMock(spec=SSHConnection)
    ssh_connection.send.return_value = return_value
    ssh_connection.get_return_code.return_value = return_code
    return ssh_connection


@patch("keywords.base_keyword.get_logger")
def test_is_namespace_empty_runs_kubectl_get_all_in_namespace(mock_get_logger):
    """The keyword queries 'kubectl get all' scoped to the given namespace."""
    ssh_connection = build_mock_ssh_connection(EMPTY_OUTPUT)
    keyword = KubectlGetResourceKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    keyword.is_namespace_empty(NAMESPACE)

    sent_command = ssh_connection.send.call_args[0][0]
    assert "kubectl get all" in sent_command
    assert f"-n {NAMESPACE}" in sent_command


@patch("keywords.base_keyword.get_logger")
def test_is_namespace_empty_returns_true_when_no_resources(mock_get_logger):
    """'No resources found' reads as an empty namespace."""
    ssh_connection = build_mock_ssh_connection(EMPTY_OUTPUT)
    keyword = KubectlGetResourceKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    assert keyword.is_namespace_empty(NAMESPACE) is True


@patch("keywords.base_keyword.get_logger")
def test_is_namespace_empty_returns_false_when_resources_exist(mock_get_logger):
    """Any listed resource reads as a non-empty namespace."""
    ssh_connection = build_mock_ssh_connection(POPULATED_OUTPUT)
    keyword = KubectlGetResourceKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    assert keyword.is_namespace_empty(NAMESPACE) is False


@patch("keywords.base_keyword.get_logger")
def test_is_namespace_empty_raises_when_kubectl_fails(mock_get_logger):
    """A failing kubectl command raises instead of reading as empty."""
    ssh_connection = build_mock_ssh_connection(["error: the server doesn't have a resource type\n"], return_code=1)
    keyword = KubectlGetResourceKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    with pytest.raises(Exception):
        keyword.is_namespace_empty(NAMESPACE)
