"""Unit tests for OpenstackUserSetKeywords.

The keywords set, clear and read the Keystone ignore_password_expiry user option in the System
Controller region. These tests check the exact commands sent over SSH and the parsing of the
user's options.
"""

import unittest
from unittest.mock import NonCallableMagicMock, patch

from framework.exceptions.keyword_exception import KeywordException
from keywords.openstack.openstack.user.openstack_user_set_keywords import OpenstackUserSetKeywords

OPENRC = "source /etc/platform/openrc;"


class TestOpenstackUserSetKeywords(unittest.TestCase):
    """Test suite for OpenstackUserSetKeywords."""

    def setUp(self):
        """Silence the BaseKeyword logger and build the keywords with a mocked SSH connection."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()
        # NonCallableMagicMock: BaseKeyword wraps callable attributes, which breaks a plain MagicMock.
        self.ssh_connection = NonCallableMagicMock()
        self.ssh_connection.get_return_code.return_value = 0
        self.keywords = OpenstackUserSetKeywords(self.ssh_connection)

    def tearDown(self):
        """Stop the logger patcher."""
        self.logger_patcher.stop()

    def _sent_command(self) -> str:
        """Return the single command passed to ssh_connection.send.

        Returns:
            str: the command string.
        """
        self.ssh_connection.send.assert_called_once()
        return self.ssh_connection.send.call_args.args[0]

    def test_set_enabled_command(self):
        """Enabling sends the System Controller region command with --ignore-password-expiry."""
        self.ssh_connection.send.return_value = [""]
        self.keywords.set_user_ignore_password_expiry("admin", True)
        self.assertEqual(self._sent_command(), f"{OPENRC}openstack --os-region-name SystemController user set admin --ignore-password-expiry")

    def test_set_disabled_command(self):
        """Disabling sends --no-ignore-password-expiry."""
        self.ssh_connection.send.return_value = [""]
        self.keywords.set_user_ignore_password_expiry("admin", False)
        self.assertEqual(self._sent_command(), f"{OPENRC}openstack --os-region-name SystemController user set admin --no-ignore-password-expiry")

    def test_set_quotes_username(self):
        """A username with shell metacharacters is quoted."""
        self.ssh_connection.send.return_value = [""]
        self.keywords.set_user_ignore_password_expiry("a b;id", True)
        self.assertIn("user set 'a b;id' --ignore-password-expiry", self._sent_command())

    def test_set_fails_on_non_zero_return_code(self):
        """A non-zero return code from the command fails the keyword."""
        self.ssh_connection.send.return_value = ["error"]
        self.ssh_connection.get_return_code.return_value = 1
        with self.assertRaises(AssertionError):
            self.keywords.set_user_ignore_password_expiry("admin", True)

    def test_get_command(self):
        """Reading sends a user show for the options column in the System Controller region."""
        self.ssh_connection.send.return_value = ['{"options": {}}']
        self.keywords.get_user_ignore_password_expiry("admin")
        self.assertEqual(self._sent_command(), f"{OPENRC}openstack --os-region-name SystemController user show admin -f json -c options")

    def test_get_true_when_option_set(self):
        """The option reads as True when Keystone reports it as true."""
        self.ssh_connection.send.return_value = ["{\r\n", '  "options": {"ignore_password_expiry": true}\r\n', "}\r\n"]
        self.assertTrue(self.keywords.get_user_ignore_password_expiry("admin"))

    def test_get_false_when_option_false(self):
        """The option reads as False when Keystone reports it as false."""
        self.ssh_connection.send.return_value = ['{"options": {"ignore_password_expiry": false}}']
        self.assertFalse(self.keywords.get_user_ignore_password_expiry("admin"))

    def test_get_false_when_options_empty(self):
        """The option reads as False when the user has no options."""
        self.ssh_connection.send.return_value = ['{"options": {}}']
        self.assertFalse(self.keywords.get_user_ignore_password_expiry("admin"))

    def test_get_false_when_options_null(self):
        """The option reads as False when options is null."""
        self.ssh_connection.send.return_value = ['{"options": null}']
        self.assertFalse(self.keywords.get_user_ignore_password_expiry("admin"))

    def test_get_raises_on_unparsable_output(self):
        """Output that is not JSON raises."""
        self.ssh_connection.send.return_value = ["Missing parameter(s)"]
        with self.assertRaises(KeywordException):
            self.keywords.get_user_ignore_password_expiry("admin")


if __name__ == "__main__":
    unittest.main()
