from keywords.linux.sysfs.object.numa_online_nodes_output import NumaOnlineNodesOutput


def test_single_node():
    """Test a single online node ('0')."""
    output = NumaOnlineNodesOutput("0")
    assert output.get_online_node_count() == 1
    assert output.get_online_node_ids() == [0]


def test_simple_range():
    """Test a contiguous range ('0-1')."""
    output = NumaOnlineNodesOutput("0-1")
    assert output.get_online_node_count() == 2
    assert output.get_online_node_ids() == [0, 1]


def test_wider_range():
    """Test a wider contiguous range ('0-3')."""
    output = NumaOnlineNodesOutput("0-3")
    assert output.get_online_node_count() == 4
    assert output.get_online_node_ids() == [0, 1, 2, 3]


def test_comma_separated():
    """Test comma-separated singletons ('0,2')."""
    output = NumaOnlineNodesOutput("0,2")
    assert output.get_online_node_count() == 2
    assert output.get_online_node_ids() == [0, 2]


def test_mixed_ranges_and_singletons():
    """Test a mixed range/singleton list ('0-3,8,12-13')."""
    output = NumaOnlineNodesOutput("0-3,8,12-13")
    assert output.get_online_node_count() == 7
    assert output.get_online_node_ids() == [0, 1, 2, 3, 8, 12, 13]
    assert output.get_online_node_ids_as_frozenset() == frozenset({0, 1, 2, 3, 8, 12, 13})


def test_empty_string():
    """Test an empty string parses to zero nodes."""
    output = NumaOnlineNodesOutput("")
    assert output.get_online_node_count() == 0
    assert output.get_online_node_ids() == []
