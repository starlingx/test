"""Keywords for managing local (non-LDAP) Linux user accounts.

Used by permission / privilege-escalation tests that need a genuinely
unprivileged local user — a member of the ``users`` group only and
explicitly NOT a member of ``sys_protected`` — to prove that a protected
file is unreadable by a regular user.

This is deliberately distinct from ``LdapKeywords``: LDAP users on
StarlingX are provisioned into the ``sys_protected`` group, which would be
able to read group-readable protected files and therefore invalidate an
unprivileged-access test.
"""

from typing import Union

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class LinuxUserKeywords(BaseKeyword):
    """Create and remove local Linux users via useradd / userdel."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def normalise_output(self, output: Union[str, list]) -> str:
        """Normalise command output (str or list of lines) to a single string.

        Args:
            output (Union[str, list]): Raw output from an SSHConnection send call.

        Returns:
            str: The output joined into a single string.
        """
        if isinstance(output, list):
            return "\n".join(output)
        return output if output is not None else ""

    def user_exists(self, username: str) -> bool:
        """Check whether a local user account exists.

        Args:
            username (str): The username to check.

        Returns:
            bool: True if the user exists in the local passwd database.
        """
        self.ssh_connection.send(f"getent passwd {username}")
        exists = self.ssh_connection.get_return_code() == 0
        get_logger().log_info(f"Local user '{username}' exists: {exists}")
        return exists

    def create_unprivileged_user(self, username: str) -> None:
        """Create a minimal unprivileged local user.

        The user is created with its own primary group and no supplementary
        groups, so it is NOT a member of ``sys_protected`` and has no sudo
        rights. Idempotent: an existing user of the same name is removed first.

        Args:
            username (str): The username to create.
        """
        get_logger().log_info(f"Creating unprivileged local user '{username}'")
        if self.user_exists(username):
            self.delete_user(username)
        self.ssh_connection.send_as_sudo(f"useradd -m -s /bin/bash {username}")
        self.validate_success_return_code(self.ssh_connection)

    def is_user_in_group(self, username: str, group_name: str) -> bool:
        """Check whether a user is a member of the given group.

        Args:
            username (str): The username to query.
            group_name (str): The group name to check membership of.

        Returns:
            bool: True if the user belongs to the group, False otherwise.
        """
        output = self.ssh_connection.send_as_sudo(f"id {username}")
        groups = self.normalise_output(output).strip()
        is_member = group_name in groups
        get_logger().log_info(f"User '{username}' member of '{group_name}': {is_member}")
        return is_member

    def can_user_read_file(self, username: str, file_path: str) -> bool:
        """Return whether the unprivileged user can read the file.

        Runs ``sudo -u <username> cat <file_path>`` so the read happens with
        the target user's own permissions (no privilege elevation), then
        inspects the output for an access-denial message.

        Args:
            username (str): The user to read as.
            file_path (str): The absolute path of the file to read.

        Returns:
            bool: True if the file is readable by the user, False if the read
            was denied.
        """
        output = self.ssh_connection.send_as_sudo(f"-u {username} cat {file_path} 2>&1")
        text = self.normalise_output(output).strip()
        denied = "Permission denied" in text or "No such file" in text
        get_logger().log_info(f"User '{username}' can read '{file_path}': {not denied}")
        return not denied

    def delete_user(self, username: str) -> None:
        """Remove a local user and its home directory.

        Safe to call even if the user does not exist.

        Args:
            username (str): The username to delete.
        """
        get_logger().log_info(f"Deleting local user '{username}'")
        self.ssh_connection.send_as_sudo(f"userdel -r {username}")
