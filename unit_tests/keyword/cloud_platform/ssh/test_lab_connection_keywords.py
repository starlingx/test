"""Unit tests for the lab config used by LabConnectionKeywords."""

from typing import Optional
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

MODULE = "keywords.cloud_platform.ssh.lab_connection_keywords"


def build_lab_config(floating_ip: str, jump_host: Optional[MagicMock] = None) -> NonCallableMagicMock:
    """Build a lab config mock.

    The mock is not callable, like a real LabConfig. BaseKeyword wraps every
    callable attribute of a keyword in its logging hook, so a callable mock stored
    on the keyword would be returned wrapped instead of as the lab config.

    Args:
        floating_ip (str): Floating IP the lab config reports.
        jump_host (Optional[MagicMock]): Jump host configuration the lab config reports.
            Defaults to None, which means the lab config does not use a jump server.

    Returns:
        NonCallableMagicMock: Lab config mock.
    """
    lab_config = NonCallableMagicMock()
    lab_config.get_floating_ip.return_value = floating_ip
    lab_config.is_use_jump_server.return_value = jump_host is not None
    lab_config.get_jump_host_configuration.return_value = jump_host
    lab_config.get_admin_credentials.return_value.get_user_name.return_value = "admin-user"
    lab_config.get_admin_credentials.return_value.get_password.return_value = "admin-password"
    lab_config.get_ssh_port.return_value = 22
    return lab_config


def test_get_active_controller_ssh_defaults_to_primary_lab():
    """Without a lab config, the primary lab config is used, as before."""
    primary_lab = build_lab_config("192.0.2.10")

    with patch("keywords.base_keyword.get_logger"), patch(f"{MODULE}.ConfigurationManager") as configuration_manager, patch(f"{MODULE}.SSHConnectionManager") as ssh_manager:
        configuration_manager.get_lab_config.return_value = primary_lab
        LabConnectionKeywords().get_active_controller_ssh()

    ssh_manager.create_ssh_connection.assert_called_once_with("192.0.2.10", "admin-user", "admin-password", ssh_port=22, jump_host=None)


def test_primary_lab_config_is_read_when_the_method_runs():
    """Without a lab config, the primary lab config is read on each call, not when the instance is created."""
    primary_lab = build_lab_config("192.0.2.10")

    with patch("keywords.base_keyword.get_logger"), patch(f"{MODULE}.ConfigurationManager") as configuration_manager, patch(f"{MODULE}.SSHConnectionManager") as ssh_manager:
        keywords = LabConnectionKeywords()
        configuration_manager.get_lab_config.assert_not_called()
        configuration_manager.get_lab_config.return_value = primary_lab
        keywords.get_active_controller_ssh()

    ssh_manager.create_ssh_connection.assert_called_once_with("192.0.2.10", "admin-user", "admin-password", ssh_port=22, jump_host=None)


def test_get_active_controller_ssh_uses_the_given_lab_config():
    """With a lab config, its floating IP is used and the primary lab config is not read."""
    other_lab = build_lab_config("192.0.2.20")

    with patch("keywords.base_keyword.get_logger"), patch(f"{MODULE}.ConfigurationManager") as configuration_manager, patch(f"{MODULE}.SSHConnectionManager") as ssh_manager:
        LabConnectionKeywords(other_lab).get_active_controller_ssh()

    configuration_manager.get_lab_config.assert_not_called()
    ssh_manager.create_ssh_connection.assert_called_once_with("192.0.2.20", "admin-user", "admin-password", ssh_port=22, jump_host=None)


def test_get_active_controller_ssh_uses_the_jump_host_of_the_given_lab_config():
    """With a lab config that uses a jump server, that lab's jump host is used, not the primary lab's."""
    primary_jump_host = MagicMock(name="primary_jump_host")
    other_jump_host = MagicMock(name="other_jump_host")
    primary_lab = build_lab_config("192.0.2.10", jump_host=primary_jump_host)
    other_lab = build_lab_config("192.0.2.20", jump_host=other_jump_host)

    with patch("keywords.base_keyword.get_logger"), patch(f"{MODULE}.ConfigurationManager") as configuration_manager, patch(f"{MODULE}.SSHConnectionManager") as ssh_manager:
        configuration_manager.get_lab_config.return_value = primary_lab
        LabConnectionKeywords(other_lab).get_active_controller_ssh()

    primary_lab.get_jump_host_configuration.assert_not_called()
    ssh_manager.create_ssh_connection.assert_called_once_with("192.0.2.20", "admin-user", "admin-password", ssh_port=22, jump_host=other_jump_host)


def test_other_methods_use_the_given_lab_config():
    """The lab config given to the constructor applies to every method, not only get_active_controller_ssh()."""
    other_lab = build_lab_config("192.0.2.20")
    other_lab.get_node.return_value.get_type.return_value = "controller"
    other_lab.get_node.return_value.get_ip.return_value = "192.0.2.21"

    with patch("keywords.base_keyword.get_logger"), patch(f"{MODULE}.ConfigurationManager") as configuration_manager, patch(f"{MODULE}.SSHConnectionManager") as ssh_manager:
        LabConnectionKeywords(other_lab).get_ssh_for_hostname("controller-1")

    configuration_manager.get_lab_config.assert_not_called()
    other_lab.get_node.assert_called_once_with("controller-1")
    ssh_manager.create_ssh_connection.assert_called_once_with("192.0.2.21", "admin-user", "admin-password", name="controller-1", ssh_port=22, jump_host=None)
