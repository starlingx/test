import json
import shlex

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc

SYSTEM_CONTROLLER_REGION = "SystemController"


class OpenstackUserSetKeywords(BaseKeyword):
    """Keywords for changing Keystone user options in the System Controller region."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the System Controller active controller.
        """
        self.ssh_connection = ssh_connection

    def set_user_ignore_password_expiry(self, username: str, enabled: bool) -> str:
        """Set or clear the ``ignore_password_expiry`` Keystone user option.

        Runs ``openstack --os-region-name SystemController user set <user> --ignore-password-expiry``
        when ``enabled`` is True, or ``--no-ignore-password-expiry`` when it is False. Setting the
        option writes a row to the Keystone ``user_option`` table, which dcorch then syncs to the
        subclouds.

        Args:
            username (str): Name or ID of the user to change.
            enabled (bool): True to set the option, False to clear it.

        Returns:
            str: Command output.
        """
        flag = "--ignore-password-expiry" if enabled else "--no-ignore-password-expiry"
        cmd = f"openstack --os-region-name {SYSTEM_CONTROLLER_REGION} user set {shlex.quote(username)} {flag}"
        output = self.ssh_connection.send(source_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)

        return "\n".join(output) if isinstance(output, list) else str(output)

    def get_user_ignore_password_expiry(self, username: str) -> bool:
        """Get the current value of the ``ignore_password_expiry`` Keystone user option.

        Args:
            username (str): Name or ID of the user to read.

        Returns:
            bool: True if the option is set, False if it is cleared or was never set.

        Raises:
            KeywordException: If the command output cannot be parsed as the user's options.
        """
        cmd = f"openstack --os-region-name {SYSTEM_CONTROLLER_REGION} user show {shlex.quote(username)} -f json -c options"
        output = self.ssh_connection.send(source_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)

        raw_output = "\n".join(output) if isinstance(output, list) else str(output)
        try:
            options = json.loads(raw_output).get("options")
        except (ValueError, AttributeError) as error:
            raise KeywordException(f"Could not parse the options of user '{username}' from: {raw_output!r}") from error

        if not isinstance(options, dict):
            return False
        return options.get("ignore_password_expiry") is True
