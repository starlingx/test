"""Keywords for running software CLI commands as an OIDC-authenticated user."""

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.upgrade.objects.software_oidc_command_result import SoftwareOidcCommandResult


class SoftwareOidcKeywords(BaseKeyword):
    """Run software CLI commands as an OIDC-authenticated user.

    Flow:
    1. SSH as LDAP user
    2. kubeconfig-setup && source ~/.profile
    3. oidc-auth -p <password>
    4. source local_starlingxrc oidc <<< password
    5. software --stx-auth-type=oidc <command>
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
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
            SSHConnection: Authenticated SSH session ready for software commands.

        Raises:
            KeywordException: If oidc-auth fails to authenticate.
        """
        if self.ldap_ssh and self.authenticated_user == username:
            return self.ldap_ssh

        if self.ldap_ssh:
            self.ldap_ssh.close()

        get_logger().log_info(f"Creating OIDC session for {username}")
        self.ldap_ssh = self.create_ldap_ssh(username, password, lab_oam_ip)
        self.authenticated_user = username

        self.ldap_ssh.send("kubeconfig-setup")
        self.ldap_ssh.send("source ~/.profile")

        output = self.ldap_ssh.send(f"oidc-auth -p {password}")
        raw = "\n".join(output) if isinstance(output, list) else output
        if "Login succeeded" not in raw:
            raise KeywordException(f"oidc-auth failed for user {username}: {raw[:200]}")

        self.ldap_ssh.send(f"source local_starlingxrc oidc <<< '{password}'")

        return self.ldap_ssh

    def build_software_command(self, software_command: str) -> str:
        """Build the full software command with OIDC auth type.

        Prepends KUBECONFIG export and openrc source, then injects
        --stx-auth-type=oidc into the software command.

        Args:
            software_command (str): The software command (e.g. 'software list').

        Returns:
            str: Full command string ready for execution.
        """
        sw_with_arg = software_command.replace("software ", "software --stx-auth-type=oidc ", 1)
        return f"export KUBECONFIG=$HOME/.kube/config && " f"source /etc/platform/openrc --no_credentials && " f"export OS_USERNAME=$(whoami) && " f"{sw_with_arg}"

    def run_software_command_as_oidc_user(
        self,
        username: str,
        password: str,
        lab_oam_ip: str,
        software_command: str,
        timeout_sec: int = 120,
    ) -> SoftwareOidcCommandResult:
        """Run a software command as an OIDC-authenticated user.

        Args:
            username (str): LDAP username.
            password (str): User password.
            lab_oam_ip (str): Lab OAM IP address.
            software_command (str): Software command (e.g. 'software list').
            timeout_sec (int): Command timeout in seconds.

        Returns:
            SoftwareOidcCommandResult: Parsed command result with success/failure status.
        """
        ldap_ssh = self.get_authenticated_session(username, password, lab_oam_ip)
        combined = self.build_software_command(software_command)
        get_logger().log_info(f"Running software command: {software_command}")
        output = ldap_ssh.send(combined, command_timeout=timeout_sec)
        raw_output = "\n".join(output) if isinstance(output, list) else output
        return SoftwareOidcCommandResult(software_command, raw_output)

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

    def create_ldap_ssh(self, username: str, password: str, lab_oam_ip: str) -> SSHConnection:
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
            name=f"oidc-sw-{username}",
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )
