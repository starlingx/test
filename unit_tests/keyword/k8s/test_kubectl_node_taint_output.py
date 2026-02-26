from keywords.k8s.node.object.kubectl_node_taint_output import KubectlNodeTaintOutput

SAMPLE_OUTPUT_MULTIPLE_TAINTS = """
Node                                               Taint
controller-0	node-role.kubernetes.io/control-plane=:NoSchedule	
controller-1	node-role.kubernetes.io/master=:NoSchedule	
"""

SAMPLE_OUTPUT_NO_TAINTS = """
Node                                              Taint
"""

SAMPLE_OUTPUT_WITH_VALUES = """
Node                                              Taint
controller-0	custom-taint=special-value:NoExecute	
"""

SAMPLE_OUTPUT_MULTIPLE_TAINTS_SAME_NODE = """
Node                                              Taint
controller-0	node-role.kubernetes.io/control-plane=:NoSchedule	node-role.kubernetes.io/master=:NoSchedule	
"""

SAMPLE_OUTPUT_MIXED_NODES = """
Node                                              Taint
controller-0	node-role.kubernetes.io/control-plane=:NoSchedule	
controller-1	node-role.kubernetes.io/control-plane=:NoSchedule	
worker-0	custom-taint=value:NoExecute	
"""


def test_parse_output_with_multiple_taints():
    """Test parsing output with multiple nodes having taints"""
    output = KubectlNodeTaintOutput(SAMPLE_OUTPUT_MULTIPLE_TAINTS)
    taints = output.get_taints()
    
    assert len(taints) == 2
    assert taints[0].get_node() == "controller-0"
    assert taints[0].get_key() == "node-role.kubernetes.io/control-plane"
    assert taints[0].get_effect() == "NoSchedule"


def test_parse_output_with_no_taints():
    """Test parsing output when no nodes have taints"""
    output = KubectlNodeTaintOutput(SAMPLE_OUTPUT_NO_TAINTS)
    taints = output.get_taints()
    
    assert len(taints) == 0


def test_parse_output_with_taint_values():
    """Test parsing taints that have non-empty values"""
    output = KubectlNodeTaintOutput(SAMPLE_OUTPUT_WITH_VALUES)
    taints = output.get_taints()
    
    assert len(taints) == 1
    assert taints[0].get_key() == "custom-taint"
    assert taints[0].get_value() == "special-value"
    assert taints[0].get_effect() == "NoExecute"


def test_taint_enabled():
    """Test checking if a specific taint exists"""
    output = KubectlNodeTaintOutput(SAMPLE_OUTPUT_MULTIPLE_TAINTS)
    
    assert output.is_taints_enabled("node-role.kubernetes.io/control-plane") == True
    assert output.is_taints_enabled("non-existent-taint") == False


def test_taint_enabled_with_effect():
    """Test checking taint with specific effect"""
    output = KubectlNodeTaintOutput(SAMPLE_OUTPUT_MULTIPLE_TAINTS)
    
    assert output.is_taints_enabled("node-role.kubernetes.io/control-plane", "NoSchedule") == True
    assert output.is_taints_enabled("node-role.kubernetes.io/control-plane", "NoExecute") == False


def test_count_taints():
    """Test counting taints"""
    output = KubectlNodeTaintOutput(SAMPLE_OUTPUT_MIXED_NODES)
    
    assert output.count_taints() == 3
    assert output.count_taints("node-role.kubernetes.io/control-plane") == 2
    assert output.count_taints("custom-taint") == 1
    assert output.count_taints("non-existent") == 0


def test_multiple_taints_same_node():
    """Test parsing when a single node has multiple taints"""
    output = KubectlNodeTaintOutput(SAMPLE_OUTPUT_MULTIPLE_TAINTS_SAME_NODE)
    taints = output.get_taints()
    
    assert len(taints) == 2
    assert taints[0].get_node() == "controller-0"
    assert taints[1].get_node() == "controller-0"
    assert taints[0].get_key() != taints[1].get_key()
