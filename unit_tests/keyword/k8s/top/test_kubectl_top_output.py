"""Unit tests for the kubectl top Output/Object/table parser.

Covers both `kubectl top nodes` and `kubectl top pods` table shapes, using the real
output shapes captured from a live AIO-SX (CPU as millicores like "445m" or whole cores,
memory as "8996Mi", and the "<unknown>" cell kubectl prints when metrics-server is not
serving). The tables carry their header line, as kubectl prints them without --no-headers,
so the base table parser can key columns by header position. The has_positive_* readers are
the ones a serving-probe actually needs, so they are asserted directly.
"""

import pytest

from keywords.k8s.top.objects.kubectl_top_output import KubectlTopOutput

_NODES_HEADER = "NAME           CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)\n"
_PODS_HEADER = "NAME                       CPU(cores)   MEMORY(bytes)\n"


def test_top_nodes_parsed_with_typed_getters():
    """A `kubectl top nodes` row parses into name, cpu, memory."""
    rows = [_NODES_HEADER, "controller-0   445m         44%      8996Mi          391%\n"]
    output = KubectlTopOutput(rows, resource="nodes")
    entries = output.get_entries()
    assert len(entries) == 1
    entry = output.get_entry("controller-0")
    assert entry.get_name() == "controller-0"
    assert entry.get_cpu() == "445m"
    assert entry.get_memory() == "8996Mi"
    assert entry.has_positive_cpu() is True
    assert entry.has_positive_memory() is True


def test_top_pods_parsed_with_typed_getters():
    """A `kubectl top pods` row parses into name, cpu, memory (no % columns)."""
    rows = [_PODS_HEADER, "coredns-6499b57679-jsjjn   2m           29Mi\n"]
    output = KubectlTopOutput(rows, resource="pods")
    entry = output.get_entry("coredns-6499b57679-jsjjn")
    assert entry.get_cpu() == "2m"
    assert entry.get_memory() == "29Mi"
    assert entry.has_positive_cpu() is True
    assert entry.has_positive_memory() is True


def test_bare_core_cpu_is_positive():
    """CPU reported as whole cores (no `m` suffix) is still a positive reading."""
    rows = [_NODES_HEADER, "controller-0   2            44%      8996Mi          391%\n"]
    output = KubectlTopOutput(rows, resource="nodes")
    assert output.get_entry("controller-0").has_positive_cpu() is True


def test_unknown_cell_is_not_positive():
    """`<unknown>` is what top prints when metrics-server is not serving: not a reading."""
    rows = [_NODES_HEADER, "controller-0   <unknown>    <unknown> <unknown>       <unknown>\n"]
    output = KubectlTopOutput(rows, resource="nodes")
    entry = output.get_entry("controller-0")
    assert entry.has_positive_cpu() is False
    assert entry.has_positive_memory() is False


def test_zero_reading_is_not_positive():
    """A zero quantity is a real cell but not a positive reading."""
    rows = [_NODES_HEADER, "controller-0   0m           0%       0Mi             0%\n"]
    output = KubectlTopOutput(rows, resource="nodes")
    entry = output.get_entry("controller-0")
    assert entry.has_positive_cpu() is False
    assert entry.has_positive_memory() is False


def test_empty_output_has_no_entries():
    """A header-only table (no data rows) yields no entries, and a lookup raises."""
    output = KubectlTopOutput([_NODES_HEADER], resource="nodes")
    assert output.get_entries() == []
    with pytest.raises(ValueError, match=r"No top entry named 'controller-0'"):
        output.get_entry("controller-0")


def test_multiple_rows():
    """Multiple rows all parse and are retrievable by name."""
    rows = [
        _NODES_HEADER,
        "controller-0   445m         44%      8996Mi          391%\n",
        "worker-0       120m         12%      2048Mi          89%\n",
    ]
    output = KubectlTopOutput(rows, resource="nodes")
    assert len(output.get_entries()) == 2
    assert output.get_entry("worker-0").get_cpu() == "120m"
