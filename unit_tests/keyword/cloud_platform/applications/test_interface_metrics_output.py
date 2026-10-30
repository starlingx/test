"""Strict metric evidence tests, including false-positive and identity cases."""

import pytest

from keywords.cloud_platform.applications.object.interface_metrics_output import InterfaceMetricsOutput


@pytest.mark.parametrize("body", ["", "# HELP only comments", "error from proxy", "metric NaN", "metric +Inf", "metric 1_000", "metric 1\nmetric 2", 'metric{x="a",x="b"} 1', 'metric{x="bad\\q"} 1', 'metric{x="unterminated} 1'])
def test_reject_bad_evidence(body):
    """Malformed and ambiguous evidence must not be silently skipped."""
    with pytest.raises(ValueError):
        InterfaceMetricsOutput(body)


def test_escaped_labels_and_timestamp():
    """Commas, whitespace, quotes and timestamps do not corrupt label/value parsing."""
    output = InterfaceMetricsOutput('metric{alias="a,b c\\"d\\ne",device="eth0"} 2.5e2 12345')
    assert output.require_sample("metric", {"alias": 'a,b c"d\ne'}) == 250
    with pytest.raises(ValueError):
        output.require_sample("met", {})


def test_interface_identity_and_vfs():
    """Every required PF/VF identity must agree with independent inventory."""
    output = InterfaceMetricsOutput('network_interface_device_info{device="eth0",pciaddr="0000:01:00.0"} 1\nnetwork_interface_vf_device_info{device="eth0",vf="0",pciaddr="0000:01:01.0"} 1')
    output.verify_interfaces({"eth0": {"pciaddr": "0000:01:00.0", "vfs": {"0": "0000:01:01.0"}}})
    with pytest.raises(ValueError):
        output.verify_interfaces({"eth0": {"pciaddr": "0000:01:00.0", "vfs": {"0": "0000:01:02.0"}}})
    with pytest.raises(ValueError):
        output.verify_interfaces({})


def test_ambiguous_subset_identity():
    """Multiple devices cannot satisfy a single expected identity."""
    output = InterfaceMetricsOutput('metric{device="a"} 1\nmetric{device="b"} 2')
    with pytest.raises(ValueError):
        output.require_sample("metric", {})


def test_contradictory_device_identity():
    """A correct identity alongside a conflicting PCI identity is still invalid."""
    with pytest.raises(ValueError, match="Contradictory"):
        InterfaceMetricsOutput('network_interface_device_info{device="eth0",pciaddr="0000:01:00.0"} 1\nnetwork_interface_device_info{device="eth0",pciaddr="0000:02:00.0"} 1')
