"""Unit tests for CPU manager state JSON parsing.

Tests that the CPU manager state file content is correctly parsed,
including cases where the output includes a 'Password:' prefix
from sshpass connections.
"""

from keywords.k8s.cat.object.cpu_manager_state_output import CpuManagerStateOutput

# Normal JSON (direct SSH — no prefix)
SAMPLE_DIRECT_SSH_JSON = '{"policyName":"static","defaultCpuSet":"1-11,13-23",' '"entries":{"abc-123":{"compute":"4,36"}},"checksum":12345}'

# JSON with Password: prefix (sshpass connection)
SAMPLE_SSHPASS_RAW = 'Password: {"policyName":"static","defaultCpuSet":"1,3-31",' '"entries":{"abc-123":{"compute":"0,2"},"def-456":{"controller":"0,2"}},' '"checksum":98765}sysadmin@compute-0:~$'

# JSON with 'none' policy
SAMPLE_NONE_POLICY_JSON = '{"policyName":"none","defaultCpuSet":"","entries":{},"checksum":0}'

# JSON with Password: prefix and 'none' policy
SAMPLE_SSHPASS_NONE_RAW = 'Password: {"policyName":"none","defaultCpuSet":"","entries":{},"checksum":0}' "sysadmin@compute-0:~$"

# Multiple entries with various CPU ranges
SAMPLE_MULTI_ENTRY_JSON = '{"policyName":"static","defaultCpuSet":"0-3",' '"entries":{' '"pod-uid-1":{"compute":"4,36"},' '"pod-uid-2":{"compute":"8-9,40-41"},' '"pod-uid-3":{"coredns":"0-1,28-29"}' '},"checksum":99999}'


def _extract_json(raw_output: str) -> str:
    """Extract JSON from raw output by stripping prefix/suffix.

    This replicates the parsing logic in get_cpu_manager_state:
    find first '{' and last '}' to extract the JSON.

    Args:
        raw_output (str): Raw command output.

    Returns:
        str: Extracted JSON string.
    """
    first_brace = raw_output.find("{")
    last_brace = raw_output.rfind("}")
    return raw_output[first_brace : last_brace + 1]


def test_extract_json_direct_ssh():
    """Test JSON extraction from direct SSH output (no prefix)."""
    json_str = _extract_json(SAMPLE_DIRECT_SSH_JSON)
    output = CpuManagerStateOutput(json_str)
    state = output.get_cpu_manager_state_object()

    assert state.get_policy_name() == "static"
    assert state.get_default_cpu_set() == "1-11,13-23"
    assert "abc-123" in state.get_entries()
    assert state.get_entries()["abc-123"]["compute"] == "4,36"


def test_extract_json_sshpass_with_password_prefix():
    """Test JSON extraction from sshpass output with Password: prefix.

    This is the key regression test — the Password: prefix and trailing
    prompt must be stripped correctly.
    """
    json_str = _extract_json(SAMPLE_SSHPASS_RAW)
    output = CpuManagerStateOutput(json_str)
    state = output.get_cpu_manager_state_object()

    assert state.get_policy_name() == "static"
    assert state.get_default_cpu_set() == "1,3-31"
    entries = state.get_entries()
    assert "abc-123" in entries
    assert "def-456" in entries
    assert entries["abc-123"]["compute"] == "0,2"
    assert entries["def-456"]["controller"] == "0,2"


def test_extract_json_none_policy():
    """Test parsing CPU manager state with 'none' policy."""
    json_str = _extract_json(SAMPLE_NONE_POLICY_JSON)
    output = CpuManagerStateOutput(json_str)
    state = output.get_cpu_manager_state_object()

    assert state.get_policy_name() == "none"
    assert state.get_entries() == {}


def test_extract_json_sshpass_none_policy():
    """Test parsing 'none' policy from sshpass output with Password: prefix."""
    json_str = _extract_json(SAMPLE_SSHPASS_NONE_RAW)
    output = CpuManagerStateOutput(json_str)
    state = output.get_cpu_manager_state_object()

    assert state.get_policy_name() == "none"
    assert state.get_entries() == {}


def test_parse_cpu_range_single_cpus():
    """Test parsing comma-separated single CPU IDs."""
    json_str = _extract_json(SAMPLE_DIRECT_SSH_JSON)
    output = CpuManagerStateOutput(json_str)
    state = output.get_cpu_manager_state_object()

    assert state.parse_cpu_range("4,36") == [4, 36]
    assert state.parse_cpu_range("0,2") == [0, 2]
    assert state.parse_cpu_range("5") == [5]


def test_parse_cpu_range_with_ranges():
    """Test parsing CPU ranges with dashes."""
    json_str = _extract_json(SAMPLE_MULTI_ENTRY_JSON)
    output = CpuManagerStateOutput(json_str)
    state = output.get_cpu_manager_state_object()

    assert state.parse_cpu_range("8-9,40-41") == [8, 9, 40, 41]
    assert state.parse_cpu_range("0-1,28-29") == [0, 1, 28, 29]
    assert state.parse_cpu_range("1-11,13-23") == list(range(1, 12)) + list(range(13, 24))


def test_multi_entry_lookup():
    """Test looking up specific entries and their CPU assignments."""
    json_str = _extract_json(SAMPLE_MULTI_ENTRY_JSON)
    output = CpuManagerStateOutput(json_str)
    state = output.get_cpu_manager_state_object()

    entries = state.get_entries()
    assert len(entries) == 3
    assert entries["pod-uid-1"]["compute"] == "4,36"
    assert entries["pod-uid-2"]["compute"] == "8-9,40-41"
    assert entries["pod-uid-3"]["coredns"] == "0-1,28-29"


def test_get_entry_pod_cpus():
    """Test getting CPU list for a specific pod in an entry."""
    json_str = _extract_json(SAMPLE_MULTI_ENTRY_JSON)
    output = CpuManagerStateOutput(json_str)
    state = output.get_cpu_manager_state_object()

    cpus = state.get_entry_pod_cpus("pod-uid-1", "compute")
    assert cpus == [4, 36]

    cpus = state.get_entry_pod_cpus("pod-uid-2", "compute")
    assert cpus == [8, 9, 40, 41]

    cpus = state.get_entry_pod_cpus("pod-uid-3", "coredns")
    assert cpus == [0, 1, 28, 29]
