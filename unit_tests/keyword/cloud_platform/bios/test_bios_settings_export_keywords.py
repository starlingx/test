import json
from unittest.mock import MagicMock, patch

import pytest

from keywords.cloud_platform.bios.bios_settings_export_keywords import BiosSettingsExportKeywords

MODULE = "keywords.cloud_platform.bios.bios_settings_export_keywords"


def _lab_config(*nodes: MagicMock) -> MagicMock:
    """Build a lab configuration holding the given nodes.

    Args:
        *nodes (MagicMock): Nodes with a configured name.

    Returns:
        MagicMock: Lab configuration double.
    """
    lab_config = MagicMock()
    lab_config.get_nodes.return_value = list(nodes)
    lab_config.get_node.side_effect = lambda name: next(node for node in nodes if node.get_name() == name)
    return lab_config


def _node(name: str, capabilities: list[str]) -> MagicMock:
    """Build a node with BMC credentials.

    Args:
        name (str): Node name.
        capabilities (list[str]): Node capabilities.

    Returns:
        MagicMock: Node double.
    """
    node = MagicMock()
    node.get_name.return_value = name
    node.get_node_capabilities.return_value = capabilities
    node.get_bm_ip.return_value = "192.0.2.10"
    node.get_bm_username.return_value = "admin"
    node.get_bm_password.return_value = "secret"
    return node


def test_exports_host_sources_and_skips_redfish_without_capability(tmp_path):
    """Write every host source and record Redfish as unsupported on IPMI-only nodes."""
    lab_config = _lab_config(_node("controller-0", ["lab_has_bmc_ipmi"]))
    with (
        patch(f"{MODULE}.ConfigurationManager") as configuration_manager,
        patch(f"{MODULE}.get_logger"),
        patch("keywords.base_keyword.get_logger"),
        patch(f"{MODULE}.LabConnectionKeywords"),
        patch(f"{MODULE}.FileKeywords") as file_keywords,
        patch(f"{MODULE}.DmiKeywords") as dmi_keywords,
        patch(f"{MODULE}.CpuPowerKeywords") as cpu_power_keywords,
        patch(f"{MODULE}.IsIPMIToolKeywords") as is_ipmitool_keywords,
        patch(f"{MODULE}.IPMIToolMcInfoKeywords") as mc_info_keywords,
        patch(f"{MODULE}.BiosOperations") as bios_operations,
    ):
        configuration_manager.get_lab_config.return_value = lab_config
        file_keywords.return_value.read_file.return_value = ["BOOT_IMAGE=/vmlinuz nohz_full=1-3\n"]
        dmi_keywords.return_value.get_bios_identity.return_value.to_dictionary.return_value = {"bios_version": "1.01"}
        cpu_power_keywords.return_value.get_cpu_power_settings.return_value.to_dictionary.return_value = {"derived": {"turbo": "enabled"}}
        is_ipmitool_keywords.return_value.is_ipmi_tool_available.return_value = True
        mc_info_keywords.return_value.get_ipmitool_mc_info.return_value.to_dictionary.return_value = {"firmware_revision": "2.80"}
        manifest_path = BiosSettingsExportKeywords().export_lab_bios_settings(str(tmp_path))

    manifest = json.loads(open(manifest_path, encoding="utf-8").read())
    assert manifest == {"status": "completed", "hosts": {"controller-0": {"status": "exported", "summary": "controller-0/collection_summary.json"}}}
    summary = json.loads((tmp_path / "controller-0" / "collection_summary.json").read_text())
    assert summary["sources"]["redfish"]["status"] == "unsupported"
    assert json.loads((tmp_path / "controller-0" / "host" / "boot_parameters.json").read_text()) == "BOOT_IMAGE=/vmlinuz nohz_full=1-3"
    assert json.loads((tmp_path / "controller-0" / "ipmi" / "mc_info.json").read_text()) == {"firmware_revision": "2.80"}
    bios_operations.assert_not_called()


def test_failed_source_keeps_error_message_and_marks_host_partial(tmp_path):
    """Record the failure message of one source while the others are still collected."""
    lab_config = _lab_config(_node("controller-0", []))
    with (
        patch(f"{MODULE}.ConfigurationManager") as configuration_manager,
        patch(f"{MODULE}.get_logger"),
        patch("keywords.base_keyword.get_logger"),
        patch(f"{MODULE}.LabConnectionKeywords"),
        patch(f"{MODULE}.FileKeywords") as file_keywords,
        patch(f"{MODULE}.DmiKeywords") as dmi_keywords,
        patch(f"{MODULE}.CpuPowerKeywords") as cpu_power_keywords,
        patch(f"{MODULE}.IsIPMIToolKeywords") as is_ipmitool_keywords,
    ):
        configuration_manager.get_lab_config.return_value = lab_config
        file_keywords.return_value.read_file.return_value = ["BOOT_IMAGE=/vmlinuz\n"]
        dmi_keywords.return_value.get_bios_identity.side_effect = TimeoutError("SSH command timed out")
        cpu_power_keywords.return_value.get_cpu_power_settings.return_value.to_dictionary.return_value = {}
        is_ipmitool_keywords.return_value.is_ipmi_tool_available.return_value = False
        manifest_path = BiosSettingsExportKeywords().export_lab_bios_settings(str(tmp_path))

    assert json.loads(open(manifest_path, encoding="utf-8").read())["status"] == "partial"
    sources = json.loads((tmp_path / "controller-0" / "collection_summary.json").read_text())["sources"]
    assert sources["host/bios_identity"] == {"status": "failed", "error_type": "TimeoutError", "error": "SSH command timed out"}
    assert sources["host/cpu_power_settings"]["status"] == "collected"
    assert sources["ipmi/mc_info"]["status"] == "unsupported"


