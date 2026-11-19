from keywords.k8s.node.object.kubectl_label_node_list_output import KubectlLabelNodeListOutput

SAMPLE_OUTPUT_ALL_NODES = """
Listing labels for Node./controller-0:
 feature.node.kubernetes.io/cpu-cpuid.AVX2=true
 feature.node.kubernetes.io/cpu-model.family=6
 kubernetes.io/hostname=controller-0
Listing labels for Node./worker-0:
 feature.node.kubernetes.io/cpu-cpuid.AVX2=true
 kubernetes.io/hostname=worker-0
"""

SAMPLE_OUTPUT_SINGLE_NODE = """
 feature.node.kubernetes.io/cpu-cpuid.AVX2=true
 feature.node.kubernetes.io/cpu-model.family=6
 kubernetes.io/hostname=controller-0
"""

NFD_PREFIX = "feature.node.kubernetes.io"


def test_get_node_names_with_all_nodes_output():
    """Test that every node header in the output is returned"""
    output = KubectlLabelNodeListOutput(SAMPLE_OUTPUT_ALL_NODES)

    assert output.get_node_names() == ["controller-0", "worker-0"]


def test_get_node_names_with_single_node_output():
    """Test that the default node name is used when there is no header"""
    output = KubectlLabelNodeListOutput(SAMPLE_OUTPUT_SINGLE_NODE, "controller-0")

    assert output.get_node_names() == ["controller-0"]


def test_get_node_names_with_empty_output():
    """Test that empty output without a default node name has no nodes"""
    output = KubectlLabelNodeListOutput("")

    assert output.get_node_names() == []


def test_output_as_list_of_lines():
    """Test that the output can be given as a list of lines"""
    output = KubectlLabelNodeListOutput(SAMPLE_OUTPUT_ALL_NODES.splitlines())

    assert output.get_node_names() == ["controller-0", "worker-0"]
    assert output.get_count_on_node_by_prefix("controller-0", NFD_PREFIX) == 2


def test_get_label_keys_on_node_by_prefix():
    """Test that only the label keys containing the prefix are returned"""
    output = KubectlLabelNodeListOutput(SAMPLE_OUTPUT_ALL_NODES)

    assert output.get_label_keys_on_node_by_prefix("controller-0", NFD_PREFIX) == [
        "feature.node.kubernetes.io/cpu-cpuid.AVX2",
        "feature.node.kubernetes.io/cpu-model.family",
    ]


def test_get_label_keys_on_node_by_prefix_no_match():
    """Test that a prefix without matches returns an empty list"""
    output = KubectlLabelNodeListOutput(SAMPLE_OUTPUT_ALL_NODES)

    assert output.get_label_keys_on_node_by_prefix("controller-0", "does-not-exist") == []


def test_get_label_keys_on_unknown_node():
    """Test that an unknown node returns an empty list"""
    output = KubectlLabelNodeListOutput(SAMPLE_OUTPUT_ALL_NODES)

    assert output.get_label_keys_on_node_by_prefix("unknown-node", NFD_PREFIX) == []


def test_get_count_on_node_by_prefix():
    """Test the label count of each node for a prefix"""
    output = KubectlLabelNodeListOutput(SAMPLE_OUTPUT_ALL_NODES)

    assert output.get_count_on_node_by_prefix("controller-0", NFD_PREFIX) == 2
    assert output.get_count_on_node_by_prefix("worker-0", NFD_PREFIX) == 1


def test_get_count_on_node_by_prefix_single_node_output():
    """Test the label count when the output has no node header"""
    output = KubectlLabelNodeListOutput(SAMPLE_OUTPUT_SINGLE_NODE, "controller-0")

    assert output.get_count_on_node_by_prefix("controller-0", NFD_PREFIX) == 2


def test_get_count_all_nodes_by_prefix():
    """Test that the count is summed across all nodes"""
    output = KubectlLabelNodeListOutput(SAMPLE_OUTPUT_ALL_NODES)

    assert output.get_count_all_nodes_by_prefix(NFD_PREFIX) == 3
    assert output.get_count_all_nodes_by_prefix("kubernetes.io/hostname") == 2
    assert output.get_count_all_nodes_by_prefix("does-not-exist") == 0


def test_get_labels_on_node_values():
    """Test that label values are parsed, including values containing '='"""
    output = KubectlLabelNodeListOutput("Listing labels for Node./controller-0:\n a.b/c=x=y\n d=\n")

    assert output.get_labels_on_node("controller-0") == {"a.b/c": "x=y", "d": ""}
