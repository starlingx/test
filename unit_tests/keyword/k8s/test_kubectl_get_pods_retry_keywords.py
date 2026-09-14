"""Unit tests for the retrying pod read on KubectlGetPodsKeywords.

get_unhealthy_pods issues a single kubectl query whose return code the framework asserts with no
retry. Immediately after 'software deploy activate' the platform re-applies its own applications,
and that query has been observed to fail transiently in the churn and then succeed unchanged
moments later. get_pods_with_retry wraps a read so a caller can tell "the cluster was busy" from
"this application is unhealthy". These tests drive that retry with a mocked reader so no live
cluster is required.

The base keyword logs every keyword call, so each test patches the logger.
"""
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

MODULE = "keywords.k8s.pods.kubectl_get_pods_keywords"


def _build_keywords() -> KubectlGetPodsKeywords:
    """Return a KubectlGetPodsKeywords with a mocked SSH connection.

    Returns:
        KubectlGetPodsKeywords: the instance under test.
    """
    ssh_connection = NonCallableMagicMock(spec=SSHConnection)
    ssh_connection.get_return_code.return_value = 0
    return KubectlGetPodsKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")


@patch("keywords.base_keyword.get_logger")
def test_a_successful_read_is_returned_without_retrying(mock_get_logger):
    """A read that succeeds first time is returned as-is and the reader is called once."""
    keywords = _build_keywords()
    good_output = NonCallableMagicMock()
    reader = MagicMock(return_value=good_output)

    result = keywords.get_pods_with_retry(reader)

    assert result is good_output
    assert reader.call_count == 1


@patch(f"{MODULE}.get_logger")
@patch("keywords.base_keyword.get_logger")
def test_a_transient_failure_is_retried_then_succeeds(mock_base_logger, mock_module_logger):
    """A read that fails once and then succeeds is retried, and the good result returned."""
    keywords = _build_keywords()
    good_output = NonCallableMagicMock()
    reader = MagicMock(side_effect=[AssertionError("Return code was 1"), good_output])

    with patch(f"{MODULE}.time.sleep"):
        result = keywords.get_pods_with_retry(reader, timeout=60, poll_interval=10)

    assert result is good_output
    assert reader.call_count == 2


@patch(f"{MODULE}.get_logger")
@patch("keywords.base_keyword.get_logger")
def test_a_read_that_never_succeeds_raises(mock_base_logger, mock_module_logger):
    """A reader that fails for the whole window raises KeywordException, not the raw error."""
    keywords = _build_keywords()
    reader = MagicMock(side_effect=AssertionError("Return code was 1"))

    with patch(f"{MODULE}.time.sleep"):
        with patch(f"{MODULE}.time.time", side_effect=[0, 1, 2, 999]):
            try:
                keywords.get_pods_with_retry(reader, timeout=60, poll_interval=10)
                assert False, "Expected KeywordException"
            except KeywordException as raised:
                assert "Could not read the pod list" in str(raised)
