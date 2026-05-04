import json5
import os
import tempfile

import pytest

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from config.database.objects.database_config import DatabaseConfig
from framework.resources.resource_finder import get_stx_resource_path


def test_default_database_config():
    """
    Tests that the default database configuration is as expected.
    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_database_config()
    assert default_config is not None, "Default database config wasn't loaded successfully"
    assert not default_config.use_database(), "Use database value is incorrect."
    assert default_config.get_database_names() == ['default'], "Database names are incorrect."
    assert default_config.get_default_database_name() == 'default', "Default database name is incorrect."

    default_entry = default_config.get_default_database_entry()
    assert default_entry.get_host_name() == "fake_host_name", "Host name is incorrect."
    assert default_entry.get_db_name() == "fake_db_name", "DB name is incorrect."
    assert default_entry.get_db_port() == 5432, "DB Port is incorrect"
    assert default_entry.get_user_name() == "fake_user", "User name is incorrect"
    assert default_entry.get_password() == "fakePassword$", "Password is incorrect."


def test_custom_database_config():
    """
    Tests that we can load a custom database configuration.
    """
    custom_file = get_stx_resource_path('unit_tests/config/database/custom_database_config.json5')
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_database_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_database_config()
    assert custom_config is not None, "Custom database config wasn't loaded successfully"
    assert custom_config.use_database(), "Use database value is incorrect."
    assert custom_config.get_database_names() == ['default'], "Single-database config should have one entry named 'default'."
    assert custom_config.get_default_database_name() == 'default', "Default database name should be 'default'."

    custom_entry = custom_config.get_default_database_entry()
    assert custom_entry.get_host_name() == "custom_host_name", "Host name is incorrect."
    assert custom_entry.get_db_name() == "custom_db_name", "DB name is incorrect."
    assert custom_entry.get_db_port() == 5432, "DB Port is incorrect"
    assert custom_entry.get_user_name() == "custom_user", "User name is incorrect"
    assert custom_entry.get_password() == "customPassword$", "Password is incorrect."


def test_multi_database_config():
    """
    Tests that we can load a multi-database configuration and access each database by name.
    """
    multi_file = get_stx_resource_path('unit_tests/config/database/multi_database_config.json5')
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_database_config_file(multi_file)
    configuration_manager.load_configs(config_file_locations)

    multi_config = configuration_manager.get_database_config()
    assert multi_config is not None, "Multi database config wasn't loaded successfully"
    assert multi_config.use_database(), "Use database value is incorrect."
    assert sorted(multi_config.get_database_names()) == ['default', 'reporting'], "Database names are incorrect."
    assert multi_config.get_default_database_name() == 'default', "Default database name is incorrect."

    # Default entry should resolve to 'main'
    default_entry = multi_config.get_default_database_entry()
    assert default_entry.get_host_name() == "default_host", "Default host name is incorrect."
    assert default_entry.get_db_name() == "default_db", "Default db name is incorrect."
    assert default_entry.get_db_port() == 5432, "Default db port is incorrect."
    assert default_entry.get_user_name() == "default_user", "Default user name is incorrect."
    assert default_entry.get_password() == "defaultPassword$", "Default password is incorrect."

    # get_database_entry returns a scoped DatabaseEntry
    reporting_entry = multi_config.get_database_entry('reporting')
    assert reporting_entry.get_host_name() == "reporting_host", "Reporting host name is incorrect."
    assert reporting_entry.get_db_name() == "reporting_db", "Reporting db name is incorrect."
    assert reporting_entry.get_db_port() == 5433, "Reporting db port is incorrect."
    assert reporting_entry.get_user_name() == "reporting_user", "Reporting user name is incorrect."
    assert reporting_entry.get_password() == "reportingPassword$", "Reporting password is incorrect."

    # Explicit 'main' entry should match the default
    main_entry = multi_config.get_database_entry('default')
    assert main_entry.get_host_name() == "default_host", "Explicit default host name is incorrect."


def test_get_database_entry_nonexistent_raises_key_error():
    """
    Tests that requesting a non-existent database entry raises KeyError.
    """
    custom_file = get_stx_resource_path('unit_tests/config/database/custom_database_config.json5')
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_database_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_database_config()
    with pytest.raises(KeyError, match="nonexistent"):
        custom_config.get_database_entry('nonexistent')


def test_invalid_default_database_name():
    """
    Tests that a config with a default_database pointing to a non-existent entry raises ValueError.
    """
    config = {
        'use_database': True,
        'default_database': 'nonexistent',
        'databases': {
            'main': {
                'host_name': 'h',
                'db_name': 'd',
                'db_port': 5432,
                'user_name': 'u',
                'password': 'p',
            },
        },
    }
    fd, path = tempfile.mkstemp(suffix='.json5')
    try:
        with os.fdopen(fd, 'w') as f:
            json5.dump(config, f)
        with pytest.raises(ValueError, match="nonexistent"):
            DatabaseConfig(path)
    finally:
        os.unlink(path)


def test_missing_entry_fields():
    """
    Tests that a config with a database entry missing required fields raises ValueError.
    """
    config = {
        'use_database': True,
        'default_database': 'default',
        'databases': {
            'default': {
                'host_name': 'h',
                # missing db_name, db_port, user_name, password
            },
        },
    }
    fd, path = tempfile.mkstemp(suffix='.json5')
    try:
        with os.fdopen(fd, 'w') as f:
            json5.dump(config, f)
        with pytest.raises(ValueError, match="missing required fields"):
            DatabaseConfig(path)
    finally:
        os.unlink(path)
