"""Keywords for LUKS keyring security validation."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.security.luks_keyring.objects.keyring_file_info import KeyringFileInfo
from keywords.cloud_platform.security.luks_keyring.objects.keyring_file_info_output import KeyringFileInfoOutput
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager


class LuksKeyringKeywords(BaseKeyword):
    """Keywords for LUKS keyring security enhancement validation.

    Provides methods for validating the LUKS-encrypted keyring filesystem,
    file permissions, secret entropy, and cross-node synchronization.
    """

    LUKS_KEYRING_BASE = "/var/luks/stx/luks_fs/controller/.keyring"
    OLD_KEYRING_BASE = "/opt/platform/.keyring"
    LUKS_MOUNT_POINT = "/var/luks/stx/luks_fs"
    LUKS_DEVICE_NAME = "luks_encrypted_vault"
    EXPECTED_SECRET_LENGTH = 44
    EXPECTED_PERMISSIONS = "640"
    EXPECTED_OWNER = "root"
    EXPECTED_GROUP = "sys_protected"

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize LUKS keyring keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection
        self._version_manager = CloudPlatformVersionManager()

    def get_luks_keyring_path(self) -> str:
        """Get the full LUKS keyring path for current SW version.

        Returns:
            str: Full path to python_keyring directory on LUKS.
        """
        sw_version = str(self._version_manager.get_sw_version())
        return f"{self.LUKS_KEYRING_BASE}/{sw_version}/python_keyring"

    def get_old_keyring_path(self) -> str:
        """Get the old (unencrypted) keyring path for current SW version.

        Returns:
            str: Full path to old keyring directory.
        """
        sw_version = str(self._version_manager.get_sw_version())
        return f"{self.OLD_KEYRING_BASE}/{sw_version}"

    def get_keyring_file_permissions(self, file_path: str) -> KeyringFileInfo:
        """Get keyring file permissions and ownership metadata.

        Args:
            file_path (str): Path to the keyring file.

        Returns:
            KeyringFileInfo: File metadata object with permissions, owner, group.
        """
        output = self.ssh_connection.send_as_sudo(f"stat -c '%a %U %G %n' {file_path}")
        self.validate_success_return_code(self.ssh_connection)
        parsed = KeyringFileInfoOutput(output)
        return parsed.get_files()[0]

    def get_secret_length(self) -> int:
        """Get the length of the keyring secret file content.

        Returns:
            int: Number of characters in the secret.
        """
        keyring_path = self.get_luks_keyring_path()
        output = self.ssh_connection.send_as_sudo(f"cat {keyring_path}/.keyring_secret | wc -c")
        self.validate_success_return_code(self.ssh_connection)
        return int(output[0].strip())

    def get_secret_value(self) -> str:
        """Get the keyring secret value.

        Returns:
            str: The keyring secret string.
        """
        keyring_path = self.get_luks_keyring_path()
        output = self.ssh_connection.send_as_sudo(f"cat {keyring_path}/.keyring_secret")
        self.validate_success_return_code(self.ssh_connection)
        return output[0].strip()

    def credential_files_at_old_path(self) -> list[str]:
        """Find credential files at the old unencrypted keyring path.

        Returns:
            list[str]: List of credential file paths found.
        """
        old_path = self.get_old_keyring_path()
        output = self.ssh_connection.send_as_sudo(
            f"find {old_path} -name 'crypted_pass.cfg' -o -name '.keyring_secret' 2>/dev/null"
        )
        return [line.strip() for line in output if line.strip()]

    def grep_hardcoded_password(self, search_paths: list[str]) -> list[str]:
        """Search for hardcoded keyring password string in given paths.

        Args:
            search_paths (list[str]): Paths to search.

        Returns:
            list[str]: List of files containing the hardcoded password.
        """
        paths_str = " ".join(search_paths)
        output = self.ssh_connection.send_as_sudo(
            f"grep -rl 'Please set a password' {paths_str} 2>/dev/null"
        )
        return [line.strip() for line in output if line.strip()]

    def is_luks_mounted(self) -> bool:
        """Check if the LUKS filesystem is mounted.

        Returns:
            bool: True if LUKS filesystem is mounted.
        """
        output = self.ssh_connection.send(f"mount | grep {self.LUKS_MOUNT_POINT}")
        return self.ssh_connection.get_return_code() == 0

    def get_luks_device_type(self) -> str:
        """Get the LUKS device type (e.g., LUKS2).

        Returns:
            str: LUKS type string.
        """
        output = self.ssh_connection.send_as_sudo(
            f"cryptsetup status {self.LUKS_DEVICE_NAME} | grep type"
        )
        self.validate_success_return_code(self.ssh_connection)
        return output[0].strip().split(":")[1].strip()

    def get_keyring_data_root(self) -> str:
        """Get the Python keyring data root path.

        Returns:
            str: The keyring data root path.
        """
        output = self.ssh_connection.send(
            "python3 -c 'import keyring.util.platform_; print(keyring.util.platform_.data_root())'"
        )
        self.validate_success_return_code(self.ssh_connection)
        return output[0].strip()

    def services_authenticate(self) -> dict[str, bool]:
        """Check if platform services authenticate successfully via keyring.

        Returns:
            dict[str, bool]: Service name to success status mapping.
        """
        results = {}
        commands = {
            "system_host_list": "system host-list",
            "system_application_list": "system application-list",
            "fm_alarm_list": "fm alarm-list",
        }
        for name, cmd in commands.items():
            self.ssh_connection.send(source_openrc(cmd))
            results[name] = self.ssh_connection.get_return_code() == 0
        return results

    def get_keyring_error_count(self, log_path: str = "/var/log/sysinv.log") -> int:
        """Count keyring-related errors in a log file.

        Args:
            log_path (str): Path to log file.

        Returns:
            int: Number of keyring error lines.
        """
        output = self.ssh_connection.send_as_sudo(
            f"grep -ic 'keyring.*error\\|keyring.*fail' {log_path} 2>/dev/null || echo 0"
        )
        return int(output[0].strip())
