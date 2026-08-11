"""Base keywords for running CLI commands as an OIDC-authenticated user.

Provides shared session management (SSH as LDAP user, oidc-auth, source
local_starlingxrc oidc) used by system, software, and sw-manager OIDC tests.
Subclass and override build_command() for CLI-specific behavior.
"""

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.oidc.oidc_command_result import OidcCommandResult


class OidcCliKeywords(BaseKeyword):
    """Base class for running CLI commands as an OIDC-authenticated user.

    Handles:
    - SSH session as LDAP user
    - kubeconfig-setup, oidc-auth, source local_starlingxrc oidc
    - Session caching and cleanup

    Subclasses override build_command() for CLI-specific command construction.
    """

    def __init__(self, ssh_connection: SSHConnection, cli_name: str = "cli") -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
            cli_name (str): CLI name for logging (e.g. 'system', 'software', 'sw-manager').
        """
        self.ssh_connection = ssh_connection
        self.cli_name = cli_name
        self.ldap_ssh: SSHConnection = None
        self.authenticated_user: str = None

    def get_authenticated_session(
        self,
        username: str,
        password: str,
        lab_oam_ip: str,
    ) -> SSHConnection:
        """Create and authenticate an OIDC session for the given user.

        Reuses existing session if already authenticated as the same user.

        Args:
            username (str): LDAP username for SSH login.
            password (str): Password for SSH and OIDC authentication.
            lab_oam_ip (str): Lab OAM IP address for SSH connection.

        Returns:
            SSHConnection: Authenticated SSH session ready for CLI commands.

        Raises:
            KeywordException: If SSH or oidc-auth fails.
        """
        if self.ldap_ssh and self.authenticated_user == username:
            return self.ldap_ssh

        if self.ldap_ssh:
            self.ldap_ssh.close()

        get_logger().log_info(f"Creating OIDC session for {username}")
        self.ldap_ssh = self._create_ldap_ssh(username, password, lab_oam_ip)
        self.authenticated_user = username

        if not self.ldap_ssh.is_connected:
            self.ldap_ssh = None
            self.authenticated_user = None
            raise KeywordException(f"SSH connection as {username}@{lab_oam_ip} failed — authentication error")

        self.ldap_ssh.send("kubeconfig-setup")
        self.ldap_ssh.send("source ~/.profile")

        output = self.ldap_ssh.send(f"oidc-auth -p {password}")
        raw = "\n".join(output) if isinstance(output, list) else output
        if "Login succeeded" not in raw:
            raise KeywordException(f"oidc-auth failed for user {username}: {raw[:200]}")

        self.ldap_ssh.send(f"source local_starlingxrc oidc <<< '{password}'")

        return self.ldap_ssh

    def build_command(self, command: str, password: str = "") -> str:
        """Build the full command with OIDC auth type.

        Override in subclasses for CLI-specific command construction.

        Args:
            command (str): The CLI command (e.g. 'system host-list').
            password (str): User password (needed by some CLIs for OS_PASSWORD).

        Returns:
            str: Full command string ready for execution.
        """
        raise NotImplementedError("Subclasses must implement build_command()")

    def run_command_as_oidc_user(
        self,
        username: str,
        password: str,
        lab_oam_ip: str,
        command: str,
        timeout_sec: int = 120,
    ) -> OidcCommandResult:
        """Run a CLI command as an OIDC-authenticated user.

        Args:
            username (str): LDAP username.
            password (str): User password.
            lab_oam_ip (str): Lab OAM IP address.
            command (str): CLI command to execute.
            timeout_sec (int): Command timeout in seconds.

        Returns:
            OidcCommandResult: Parsed command result with success/failure status.
        """
        ldap_ssh = self.get_authenticated_session(username, password, lab_oam_ip)
        combined = self.build_command(command, password)
        get_logger().log_info(f"Running {self.cli_name} command: {command}")
        output = ldap_ssh.send(combined, command_timeout=timeout_sec)
        raw_output = "\n".join(output) if isinstance(output, list) else output
        return_code = ldap_ssh.get_return_code()
        return OidcCommandResult(command, raw_output, return_code)

    def close_session(self) -> None:
        """Close the OIDC SSH session and clear cached state."""
        if self.ldap_ssh:
            self.ldap_ssh.close()
            self.ldap_ssh = None
            self.authenticated_user = None

    def get_ldap_ssh(self) -> SSHConnection:
        """Get the current LDAP SSH session.

        Returns:
            SSHConnection: The authenticated LDAP SSH connection, or None if not connected.
        """
        return self.ldap_ssh

    def _create_ldap_ssh(self, username: str, password: str, lab_oam_ip: str) -> SSHConnection:
        """Create a direct SSH connection as the LDAP user.

        Args:
            username (str): LDAP username.
            password (str): User password.
            lab_oam_ip (str): Lab OAM IP address.

        Returns:
            SSHConnection: SSH connection to the lab as the LDAP user.
        """
        lab_config = ConfigurationManager.get_lab_config()
        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        get_logger().log_info(f"Creating SSH connection as LDAP user {username}@{lab_oam_ip}")
        return SSHConnectionManager.create_ssh_connection(
            lab_oam_ip,
            username,
            password,
            name=f"oidc-{self.cli_name}-{username}",
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )

    def corrupt_cached_oidc_token(self) -> None:
        """Corrupt the OIDC token in the user's kubeconfig to simulate token expiry/tampering.

        Replaces the token value in ~/.kube/config with an invalid string.
        Requires an active authenticated session.

        Raises:
            KeywordException: If no authenticated session exists.
        """
        if not self.ldap_ssh:
            raise KeywordException("No authenticated session to corrupt token on")
        get_logger().log_info("Corrupting OIDC token in kubeconfig")
        self.ldap_ssh.send("sed -i 's/token:.*/token: INVALID_TOKEN_12345/' $HOME/.kube/config")
