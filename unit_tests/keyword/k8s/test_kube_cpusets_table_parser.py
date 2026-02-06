from keywords.k8s.kube_cpusets.object.kube_cpusets_table_parser import KubeCpusetsTableParser

SAMPLE_TABLE = """+-----------------------------+-------------------------------------------------+----------------------------+---------------+-------------------+------------+--------+----------+-------------------+
| namespace                   | pod.name                                        | container.name             | container.id  | state             | QoS        | shares | group    | cpus              |
+-----------------------------+-------------------------------------------------+----------------------------+---------------+-------------------+------------+--------+----------+-------------------+
| cert-manager                | cm-cert-manager-cainjector-65fb8bc5d5-6f4jr     | cert-manager-cainjector    | 5beb15941179a | CONTAINER_RUNNING | besteffort |      2 | platform | node 0 0,32       |
| kernel-module-management    | kmm-operator-controller-55df64956-cdqdj         | manager                    | 2efe63df8ce78 | CONTAINER_RUNNING | burstable  |      2 | default  | node 0 1-31,33-63 |
+-----------------------------+-------------------------------------------------+----------------------------+---------------+-------------------+------------+--------+----------+-------------------+
"""


def test_parse_table():
    """Test parsing kube-cpusets table."""
    parser = KubeCpusetsTableParser(SAMPLE_TABLE)
    values = parser.get_output_values_list()
    assert len(values) == 2


def test_parse_table_headers():
    """Test table headers are parsed correctly."""
    parser = KubeCpusetsTableParser(SAMPLE_TABLE)
    values = parser.get_output_values_list()
    assert "namespace" in values[0]
    assert "pod.name" in values[0]
    assert "container.name" in values[0]
    assert "cpus" in values[0]


def test_parse_table_values():
    """Test table values are parsed correctly."""
    parser = KubeCpusetsTableParser(SAMPLE_TABLE)
    values = parser.get_output_values_list()
    assert values[0]["namespace"] == "cert-manager"
    assert values[0]["group"] == "platform"
    assert values[1]["namespace"] == "kernel-module-management"
    assert values[1]["cpus"] == "node 0 1-31,33-63"
