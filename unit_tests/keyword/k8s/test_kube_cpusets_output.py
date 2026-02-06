from keywords.k8s.kube_cpusets.object.kube_cpusets_output import KubeCpusetsOutput

SAMPLE_OUTPUT = """2026-02-06 16:47:23,345 1319643 INFO kube_cpusets: host:controller-0, system_type=All-in-one, nodetype=controller, subfunction=controller,worker,lowlatency, cpumanager_policy=static

Per-container cpusets:
+-----------------------------+-------------------------------------------------+----------------------------+---------------+-------------------+------------+--------+----------+-------------------+
| namespace                   | pod.name                                        | container.name             | container.id  | state             | QoS        | shares | group    | cpus              |
+-----------------------------+-------------------------------------------------+----------------------------+---------------+-------------------+------------+--------+----------+-------------------+
| cert-manager                | cm-cert-manager-cainjector-65fb8bc5d5-6f4jr     | cert-manager-cainjector    | 5beb15941179a | CONTAINER_RUNNING | besteffort |      2 | platform | node 0 0,32       |
| kernel-module-management    | kmm-operator-controller-55df64956-cdqdj         | manager                    | 2efe63df8ce78 | CONTAINER_RUNNING | burstable  |      2 | default  | node 0 1-31,33-63 |
| kernel-module-management    | kmm-operator-webhook-65cd7859b5-7v9qq           | webhook-server             | a932af9477c56 | CONTAINER_RUNNING | burstable  |      2 | default  | node 0 1-31,33-63 |
| kube-system                 | calico-kube-controllers-545d5c5774-2hk4k        | calico-kube-controllers    | 29d12972c4f1e | CONTAINER_RUNNING | besteffort |      2 | platform | node 0 0,32       |
+-----------------------------+-------------------------------------------------+----------------------------+---------------+-------------------+------------+--------+----------+-------------------+

Logical cpusets usage per numa node:
+------+-------+----------+---------------+---------------+------------+------------+
| Node | Total | Platform | Isolated_used | Isolated_free | Guaranteed |    Default |
+------+-------+----------+---------------+---------------+------------+------------+
|    0 |  0-63 |     0,32 |             - |             - |          - | 1-31,33-63 |
+------+-------+----------+---------------+---------------+------------+------------+
"""


def test_parse_output():
    """Test parsing kube-cpusets output."""
    output = KubeCpusetsOutput(SAMPLE_OUTPUT)
    containers = output.get_containers()
    assert len(containers) == 4


def test_get_containers_by_namespace():
    """Test filtering containers by namespace."""
    output = KubeCpusetsOutput(SAMPLE_OUTPUT)
    kmm_containers = output.get_containers_by_namespace("kernel-module-management")
    assert len(kmm_containers) == 2
    assert all(c.get_namespace() == "kernel-module-management" for c in kmm_containers)


def test_get_containers_by_pod_name():
    """Test filtering containers by pod name."""
    output = KubeCpusetsOutput(SAMPLE_OUTPUT)
    containers = output.get_containers_by_pod_name("kmm-operator")
    assert len(containers) == 2


def test_get_containers_by_group():
    """Test filtering containers by group."""
    output = KubeCpusetsOutput(SAMPLE_OUTPUT)
    default_containers = output.get_containers_by_group("default")
    assert len(default_containers) == 2
    platform_containers = output.get_containers_by_group("platform")
    assert len(platform_containers) == 2
