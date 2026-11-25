import json
from pathlib import Path

import json5
import pytest

from config.app_upgrade_compat.objects.app_upgrade_compat_config import AppUpgradeCompatConfig
from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def _load_default_config() -> AppUpgradeCompatConfig:
    """
    Load the default application upgrade compatibility config.

    Returns:
        AppUpgradeCompatConfig: the configuration built from the shipped default file.

    """
    configuration_manager = ConfigurationManagerClass()
    configuration_manager.load_configs(ConfigurationFileLocationsManager())
    return configuration_manager.get_app_upgrade_compat_config()


def test_default_app_upgrade_compat_config():
    """
    Tests that the default application upgrade compatibility configuration is as expected.

    """
    default_config = _load_default_config()
    assert default_config is not None, "Default app upgrade compat config wasn't loaded successfully"
    assert default_config.get_to_version() == "26.10", "Target version was incorrect"


def test_custom_app_upgrade_compat_config():
    """
    Tests that we can load a custom application upgrade compatibility configuration.

    """
    custom_file = get_stx_resource_path("config/app_upgrade_compat/files/default.json5")
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_app_upgrade_compat_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_app_upgrade_compat_config()
    assert custom_config is not None, "Custom app upgrade compat config wasn't loaded successfully"
    assert custom_config.get_to_version() == "26.10", "Target version was incorrect"


@pytest.mark.parametrize("app_key", ["cert-manager", "oran-o2", "reloader"])
def test_configured_applications_resolve(app_key: str):
    """
    Tests that every configured application exposes an application name and a namespace.

    Args:
        app_key(str): the configured application key under test.

    """
    default_config = _load_default_config()
    assert default_config.get_app_name(app_key), f"Application {app_key} had no app_name"
    assert default_config.get_namespace(app_key), f"Application {app_key} had no namespace"


def test_unconfigured_application_raises():
    """
    Tests that reading an application the configuration does not carry raises rather than returning None.

    A test asking for an application that is not configured has a bug in the test, not a missing
    default, so the configuration refuses instead of handing back an empty value.

    """
    default_config = _load_default_config()
    with pytest.raises(ValueError):
        default_config.get_app_name("not-a-configured-application")
    with pytest.raises(ValueError):
        default_config.get_namespace("not-a-configured-application")


@pytest.mark.parametrize("applications", [{}, {"ipsec-policy-operator": {}}, {"ipsec-policy-operator": {"traffic_image": ""}}])
def test_missing_ipsec_image_identifies_config_setting(tmp_path, applications):
    """Missing and empty image values identify the setting to configure."""
    path = tmp_path / "app-upgrade-compat.json5"
    path.write_text(json.dumps({"applications": applications}))
    config = AppUpgradeCompatConfig(str(path))
    with pytest.raises(ValueError, match=r"applications\.ipsec-policy-operator\.traffic_image"):
        config.get_ipsec_traffic_image()


def _write_config(tmp_path: Path, applications: dict, to_version: str = "26.10") -> AppUpgradeCompatConfig:
    """Build a config object from a temporary file, so override shapes can be tested directly.

    AppUpgradeCompatConfig takes a path and opens it, so an arbitrary shape needs no fixture work.

    Args:
        tmp_path (Path): pytest's per-test temporary directory.
        applications (dict): the applications block to write.
        to_version (str): the shared target release.

    Returns:
        AppUpgradeCompatConfig: the configuration built from the written file.
    """
    config_file = tmp_path / "app_upgrade_compat.json5"
    config_file.write_text(json5.dumps({"to_version": to_version, "applications": applications}))
    return AppUpgradeCompatConfig(str(config_file))


def test_shared_target_is_returned_when_no_application_is_named():
    """The seven existing callers pass no argument and must keep getting the shared value.

    This is the regression guard for the per-application override: it has to pass both before and
    after that change, or the override has broken every other compatibility test.
    """
    assert _load_default_config().get_to_version() == "26.10", "Shared target version was incorrect"


def test_application_override_is_returned_when_present(tmp_path: Path):
    """An application carrying its own to_version targets that release, not the shared one.

    Args:
        tmp_path (Path): pytest's per-test temporary directory.
    """
    config = _write_config(tmp_path, {"reloader": {"app_name": "reloader", "namespace": "reloader", "to_version": "27.03"}})
    assert config.get_to_version("reloader") == "27.03", "Application override was not returned"


def test_shared_target_is_returned_for_an_application_without_an_override(tmp_path: Path):
    """An application with no override falls through, so the other six entries need no edit.

    Args:
        tmp_path (Path): pytest's per-test temporary directory.
    """
    config = _write_config(tmp_path, {"istio": {"app_name": "istio", "namespace": "istio-system"}})
    assert config.get_to_version("istio") == "26.10", "Fall-through to the shared target failed"


def test_blank_application_override_raises(tmp_path: Path):
    """A blank override must fail loudly rather than silently targeting the shared release.

    Silently falling through is the "looks healthy, is broken" class this whole test family exists
    to catch: the run would pass while exercising a release nobody chose.

    Args:
        tmp_path (Path): pytest's per-test temporary directory.
    """
    for blank in ("", "   "):
        config = _write_config(tmp_path, {"reloader": {"app_name": "reloader", "namespace": "reloader", "to_version": blank}})
        with pytest.raises(ValueError):
            config.get_to_version("reloader")


def test_application_override_is_stripped(tmp_path: Path):
    """Surrounding whitespace would otherwise be carried into the release comparison.

    Args:
        tmp_path (Path): pytest's per-test temporary directory.
    """
    config = _write_config(tmp_path, {"reloader": {"app_name": "reloader", "namespace": "reloader", "to_version": " 27.03 "}})
    assert config.get_to_version("reloader") == "27.03", "Override was not stripped"


def test_unconfigured_application_raises_for_the_target_too():
    """Asking for an unconfigured application is a bug in the caller, for every reader alike."""
    with pytest.raises(ValueError):
        _load_default_config().get_to_version("not-a-configured-application")
