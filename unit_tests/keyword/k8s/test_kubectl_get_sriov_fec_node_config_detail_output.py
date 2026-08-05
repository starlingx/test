"""Unit tests for SriovFecNodeConfig '-o json' detail output parsing.

Verifies that the JSON output of 'kubectl get sriovfecnodeconfigs.sriovfec.intel.com
<node> -o json' is parsed into the object graph (physical functions, accelerators,
virtual functions, configured condition) and that VFIO mode detection works.
"""

from unittest.mock import patch

import pytest

from keywords.k8s.sriov_fec_node_config.object.kubectl_get_sriov_fec_node_config_detail_output import KubectlGetSriovFecNodeConfigDetailOutput

# Module under test, used to patch the logger on the graceful-degradation paths.
OUTPUT_MODULE = "keywords.k8s.sriov_fec_node_config.object.kubectl_get_sriov_fec_node_config_detail_output"


# Single-node config in VFIO mode (pfDriver/vfDriver and bound drivers all vfio-pci).
SAMPLE_VFIO_JSON = '{"apiVersion":"sriovfec.intel.com/v2","kind":"SriovFecNodeConfig",' '"metadata":{"name":"controller-0","namespace":"sriov-fec-system"},' '"spec":{"drainSkip":true,"physicalFunctions":[{"bbDevConfig":{"acc200":' '{"maxQueueSize":1024,"numVfBundles":2}},"pciAddress":"0000:f7:00.0",' '"pfDriver":"vfio-pci","vfAmount":2,"vfDriver":"vfio-pci"}]},' '"status":{"conditions":[{"lastTransitionTime":"2026-06-29T15:33:26Z",' '"message":"Configured successfully","observedGeneration":2,' '"reason":"Succeeded","status":"True","type":"Configured"}],' '"inventory":{"sriovAccelerators":[{"deviceID":"57c0","driver":"vfio-pci",' '"maxVirtualFunctions":16,"pciAddress":"0000:f7:00.0","vendorID":"8086",' '"virtualFunctions":[{"deviceID":"57c1","driver":"vfio-pci","pciAddress":"0000:f7:00.1"},' '{"deviceID":"57c1","driver":"vfio-pci","pciAddress":"0000:f7:00.2"}]}]},' '"pfBbConfVersion":"v25.01-0-g812e032"}}'

# Single-node config in igb_uio mode (not VFIO).
SAMPLE_IGB_UIO_JSON = '{"apiVersion":"sriovfec.intel.com/v2","kind":"SriovFecNodeConfig",' '"metadata":{"name":"controller-0","namespace":"sriov-fec-system"},' '"spec":{"physicalFunctions":[{"pciAddress":"0000:f7:00.0",' '"pfDriver":"igb_uio","vfAmount":2,"vfDriver":"igb_uio"}]},' '"status":{"conditions":[{"reason":"Succeeded","status":"True","type":"Configured",' '"message":"Configured successfully"}],' '"inventory":{"sriovAccelerators":[{"deviceID":"57c0","driver":"igb_uio",' '"maxVirtualFunctions":16,"pciAddress":"0000:f7:00.0","vendorID":"8086",' '"virtualFunctions":[{"deviceID":"57c1","driver":"igb_uio","pciAddress":"0000:f7:00.1"}]}]}}}'

# List form ("items") with a Password: prefix from an sshpass-style connection.
SAMPLE_LIST_WITH_PREFIX = 'Password: {"apiVersion":"v1","items":[' + SAMPLE_VFIO_JSON + '],"kind":"List"}sysadmin@controller-0:~$'

# PF requests vfio-pci but the VFs are configured for igb_uio (mixed drivers).
SAMPLE_MIXED_DRIVER_JSON = '{"apiVersion":"sriovfec.intel.com/v2","kind":"SriovFecNodeConfig","metadata":{"name":"controller-0","namespace":"sriov-fec-system"},"spec":{"physicalFunctions":[{"pciAddress":"0000:f7:00.0","pfDriver":"vfio-pci","vfAmount":2,"vfDriver":"igb_uio"}]},"status":{"conditions":[{"reason":"Succeeded","status":"True","type":"Configured","message":"Configured successfully"}],"inventory":{"sriovAccelerators":[{"deviceID":"57c0","driver":"vfio-pci","maxVirtualFunctions":16,"pciAddress":"0000:f7:00.0","vendorID":"8086","virtualFunctions":[{"deviceID":"57c1","driver":"igb_uio","pciAddress":"0000:f7:00.1"}]}]}}}'

