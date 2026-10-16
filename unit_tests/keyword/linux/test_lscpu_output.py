from keywords.linux.lscpu.object.lscpu_output import LscpuOutput

SAMPLE_OUTPUT = """Architecture:                       x86_64
CPU op-mode(s):                     32-bit, 64-bit
CPU(s):                             64
On-line CPU(s) list:                0-63
Vendor ID:                          AuthenticAMD
Socket(s):                          2
NUMA node(s):                       4
NUMA node0 CPU(s):                  0-15
NUMA node1 CPU(s):                  16-31
"""


def test_get_cpu_count():
    """Test parsing the total CPU count."""
    output = LscpuOutput(SAMPLE_OUTPUT)
    assert output.get_cpu_count() == 64


def test_get_socket_count():
    """Test parsing the socket count."""
    output = LscpuOutput(SAMPLE_OUTPUT)
    assert output.get_socket_count() == 2


def test_get_numa_node_count():
    """Test parsing the NUMA node count."""
    output = LscpuOutput(SAMPLE_OUTPUT)
    assert output.get_numa_node_count() == 4


def test_get_field_returns_raw_value():
    """Test that an arbitrary field is returned verbatim."""
    output = LscpuOutput(SAMPLE_OUTPUT)
    assert output.get_field("Vendor ID") == "AuthenticAMD"


def test_missing_field_returns_defaults():
    """Test that absent/unparsable fields return safe defaults."""
    output = LscpuOutput("Architecture: x86_64\n")
    assert output.get_field("Socket(s)") == ""
    assert output.get_socket_count() == 0
    assert output.get_numa_node_count() == 0
    assert output.get_cpu_count() == 0


def test_empty_output():
    """Test that empty output parses to all-zero counts."""
    output = LscpuOutput("")
    assert output.get_cpu_count() == 0
    assert output.get_socket_count() == 0
    assert output.get_numa_node_count() == 0
