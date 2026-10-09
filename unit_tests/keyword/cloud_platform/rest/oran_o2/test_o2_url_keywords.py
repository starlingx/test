"""Unit tests for O2 IMS URL construction across both API namespaces.

Verifies that the controller-local builders place the namespace prefix and the
endpoint suffix correctly for both the inventory and the monitoring namespace, that
a leading slash on the suffix is tolerated, and that the two namespaces cannot
collapse onto the same URL now that one parameterised builder serves both.

This is lab-free. The controller-local builders resolve to the controller's own
loopback, so no lab address is involved, and the port is read back through the
configuration getter rather than written as a literal.
"""

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from keywords.cloud_platform.rest.oran_o2.o2_url_keywords import GetO2UrlKeywords


def _build_url_keywords() -> GetO2UrlKeywords:
    """Load the configuration and build the O2 URL keywords.

    GetO2UrlKeywords reads the O2 IMS config and the lab config in its constructor,
    so the configuration must be loaded before it is built.

    Returns:
        GetO2UrlKeywords: URL keywords ready to build endpoint URLs.
    """
    ConfigurationManager.load_configs(ConfigurationFileLocationsManager())
    return GetO2UrlKeywords()


def _get_local_base_url() -> str:
    """Return the expected controller-local base URL, with the port read from config.

    Returns:
        str: The expected base URL, e.g. https://localhost:30205.
    """
    port = ConfigurationManager.get_o2ims_config().get_served_port()
    return f"https://localhost:{port}"


def test_local_monitoring_endpoint_url_carries_the_monitoring_namespace():
    """A monitoring suffix is placed under the monitoring namespace prefix."""
    url_keywords = _build_url_keywords()

    observed = url_keywords.get_local_monitoring_endpoint_url("v1/alarms")

    assert observed == f"{_get_local_base_url()}/o2ims-infrastructureMonitoring/v1/alarms"


def test_local_inventory_endpoint_url_carries_the_inventory_namespace():
    """An inventory suffix is placed under the inventory namespace prefix.

    The inventory builder is covered alongside the monitoring one because both now
    route through the same parameterised private builder, so a regression in that
    builder would affect both.
    """
    url_keywords = _build_url_keywords()

    observed = url_keywords.get_local_inventory_endpoint_url("v1/resourcePools")

    assert observed == f"{_get_local_base_url()}/o2ims-infrastructureInventory/v1/resourcePools"


def test_leading_slash_on_the_suffix_is_tolerated():
    """A suffix with a leading slash yields the same URL as one without."""
    url_keywords = _build_url_keywords()

    with_slash = url_keywords.get_local_monitoring_endpoint_url("/v1/alarms")
    without_slash = url_keywords.get_local_monitoring_endpoint_url("v1/alarms")

    assert with_slash == without_slash
    assert "//v1/alarms" not in with_slash


def test_the_two_namespaces_do_not_collapse_onto_the_same_url():
    """The same suffix under each namespace yields two different URLs.

    Guards the parameterised builder against a regression that ignored the namespace
    argument and defaulted to one prefix for both callers.
    """
    url_keywords = _build_url_keywords()

    inventory_url = url_keywords.get_local_inventory_endpoint_url("v1/alarms")
    monitoring_url = url_keywords.get_local_monitoring_endpoint_url("v1/alarms")

    assert inventory_url != monitoring_url
    assert "o2ims-infrastructureInventory" in inventory_url
    assert "o2ims-infrastructureMonitoring" in monitoring_url


def test_monitoring_alarm_subscriptions_suffix_is_placed_correctly():
    """A nested monitoring suffix is appended after the namespace prefix."""
    url_keywords = _build_url_keywords()

    observed = url_keywords.get_local_monitoring_endpoint_url("v1/alarmSubscriptions")

    assert observed.endswith("/o2ims-infrastructureMonitoring/v1/alarmSubscriptions")


def test_a_single_query_parameter_is_appended():
    """A single key/value parameter is appended after a '?'."""
    url_keywords = _build_url_keywords()

    observed = url_keywords.get_local_inventory_endpoint_url("v1/deploymentManagers", {"nextpage_opaque_marker": "1"})

    assert observed == f"{_get_local_base_url()}/o2ims-infrastructureInventory/v1/deploymentManagers?nextpage_opaque_marker=1"


def test_two_query_parameters_are_joined_with_ampersand():
    """Two parameters are joined with '&' in insertion order."""
    url_keywords = _build_url_keywords()

    observed = url_keywords.get_local_inventory_endpoint_url("v1/deploymentManagers", {"all_fields": "true", "nextpage_opaque_marker": "1"})

    assert observed.endswith("/v1/deploymentManagers?all_fields=true&nextpage_opaque_marker=1")


def test_query_parameter_values_are_encoded():
    """A value with reserved characters is percent-encoded."""
    url_keywords = _build_url_keywords()

    observed = url_keywords.get_local_inventory_endpoint_url("v1/deploymentManagers", {"marker": "a b&c"})

    assert observed.endswith("/v1/deploymentManagers?marker=a%20b%26c")