# Spec requests vfio-pci everywhere but one bound VF reports a different driver.
SAMPLE_BOUND_VF_MISMATCH_JSON = '{"apiVersion":"sriovfec.intel.com/v2","kind":"SriovFecNodeConfig","metadata":{"name":"controller-0","namespace":"sriov-fec-system"},"spec":{"physicalFunctions":[{"pciAddress":"0000:f7:00.0","pfDriver":"vfio-pci","vfAmount":2,"vfDriver":"vfio-pci"}]},"status":{"conditions":[{"reason":"Succeeded","status":"True","type":"Configured","message":"Configured successfully"}],"inventory":{"sriovAccelerators":[{"deviceID":"57c0","driver":"vfio-pci","maxVirtualFunctions":16,"pciAddress":"0000:f7:00.0","vendorID":"8086","virtualFunctions":[{"deviceID":"57c1","driver":"vfio-pci","pciAddress":"0000:f7:00.1"},{"deviceID":"57c1","driver":"igb_uio","pciAddress":"0000:f7:00.2"}]}]}}}'

# Card present in the status inventory but not configured in the spec.
SAMPLE_UNCONFIGURED_JSON = '{"apiVersion":"sriovfec.intel.com/v2","kind":"SriovFecNodeConfig","metadata":{"name":"controller-0","namespace":"sriov-fec-system"},"spec":{"physicalFunctions":[{"pciAddress":"0000:aa:00.0","pfDriver":"vfio-pci","vfAmount":2,"vfDriver":"vfio-pci"}]},"status":{"inventory":{"sriovAccelerators":[{"deviceID":"57c0","driver":"vfio-pci","maxVirtualFunctions":16,"pciAddress":"0000:f7:00.0","vendorID":"8086","virtualFunctions":[]}]}}}'


def test_parses_physical_function_spec_drivers():
    """Spec physicalFunctions pfDriver/vfDriver are parsed correctly."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")

    physical_functions = detail.get_physical_functions()
    assert len(physical_functions) == 1
    assert physical_functions[0].get_pci_address() == "0000:f7:00.0"
    assert physical_functions[0].get_pf_driver() == "vfio-pci"
    assert physical_functions[0].get_vf_driver() == "vfio-pci"
    assert physical_functions[0].get_vf_amount() == 2


def test_parses_inventory_accelerator_bound_driver():
    """Status inventory accelerator driver (observed binding) is parsed correctly."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")

    accelerator = detail.get_accelerator_by_device_id("57c0")
    assert accelerator.get_driver() == "vfio-pci"
    assert accelerator.get_vendor_id() == "8086"
    assert accelerator.get_max_virtual_functions() == 16
    assert accelerator.get_pci_address() == "0000:f7:00.0"


def test_parses_virtual_function_drivers():
    """Both virtual functions are parsed and bound to vfio-pci."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")

    accelerator = detail.get_accelerator_by_device_id("57c0")
    virtual_functions = accelerator.get_virtual_functions()
    assert len(virtual_functions) == 2
    assert all(virtual_function.get_driver() == "vfio-pci" for virtual_function in virtual_functions)
    assert accelerator.get_virtual_function_by_pci_address("0000:f7:00.2").get_device_id() == "57c1"


def test_parses_configured_condition():
    """The 'Configured' status condition reason/status/message are parsed."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")

    assert detail.get_configured_reason() == "Succeeded"
    assert detail.get_configured_status() == "True"
    assert detail.get_configured_message() == "Configured successfully"


def test_is_vfio_mode_true():
    """is_vfio_mode returns True when spec and inventory drivers are vfio-pci."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    assert output.is_vfio_mode("controller-0") is True


def test_is_vfio_mode_false_for_igb_uio():
    """is_vfio_mode returns False when the card is configured with igb_uio."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_IGB_UIO_JSON)
    assert output.is_vfio_mode("controller-0") is False

    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")
    assert detail.get_physical_functions()[0].get_pf_driver() == "igb_uio"
    assert detail.get_accelerator_by_device_id("57c0").get_driver() == "igb_uio"