def test_unreachable_host_still_exports_redfish_and_is_partial(tmp_path):
    """Collect BMC data over Redfish when SSH fails, without reporting the host as exported."""
    lab_config = _lab_config(_node("controller-0", ["lab_has_bmc_redfish"]))
    with (
        patch(f"{MODULE}.ConfigurationManager") as configuration_manager,
        patch(f"{MODULE}.get_logger"),
        patch("keywords.base_keyword.get_logger"),
        patch(f"{MODULE}.LabConnectionKeywords") as lab_connection_keywords,
        patch(f"{MODULE}.GetSystemInfo") as get_system_info,
        patch(f"{MODULE}.BiosOperations") as bios_operations,
    ):
        configuration_manager.get_lab_config.return_value = lab_config
        lab_connection_keywords.return_value.get_ssh_for_hostname.side_effect = OSError("connection refused")
        get_system_info.return_value.get_system_info.return_value.to_bios_identity_dictionary.return_value = {"id": "1", "bios_version": "2.19.1", "manufacturer": "Dell Inc.", "model": "PowerEdge R750"}
        bios_operations.return_value.get_bios.return_value.to_dictionary.return_value = {
            "id": "/redfish/v1/Systems/1/Bios",
            "attribute_registry": "BiosAttributeRegistry.v1_0_0",
            "attributes": {"ProcCStates": "Disabled", "AdminPassword": "plain"},
        }
        manifest_path = BiosSettingsExportKeywords().export_lab_bios_settings(str(tmp_path))

    assert json.loads(open(manifest_path, encoding="utf-8").read())["hosts"]["controller-0"]["status"] == "partial"
    sources = json.loads((tmp_path / "controller-0" / "collection_summary.json").read_text())["sources"]
    assert sources["host/ssh_connection"]["error"] == "connection refused"
    assert "host/bios_identity" not in sources
    redfish_bios = json.loads((tmp_path / "controller-0" / "redfish" / "bios.json").read_text())
    assert redfish_bios["attributes"] == {"ProcCStates": "Disabled", "AdminPassword": "<redacted>"}
    assert json.loads((tmp_path / "controller-0" / "redfish" / "system.json").read_text())["bios_version"] == "2.19.1"


def test_keyword_logging_does_not_record_bmc_password(tmp_path):
    """Keep BMC credentials out of the BaseKeyword call log."""
    lab_config = _lab_config(_node("controller-0", ["lab_has_bmc_redfish"]))
    with (
        patch(f"{MODULE}.ConfigurationManager") as configuration_manager,
        patch(f"{MODULE}.get_logger"),
        patch("keywords.base_keyword.get_logger") as keyword_logger,
        patch(f"{MODULE}.LabConnectionKeywords") as lab_connection_keywords,
        patch(f"{MODULE}.GetSystemInfo") as get_system_info,
        patch(f"{MODULE}.BiosOperations") as bios_operations,
    ):
        configuration_manager.get_lab_config.return_value = lab_config
        lab_connection_keywords.return_value.get_ssh_for_hostname.side_effect = OSError("connection refused")
        get_system_info.return_value.get_system_info.side_effect = RuntimeError("unreachable")
        bios_operations.return_value.get_bios.side_effect = RuntimeError("unreachable")
        BiosSettingsExportKeywords().export_lab_bios_settings(str(tmp_path))

    logged = " ".join(str(call) for call in keyword_logger.return_value.log_keyword.call_args_list)
    assert "export_lab_bios_settings" in logged
    assert "secret" not in logged


def test_unexpected_error_is_not_swallowed(tmp_path):
    """Let an unexpected error fail the export instead of recording it as a failed source."""
    lab_config = _lab_config(_node("controller-0", []))
    with (
        patch(f"{MODULE}.ConfigurationManager") as configuration_manager,
        patch(f"{MODULE}.get_logger"),
        patch("keywords.base_keyword.get_logger"),
        patch(f"{MODULE}.LabConnectionKeywords"),
        patch(f"{MODULE}.FileKeywords") as file_keywords,
        patch(f"{MODULE}.DmiKeywords") as dmi_keywords,
    ):
        configuration_manager.get_lab_config.return_value = lab_config
        file_keywords.return_value.read_file.return_value = ["BOOT_IMAGE=/vmlinuz\n"]
        dmi_keywords.return_value.get_bios_identity.side_effect = ValueError("parser bug")
        with pytest.raises(ValueError, match="parser bug"):
            BiosSettingsExportKeywords().export_lab_bios_settings(str(tmp_path))
