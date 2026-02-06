from keywords.k8s.kube_cpusets.object.kube_cpusets_object import KubeCpusetsObject


def test_get_cpu_list_comma_separated():
    """Test get_cpu_list with comma-separated values."""
    obj = KubeCpusetsObject()
    obj.set_cpus("node 0 0,32")
    assert obj.get_cpu_list() == [0, 32]


def test_get_cpu_list_range():
    """Test get_cpu_list with CPU range."""
    obj = KubeCpusetsObject()
    obj.set_cpus("node 0 1-3")
    assert obj.get_cpu_list() == [1, 2, 3]


def test_get_cpu_list_single_number():
    """Test get_cpu_list with single CPU number."""
    obj = KubeCpusetsObject()
    obj.set_cpus("node 0 5")
    assert obj.get_cpu_list() == [5]


def test_get_cpu_list_complex_range():
    """Test get_cpu_list with complex comma-separated ranges."""
    obj = KubeCpusetsObject()
    obj.set_cpus("node 0 1-31,33-63")
    result = obj.get_cpu_list()
    expected = list(range(1, 32)) + list(range(33, 64))
    assert result == expected


def test_get_cpu_list_empty():
    """Test get_cpu_list with empty cpus."""
    obj = KubeCpusetsObject()
    assert obj.get_cpu_list() == []
