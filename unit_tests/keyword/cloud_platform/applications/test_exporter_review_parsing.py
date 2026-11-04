"""Regression cases for review-driven parser and object refactoring."""

import json

import pytest
import yaml

from keywords.cloud_platform.applications.object.exporter_http_output import ExporterHttpOutput
from keywords.cloud_platform.applications.object.exporter_workload_output import ExporterWorkloadOutput
from keywords.cloud_platform.applications.object.interface_metrics_output import InterfaceMetricsOutput
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser
from keywords.linux.ip.object.host_interface_inventory_output import HostInterfaceInventoryOutput


def test_host_inventory_filters_admin_state_and_keeps_oper_down():
    """Admin-UP is distinct from operational link state; exclude loopback/veth."""
    links = [
        {"ifname": "eth0", "flags": ["UP"], "operstate": "DOWN"},
        {"ifname": "eth1", "flags": [], "operstate": "UP"},
        {"ifname": "lo", "flags": ["UP", "LOOPBACK"]},
        {"ifname": "veth0", "flags": ["UP"], "linkinfo": {"info_kind": "veth"}},
    ]
    inventory = HostInterfaceInventoryOutput(json.dumps(links))
    assert inventory.get_interface_names() == ("eth0",)
    inventory.set_device_paths("eth0", ["/sys/devices/0000:01:00.0/net/eth0\n", "virtfn2 /sys/devices/0000:01:00.2\n"])
    assert inventory.get_interfaces() == {"eth0": {"pciaddr": "0000:01:00.0", "vfs": {"2": "0000:01:00.2"}}}


@pytest.mark.parametrize("paths", ["/sys/device\nvirtfn0 invalid", "/sys/device\nvirtfn0 /0000:01:00.1\nvirtfn0 /0000:01:00.2"])
def test_malformed_vf_evidence_fails(paths):
    """Do not turn missing or contradictory VF PCI evidence into success."""
    inventory = HostInterfaceInventoryOutput('[{"ifname":"eth0","flags":["UP"]}]')
    with pytest.raises(ValueError):
        inventory.set_device_paths("eth0", paths)


def test_virtual_interface_has_no_pci_or_vfs():
    """An eligible virtual interface can legitimately lack a sysfs device."""
    inventory = HostInterfaceInventoryOutput('[{"ifname":"bridge0","flags":["UP"]}]')
    inventory.set_device_paths("bridge0", "")
    assert inventory.get_interfaces() == {"bridge0": {"pciaddr": "", "vfs": {}}}


def test_metric_objects_preserve_labels_and_values():
    """Parsed objects expose defensive label copies and numeric values."""
    output = InterfaceMetricsOutput('packets{device="eth0"} 42')
    sample = output.get_samples()[0]
    sample.get_labels()["device"] = "wrong"
    assert sample.get_name() == "packets"
    assert sample.get_value() == 42
    assert output.require_sample("packets", {"device": "eth0"}) == 42


def test_http_accessors_preserve_status_and_body():
    """Explicit setters/getters retain negative HTTP evidence."""
    output = ExporterHttpOutput.from_curl(["unavailable\n", "503"], 0)
    assert (output.get_status_code(), output.get_body()) == (503, "unavailable")
    output.set_status_code(200)
    output.set_body("metric 1")
    assert (output.get_status_code(), output.get_body()) == (200, "metric 1")


@pytest.mark.parametrize("selector", [{}, {"matchLabels": {}}, {"matchLabels": {"app": "exporter"}, "matchExpressions": [{"key": "a"}]}])
def test_selector_getter_rejects_unsupported_queries(selector):
    """Keep selector validation in the output object."""
    with pytest.raises(ValueError):
        ExporterWorkloadOutput({"spec": {"selector": selector}}, []).get_label_selector()


def test_selector_getter_is_deterministic():
    """Return an equality selector without changing eligibility or readiness."""
    output = ExporterWorkloadOutput({"spec": {"selector": {"matchLabels": {"z": "2", "a": "1"}}}}, [])
    assert output.get_label_selector() == "a=1,z=2"


def test_vertical_parser_preserves_yaml_and_flattened_text_together():
    """Handle YAML, literal pipes, wrapped prose and legacy binary in one table."""
    border = "+--------------------+--------------------------------------------------------------+"
    rows = [border, "| Property           | Value                                                        |", border]
    fields = [("user_overrides", ["image:", "  tag: candidate", "message: |", "  first | second", "  third", ""]), ("progress", ["Application update", "completed."]), ("certificate", ["!!binary |", "YWJj", "ZA=="])]
    for key, lines in fields:
        rows.extend(f"| {key if index == 0 else '':<18} | {line:<60} |" for index, line in enumerate(lines))
    rows.append(border)
    values = SystemVerticalTableParser(rows).get_output_values_dict()
    assert yaml.safe_load(values["user_overrides"]) == {"image": {"tag": "candidate"}, "message": "first | second\nthird\n"}
    assert values["progress"] == "Application update completed."
    assert values["certificate"].strip() == "YWJj ZA=="
