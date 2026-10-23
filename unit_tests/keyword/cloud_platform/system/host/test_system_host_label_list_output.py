"""Unit tests for SystemHostLabelListOutput.is_label_present and is_label_value_set.

Both helpers answer questions about a single parsed 'system host-label-list' output, so the
CLI runs once and several questions can be asked of the same output. These tests build the
output from a sample table, so no live system is required.
"""

from keywords.cloud_platform.system.host.objects.system_host_label_list_output import SystemHostLabelListOutput

HOST_LABEL_LIST_TABLE = [
    "+--------------+---------------------+-------------+\n",
    "| hostname     | label key           | label value |\n",
    "+--------------+---------------------+-------------+\n",
    "| controller-0 | power-management    | enabled     |\n",
    "| controller-0 | kube-cpu-mgr-policy | static      |\n",
    "+--------------+---------------------+-------------+\n",
]

EMPTY_HOST_LABEL_LIST_TABLE = [
    "+----------+-----------+-------------+\n",
    "| hostname | label key | label value |\n",
    "+----------+-----------+-------------+\n",
    "+----------+-----------+-------------+\n",
]


def test_is_label_present_returns_true_for_existing_key():
    """A key listed in the output reads as present."""
    output = SystemHostLabelListOutput(HOST_LABEL_LIST_TABLE)
    assert output.is_label_present("power-management") is True


def test_is_label_present_returns_false_for_missing_key():
    """A key that is not listed reads as absent."""
    output = SystemHostLabelListOutput(HOST_LABEL_LIST_TABLE)
    assert output.is_label_present("kube-topology-mgr-policy") is False


def test_is_label_present_returns_false_when_host_has_no_labels():
    """An empty label list reads as absent for any key."""
    output = SystemHostLabelListOutput(EMPTY_HOST_LABEL_LIST_TABLE)
    assert output.is_label_present("power-management") is False


def test_is_label_value_set_returns_true_for_matching_value():
    """A present key with the expected value reads as set."""
    output = SystemHostLabelListOutput(HOST_LABEL_LIST_TABLE)
    assert output.is_label_value_set("kube-cpu-mgr-policy", "static") is True


def test_is_label_value_set_returns_false_for_different_value():
    """A present key with another value reads as not set."""
    output = SystemHostLabelListOutput(HOST_LABEL_LIST_TABLE)
    assert output.is_label_value_set("kube-cpu-mgr-policy", "none") is False


def test_is_label_value_set_returns_false_for_missing_key():
    """A missing key reads as not set, whatever the expected value."""
    output = SystemHostLabelListOutput(HOST_LABEL_LIST_TABLE)
    assert output.is_label_value_set("kube-topology-mgr-policy", "restricted") is False
