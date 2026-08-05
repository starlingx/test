"""Unit tests for the SriovFecNodeConfig detail keyword method.

Verifies that get_sriov_fec_node_config_detail issues the '-o json' command and
returns a parsed object reporting the configured and bound drivers, using a
mocked SSH connection so no live cluster is required.

The base keyword logs every keyword call, so each test patches the logger to
avoid requiring a configured logger.
"""

from unittest.mock import NonCallableMagicMock, patch

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.sriov_fec_node_config.kubectl_get_sriov_fec_node_config_keywords import KubectlGetSriovFecNodeConfigKeywords

SAMPLE_VFIO_JSON = '{"apiVersion":"sriovfec.intel.com/v2","kind":"SriovFecNodeConfig","metadata":{"name":"controller-0","namespace":"sriov-fec-system"},"spec":{"physicalFunctions":[{"pciAddress":"0000:f7:00.0","pfDriver":"vfio-pci","vfAmount":2,"vfDriver":"vfio-pci"}]},"status":{"conditions":[{"reason":"Succeeded","status":"True","type":"Configured","message":"Configured successfully"}],"inventory":{"sriovAccelerators":[{"deviceID":"57c0","driver":"vfio-pci","maxVirtualFunctions":16,"pciAddress":"0000:f7:00.0","vendorID":"8086","virtualFunctions":[{"deviceID":"57c1","driver":"vfio-pci","pciAddress":"0000:f7:00.1"}]}]}}}'


def build_mock_ssh_connection(return_value: str) -> NonCallableMagicMock:
    """Build a non-callable mocked SSH connection.

    A non-callable mock is required because BaseKeyword.__getattribute__ wraps
    callable attributes with its keyword-logging hook.

    Args:
        return_value (str): The value the mocked send() should return.

    Returns:
        NonCallableMagicMock: The mocked SSH connection.
    """
    ssh_connection = NonCallableMagicMock(spec=SSHConnection)
    ssh_connection.send.return_value = return_value
    ssh_connection.get_return_code.return_value = 0
    return ssh_connection


@patch("keywords.base_keyword.get_logger")
def test_detail_method_issues_o_json_command(mock_get_logger):
    """The detail method sends the resource '-o json' command for the node."""
    ssh_connection = build_mock_ssh_connection(SAMPLE_VFIO_JSON)
    keyword = KubectlGetSriovFecNodeConfigKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    keyword.get_sriov_fec_node_config_detail("controller-0")

    sent_command = ssh_connection.send.call_args[0][0]
    assert "sriovfecnodeconfigs.sriovfec.intel.com controller-0" in sent_command
    assert "-n sriov-fec-system" in sent_command
    assert "-o json" in sent_command


@patch("keywords.base_keyword.get_logger")
def test_detail_method_returns_vfio_mode_object(mock_get_logger):
    """The returned object reports VFIO mode and the bound driver from the mocked JSON."""
    ssh_connection = build_mock_ssh_connection(SAMPLE_VFIO_JSON)
    keyword = KubectlGetSriovFecNodeConfigKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    output = keyword.get_sriov_fec_node_config_detail("controller-0")

    assert output.is_vfio_mode("controller-0") is True
    assert output.is_vfio_mode("controller-0", device_id="57c0") is True
    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")
    assert detail.get_physical_functions()[0].get_pf_driver() == "vfio-pci"
    assert detail.get_accelerator_by_device_id("57c0").get_driver() == "vfio-pci"


@patch("keywords.base_keyword.get_logger")
def test_detail_method_custom_namespace(mock_get_logger):
    """A custom namespace is reflected in the issued command."""
    ssh_connection = build_mock_ssh_connection(SAMPLE_VFIO_JSON)
    keyword = KubectlGetSriovFecNodeConfigKeywords(ssh_connection, kubeconfig_path="/tmp/fake-kubeconfig")

    keyword.get_sriov_fec_node_config_detail("controller-0", namespace="custom-ns")

    sent_command = ssh_connection.send.call_args[0][0]
    assert "-n custom-ns" in sent_command
