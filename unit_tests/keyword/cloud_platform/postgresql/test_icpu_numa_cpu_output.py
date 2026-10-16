from keywords.cloud_platform.postgresql.object.icpu_numa_cpu_output import IcpuNumaCpuOutput

# Two NUMA nodes (sysinv forinodeid 1 and 2), as psql renders them by default.
SAMPLE_OUTPUT = """ forinodeid | cpu
------------+-----
          1 |   0
          1 |   1
          1 |   2
          2 |   3
          2 |   4
(5 rows)
"""


def test_get_node_cpu_sets():
    """Test the per-node CPU sets are grouped and normalized to 0-based ids."""
    output = IcpuNumaCpuOutput(SAMPLE_OUTPUT)
    assert output.get_node_cpu_sets() == {
        0: frozenset({0, 1, 2}),
        1: frozenset({3, 4}),
    }


def test_get_node_count():
    """Test the distinct NUMA node count."""
    output = IcpuNumaCpuOutput(SAMPLE_OUTPUT)
    assert output.get_node_count() == 2


def test_zero_based_normalization():
    """Test sysinv's 1-based forinodeid is normalized to 0-based node ids."""
    output = IcpuNumaCpuOutput(SAMPLE_OUTPUT)
    assert set(output.get_node_cpu_sets().keys()) == {0, 1}


def test_single_node():
    """Test a single-node (SNC-disabled) result normalizes to node 0."""
    single = " forinodeid | cpu\n------------+-----\n          1 |   0\n          1 |   1\n(2 rows)\n"
    output = IcpuNumaCpuOutput(single)
    assert output.get_node_count() == 1
    assert output.get_node_cpu_sets() == {0: frozenset({0, 1})}


def test_empty_output():
    """Test empty/no-data output yields an empty mapping."""
    output = IcpuNumaCpuOutput("")
    assert output.get_node_cpu_sets() == {}
    assert output.get_node_count() == 0


def test_header_and_footer_ignored():
    """Test the header, separator, and '(N rows)' footer are not parsed as data."""
    output = IcpuNumaCpuOutput(SAMPLE_OUTPUT)
    # 5 data CPUs total across the two nodes; header/separator/footer excluded.
    total_cpus = sum(len(cpus) for cpus in output.get_node_cpu_sets().values())
    assert total_cpus == 5
