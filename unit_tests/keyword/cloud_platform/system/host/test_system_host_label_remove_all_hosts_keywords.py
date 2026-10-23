"""Unit tests for SystemHostLabelKeywords.remove_labels_from_all_hosts.

The keyword is used in cleanup, so it must be idempotent: on each host it removes only the
requested keys that are present and skips hosts that have none of them. These tests mock the
host list, the per-host label list and the remove call, so no live system is required.
"""

from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords

HOST_LIST_PATH = "keywords.cloud_platform.system.host.system_host_label_keywords.SystemHostListKeywords"


def _label_list(present_keys: list) -> NonCallableMagicMock:
    """Build a label list output that reports only the given keys as present.

    Args:
        present_keys (list): Label keys present on the host.

    Returns:
        NonCallableMagicMock: Mocked SystemHostLabelListOutput.
    """
    label_list = NonCallableMagicMock()
    label_list.is_label_present = MagicMock(side_effect=lambda key: key in present_keys)
    return label_list


def _build_keywords(labels_by_host: dict) -> SystemHostLabelKeywords:
    """Return an instance whose label list and remove calls are mocked.

    A non-callable mock is used for attributes because BaseKeyword.__getattribute__ wraps
    callable attributes with its keyword-logging hook.

    Args:
        labels_by_host (dict): Host name -> list of label keys present on that host.

    Returns:
        SystemHostLabelKeywords: The instance under test.
    """
    keywords = SystemHostLabelKeywords.__new__(SystemHostLabelKeywords)
    object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
    object.__setattr__(keywords, "get_system_host_label_list", MagicMock(side_effect=lambda host: _label_list(labels_by_host[host])))
    object.__setattr__(keywords, "system_host_label_remove", MagicMock())
    return keywords


@patch("keywords.cloud_platform.system.host.system_host_label_keywords.get_logger")
@patch("keywords.base_keyword.get_logger")
@patch(HOST_LIST_PATH)
def test_removes_only_present_keys_on_each_host(mock_host_list, mock_base_logger, mock_logger):
    """Each host gets one remove call with only the keys it actually has."""
    labels_by_host = {"controller-0": ["power-management", "other"], "worker-0": ["power-management"]}
    mock_host_list.return_value.get_system_host_list.return_value.get_host_names.return_value = list(labels_by_host)
    keywords = _build_keywords(labels_by_host)

    keywords.remove_labels_from_all_hosts(["power-management", "kube-cpu-mgr-policy"])

    keywords.system_host_label_remove.assert_any_call("controller-0", "power-management")
    keywords.system_host_label_remove.assert_any_call("worker-0", "power-management")
    assert keywords.system_host_label_remove.call_count == 2


@patch("keywords.cloud_platform.system.host.system_host_label_keywords.get_logger")
@patch("keywords.base_keyword.get_logger")
@patch(HOST_LIST_PATH)
def test_removes_multiple_present_keys_in_a_single_call(mock_host_list, mock_base_logger, mock_logger):
    """Several present keys on a host are removed with one space-separated call."""
    labels_by_host = {"controller-0": ["key1", "key2"]}
    mock_host_list.return_value.get_system_host_list.return_value.get_host_names.return_value = list(labels_by_host)
    keywords = _build_keywords(labels_by_host)

    keywords.remove_labels_from_all_hosts(["key1", "key2"])

    keywords.system_host_label_remove.assert_called_once_with("controller-0", "key1 key2")


@patch("keywords.cloud_platform.system.host.system_host_label_keywords.get_logger")
@patch("keywords.base_keyword.get_logger")
@patch(HOST_LIST_PATH)
def test_skips_hosts_without_the_labels(mock_host_list, mock_base_logger, mock_logger):
    """No remove call is made when no host has any of the keys (idempotent cleanup)."""
    labels_by_host = {"controller-0": [], "controller-1": ["unrelated"]}
    mock_host_list.return_value.get_system_host_list.return_value.get_host_names.return_value = list(labels_by_host)
    keywords = _build_keywords(labels_by_host)

    keywords.remove_labels_from_all_hosts(["power-management"])

    keywords.system_host_label_remove.assert_not_called()


@patch("keywords.cloud_platform.system.host.system_host_label_keywords.get_logger")
@patch("keywords.base_keyword.get_logger")
@patch(HOST_LIST_PATH)
def test_queries_label_list_once_per_host(mock_host_list, mock_base_logger, mock_logger):
    """The label list CLI runs once per host, whatever the number of keys."""
    labels_by_host = {"controller-0": ["a"], "controller-1": ["b"]}
    mock_host_list.return_value.get_system_host_list.return_value.get_host_names.return_value = list(labels_by_host)
    keywords = _build_keywords(labels_by_host)

    keywords.remove_labels_from_all_hosts(["a", "b", "c"])

    assert keywords.get_system_host_label_list.call_count == 2
