"""Keywords for validating permissions on /etc/platform/platform.conf.

Backs the platform.conf permission-hardening regression test: the fix removes
the world-readable ``other`` bit from ``/etc/platform/platform.conf`` and
scopes group read to the ``sys_protected`` group, closing the
information-disclosure path by which an unprivileged local user could harvest
the host UUID.

Expected state on a fixed load:
    mode         : 640
    owner:group  : root:sys_protected
    other read   : cleared
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.luks_keyring.objects.keyring_file_info import KeyringFileInfo
from keywords.cloud_platform.security.luks_keyring.objects.keyring_file_info_output import KeyringFileInfoOutput


class PlatformConfPermissionKeywords(BaseKeyword):
    """Read and interpret the permissions of /etc/platform/platform.conf."""

    PLATFORM_CONF_PATH = "/etc/platform/platform.conf"
    EXPECTED_MODE = "640"
    EXPECTED_OWNER = "root"
    EXPECTED_GROUP = "sys_protected"

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_platform_conf_file_info(self) -> KeyringFileInfo:
        """Return the mode/owner/group/path of platform.conf.

        Runs ``stat -c '%a %U %G %n'`` and parses the result with the shared
        file-stat output parser, returning a KeyringFileInfo object exposing
        ``get_permissions``, ``get_owner``, ``get_group`` and
        ``has_world_access``.

        Returns:
            KeyringFileInfo: Parsed metadata for platform.conf.
        """
        output = self.ssh_connection.send_as_sudo(f"stat -c '%a %U %G %n' {self.PLATFORM_CONF_PATH}")
        file_info = KeyringFileInfoOutput(output).get_file(self.PLATFORM_CONF_PATH)
        get_logger().log_info(f"platform.conf: mode={file_info.get_permissions()} owner={file_info.get_owner()} group={file_info.get_group()}")
        return file_info
