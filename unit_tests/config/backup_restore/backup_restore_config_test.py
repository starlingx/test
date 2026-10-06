import pytest

from config.backup_restore.objects.onsite_restore_config import OnsiteRestoreConfig
from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_default_backup_restore_config():
    """
    Tests that the default backup restore configuration is as expected.
    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)

    default_config = configuration_manager.get_backup_restore_config()
    assert default_config is not None, "Default backup restore config wasn't loaded successfully"
    assert default_config.get_local_backup_base_path() == "/tmp/bnr", "Default local backup base path should be /tmp/bnr"


def test_default_onsite_restore_config():
    """
    Tests that the default onsite restore (nested) configuration is as expected.
    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)

    onsite_config = configuration_manager.get_backup_restore_config().get_onsite_restore_config()
    assert onsite_config is not None, "Default onsite restore config wasn't loaded successfully"
    assert onsite_config.get_seed_stage_path() == "/home/sysadmin/onsite-restore-seed", "Default seed stage path is incorrect"
    assert onsite_config.get_www_iso_base_path() == "/var/www/pages/iso", "Default www iso base path is incorrect"
    assert onsite_config.get_default_restore_timeout() == 5400, "Default restore timeout should be 5400"
    assert onsite_config.get_available_versions() == ["26.10"], "Only 26.10 should be supported by default"


def test_default_onsite_restore_resolves_without_base_url_raises():
    """Tests that resolving with no release_base_url configured fails fast with ValueError."""
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)

    onsite_config = configuration_manager.get_backup_restore_config().get_onsite_restore_config()
    assert onsite_config.get_release_base_url() == "", "Default release_base_url should be empty (supplied by a non-public config file)"
    assert onsite_config.get_ssl_ca_cert_name() == "", "Default ssl_ca_cert_name should be empty (no CA install by default)"
    assert onsite_config.get_sc_https_iso_port() == 8443, "Default SC HTTPS ISO port should be 8443"
    with pytest.raises(ValueError):
        onsite_config.resolve_nocloud_tarball_url("26.10")


def test_default_onsite_restore_unsupported_version_raises():
    """
    Tests that an unsupported load fails fast with a KeyError (feature not supported).
    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)

    onsite_config = configuration_manager.get_backup_restore_config().get_onsite_restore_config()
    with pytest.raises(KeyError):
        onsite_config.resolve_nocloud_tarball_url("26.03")


def test_custom_backup_restore_config():
    """Tests loading a custom backup restore config.

    Includes the nested onsite restore section and per-entry tarball_url override.
    """
    custom_file = get_stx_resource_path("unit_tests/config/backup_restore/custom_backup_restore_config.json5")
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_backup_restore_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_backup_restore_config()
    assert custom_config.get_local_backup_base_path() == "/custom/bnr", "Custom local backup base path isn't loaded correctly"

    onsite_config = custom_config.get_onsite_restore_config()
    assert onsite_config.get_seed_stage_path() == "/home/testadmin/custom-seed", "Custom seed stage path isn't loaded correctly"
    assert onsite_config.get_www_iso_base_path() == "/custom/www/iso", "Custom www iso base path isn't loaded correctly"
    assert onsite_config.get_default_restore_timeout() == 1234, "Custom restore timeout isn't loaded correctly"

    # Resolved from release_base_url + template.
    resolved = onsite_config.resolve_nocloud_tarball_url("26.10")
    assert resolved == "http://custom-builds.example.com/builds/wrcp/master/trixie/amd64/wrcp-trixie-master-debian/latest_build/export/windshare/custom-nocloud.tar", "Custom resolved URL is incorrect"

    # Explicit per-entry tarball_url override takes precedence over the template.
    overridden = onsite_config.resolve_nocloud_tarball_url("27.03")
    assert overridden == "http://override.example.com/pinned-nocloud.tar", "Explicit tarball_url override should take precedence"


def test_onsite_restore_prefix_match_prefers_longest_key():
    """Tests that a reported version matches the longest (most specific) registry key.

    With two registry keys where one is a string-prefix of the other ('26.1' and
    '26.10'), a reported '26.10-90' must resolve to the '26.10' entry, not '26.1',
    regardless of insertion order.
    """
    onsite_config = OnsiteRestoreConfig(
        {
            "release_base_url": "http://builds.example.com/builds/wrcp",
            "versions": {
                "26.1": {"branch": "r1", "distro": "trixie"},
                "26.10": {"branch": "r10", "distro": "trixie"},
            },
        }
    )
    resolved = onsite_config.resolve_nocloud_tarball_url("26.10-90")
    assert "/r10/" in resolved, "26.10-90 must resolve to the longest-matching key (26.10 -> branch r10)"
    assert "/r1/" not in resolved, "26.10-90 must not resolve to the shorter prefix key (26.1)"


def test_onsite_restore_entry_defaults_branch_and_distro():
    """Tests that a versions entry omitting branch/distro falls back to master/trixie."""
    onsite_config = OnsiteRestoreConfig(
        {
            "release_base_url": "http://builds.example.com/builds/wrcp",
            "versions": {"26.10": {}},
        }
    )
    resolved = onsite_config.resolve_nocloud_tarball_url("26.10")
    assert resolved == "http://builds.example.com/builds/wrcp/master/trixie/amd64/wrcp-trixie-master-debian/latest_build/export/windshare/nocloud-factory-install.tar", "Entry omitting branch/distro should default to master/trixie"