def test_is_vfio_mode_true_for_device_id():
    """is_vfio_mode scoped to a device ID returns True when that card is vfio-pci."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    assert output.is_vfio_mode("controller-0", device_id="57c0") is True


def test_is_vfio_mode_false_for_device_id_igb_uio():
    """is_vfio_mode scoped to a device ID returns False when that card is igb_uio."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_IGB_UIO_JSON)
    assert output.is_vfio_mode("controller-0", device_id="57c0") is False


def test_is_vfio_mode_unknown_device_id_raises():
    """is_vfio_mode scoped to an unknown device ID raises ValueError."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    with pytest.raises(ValueError, match="device ID '0d5c' not found"):
        output.is_vfio_mode("controller-0", device_id="0d5c")


def test_is_vfio_mode_false_when_vf_driver_differs():
    """is_vfio_mode returns False when pfDriver is vfio-pci but vfDriver is not.

    pfDriver and vfDriver are configured independently, so a physical function
    bound to vfio-pci whose virtual functions use another driver is not VFIO mode.
    """
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_MIXED_DRIVER_JSON)

    assert output.is_vfio_mode("controller-0") is False
    assert output.is_vfio_mode("controller-0", device_id="57c0") is False

    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")
    assert detail.get_physical_functions()[0].get_pf_driver() == "vfio-pci"
    assert detail.get_physical_functions()[0].get_vf_driver() == "igb_uio"


def test_is_vfio_mode_false_when_bound_vf_driver_differs():
    """is_vfio_mode returns False when a bound virtual function driver is not vfio-pci."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_BOUND_VF_MISMATCH_JSON)

    assert output.is_vfio_mode("controller-0") is False
    assert output.is_vfio_mode("controller-0", device_id="57c0") is False

    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")
    accelerator = detail.get_accelerator_by_device_id("57c0")
    assert accelerator.get_driver() == "vfio-pci"
    assert accelerator.get_virtual_functions()[1].get_driver() == "igb_uio"


def test_is_vfio_mode_false_for_unconfigured_card():
    """is_vfio_mode returns False when the card is in the inventory but absent from the spec."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_UNCONFIGURED_JSON)
    assert output.is_vfio_mode("controller-0", device_id="57c0") is False


def test_pci_address_navigation_getters():
    """Accelerators and physical functions can be looked up by PCI address."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")

    assert detail.get_accelerator_by_pci_address("0000:f7:00.0").get_device_id() == "57c0"
    assert detail.has_physical_function_by_pci_address("0000:f7:00.0") is True
    assert detail.get_physical_function_by_pci_address("0000:f7:00.0").get_pf_driver() == "vfio-pci"

    assert detail.has_physical_function_by_pci_address("0000:ff:00.0") is False
    with pytest.raises(ValueError, match="PCI address '0000:ff:00.0' not found"):
        detail.get_accelerator_by_pci_address("0000:ff:00.0")


def test_parses_list_form_with_password_prefix():
    """List ('items') form with a Password: prefix is parsed correctly."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_LIST_WITH_PREFIX)
    details = output.get_sriov_fec_node_config_details()
    assert len(details) == 1
    assert output.is_vfio_mode("controller-0") is True


def test_get_detail_by_name_not_found_raises():
    """Looking up a non-existent node config raises ValueError."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    with pytest.raises(ValueError, match="SriovFecNodeConfig 'compute-0' not found"):
        output.get_sriov_fec_node_config_detail_by_name("compute-0")


def test_accelerator_by_device_id_not_found_raises():
    """Looking up a non-existent accelerator device ID raises ValueError."""
    output = KubectlGetSriovFecNodeConfigDetailOutput(SAMPLE_VFIO_JSON)
    detail = output.get_sriov_fec_node_config_detail_by_name("controller-0")
    with pytest.raises(ValueError, match="device ID '0d5c' not found"):
        detail.get_accelerator_by_device_id("0d5c")


def test_empty_output_yields_no_details():
    """Empty output produces an empty detail list."""
    with patch(f"{OUTPUT_MODULE}.get_logger"):
        output = KubectlGetSriovFecNodeConfigDetailOutput("")
    assert output.get_sriov_fec_node_config_details() == []


def test_malformed_json_yields_no_details():
    """Malformed JSON is handled gracefully and produces no details."""
    with patch(f"{OUTPUT_MODULE}.get_logger"):
        output = KubectlGetSriovFecNodeConfigDetailOutput("{not valid json")
    assert output.get_sriov_fec_node_config_details() == []
