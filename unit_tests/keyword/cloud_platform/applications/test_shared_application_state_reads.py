"""Shared read contracts used by interface exporter recovery."""

from unittest.mock import NonCallableMock, patch

import pytest
import yaml

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords import NodeInterfaceMetricsExporterKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords


@pytest.fixture(autouse=True)
def keyword_logging():
    """Keep keyword logging independent of global lab configuration."""
    with patch("keywords.base_keyword.get_logger"):
        yield


@pytest.mark.parametrize("present", [True, False])
def test_shared_application_state(present):
    """Only a successfully parsed inventory can establish app absence."""
    keywords = SystemApplicationListKeywords(NonCallableMock())
    inventory = NonCallableMock()
    inventory.application_exists.return_value = present
    inventory.get_application.return_value.get_version.return_value = "1"
    inventory.get_application.return_value.get_status.return_value = "applied"
    with patch.object(keywords, "get_system_application_list", return_value=inventory) as read:
        assert keywords.get_application_state("app") == (("1", "applied") if present else None)
        read.assert_called_once_with()
    with patch.object(keywords, "get_system_application_list", side_effect=AssertionError("CLI failed")):
        with pytest.raises(AssertionError):
            keywords.get_application_state("app")


@pytest.mark.parametrize("raw_user_override_content,expected", [(None, {}), ("None", {}), ("null", {}), ("{}", {}), ({"image": {"tag": "old"}}, {"image": {"tag": "old"}}), ("image:\n  tag: old", {"image": {"tag": "old"}})])
def test_shared_user_values(raw_user_override_content, expected):
    """Retain empty and nonempty user mappings without defaults."""
    keywords = SystemHelmOverrideKeywords(NonCallableMock())
    output = NonCallableMock()
    output.get_helm_override_show.return_value.get_user_overrides.return_value = raw_user_override_content
    with patch.object(keywords, "get_system_helm_override_show", return_value=output):
        assert keywords.get_user_override_values("app", "chart", "namespace") == expected


@pytest.mark.parametrize("raw_user_override_content", ["[one, two]", "true", "invalid: [", "scalar"])
def test_invalid_user_values_propagate(raw_user_override_content):
    """Malformed/nonmapping configuration cannot become an empty baseline."""
    keywords = SystemHelmOverrideKeywords(NonCallableMock())
    output = NonCallableMock()
    output.get_helm_override_show.return_value.get_user_overrides.return_value = raw_user_override_content
    with patch.object(keywords, "get_system_helm_override_show", return_value=output):
        with pytest.raises((KeywordException, yaml.YAMLError)):
            keywords.get_user_override_values("app", "chart", "namespace")


def test_exporter_delegates_to_shared_reads():
    """Exercise exporter wrappers against the real shared read methods."""
    app = namespace = "node-interface-metrics-exporter"
    keywords = NodeInterfaceMetricsExporterKeywords(NonCallableMock(), "/etc/kubernetes/admin.conf")
    inventory = NonCallableMock()
    inventory.application_exists.return_value = True
    inventory.get_application.return_value.get_version.return_value = "original"
    inventory.get_application.return_value.get_status.return_value = "applied"
    output = NonCallableMock()
    output.get_helm_override_show.return_value.get_user_overrides.return_value = "custom: original"
    with patch.object(SystemApplicationListKeywords, "get_system_application_list", return_value=inventory), patch.object(SystemHelmOverrideKeywords, "get_system_helm_override_show", return_value=output) as show:
        assert keywords.application_state() == ("original", "applied")
        assert keywords.user_overrides() == {"custom": "original"}
        inventory.application_exists.assert_called_once_with(app)
        show.assert_called_once_with(app, app, namespace)


@pytest.mark.parametrize("override_lines,expected", [(["image:", "  tag: stx.12.0-v3.0.0", ""], {"image": {"tag": "stx.12.0-v3.0.0"}}), (["message: |", "  first | second", "  third", ""], {"message": "first | second\nthird\n"})])
def test_nested_override_real_execution_to_parser(override_lines, expected):
    """Preserve lab-style YAML continuation rows through the real CLI reader."""
    connection = NonCallableMock()
    border = "+--------------------+--------------------------------------------------------------+"
    rows = [border, "| Property           | Value                                                        |", border]
    for key, lines in [("attributes", ["enabled: true"]), ("combined_overrides", ["None"]), ("name", ["node-interface-metrics-exporter"]), ("namespace", ["node-interface-metrics-exporter"]), ("system_overrides", ["None"]), ("user_overrides", override_lines)]:
        rows.extend(f"| {key if index == 0 else '':<18} | {line:<60} |" for index, line in enumerate(lines))
    rows.append(border)
    connection.send.return_value = [row + "\n" for row in rows]
    connection.get_return_code.return_value = 0
    keywords = SystemHelmOverrideKeywords(connection)
    assert keywords.get_user_override_values("app", "chart", "namespace") == expected
    # Every Helm caller now receives intact YAML without opting in.
    legacy = keywords.get_system_helm_override_show("app", "chart", "namespace").get_helm_override_show().get_user_overrides()
    assert yaml.safe_load(legacy) == expected


def test_override_cli_failure_is_not_an_empty_mapping():
    """Failed reads must propagate instead of replacing original overrides."""
    connection = NonCallableMock()
    connection.send.return_value = ["service unavailable"]
    connection.get_return_code.return_value = 1
    with pytest.raises(AssertionError):
        SystemHelmOverrideKeywords(connection).get_user_override_values("app", "chart", "namespace")
