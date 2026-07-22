"""Keywords for managing OIDC-authenticated SSH sessions for dcmanager commands."""

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.oam.system_oam_show_keywords import SystemOamShowKeywords


class DcManagerOidcKeywords(BaseKeyword):
    """Manage an OIDC-authenticated SSH session for dcmanager operations.

    Provides an authenticated SSH session that can be passed to dcmanager
    keywords with use_oidc=True. The session is created by:
    1. SSH as LDAP user
    2. kubeconfig-setup && source ~/.profile (sets KUBECONFIG)
    3. oidc-auth -p <password> (gets OIDC token into kubeconfig)
    4. source local_starlingxrc oidc <<< password (sets OS_AUTH_URL etc)
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.ldap_ssh = None
        self.authenticated_user = None

    def get_authenticated_session(self, username: str, password: str, lab_oam_ip: str) -> SSHConnection:
        """Create and authenticate an OIDC session for the given user.

        Reuses existing session if already authenticated as the same user.
        Performs kubeconfig-setup, oidc-auth, and sources local_starlingxrc.

        Args:
            username (str): LDAP username for SSH login.
            password (str): Password for SSH and OIDC authentication.
            lab_oam_ip (str): Lab OAM IP address for SSH connection.

        Returns:
            SSHConnection: Authenticated SSH session ready for dcmanager commands.

        Raises:
            KeywordException: If SSH connection or oidc-auth fails.
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
            raise KeywordException(f"SSH connection as {username}@{lab_oam_ip} failed")

        self.ldap_ssh.send("kubeconfig-setup")
        self.ldap_ssh.send("source ~/.profile")

        # Patch kubeconfig if platform OAM is IPv4 but kubeconfig-setup used IPv6
        oam_show_kw = SystemOamShowKeywords(self.ssh_connection)
        oam_ipv4_addr = oam_show_kw.oam_show().get_oam_ip()
        if oam_ipv4_addr and ":" not in oam_ipv4_addr:
            get_logger().log_info(f"Patching kubeconfig to use IPv4 OAM {oam_ipv4_addr} for NodePort access")
            self.ldap_ssh.send(f"sed -i 's|\\[.*\\]:30556|{oam_ipv4_addr}:30556|g; s|\\[.*\\]:30555|{oam_ipv4_addr}:30555|g; s|\\[.*\\]:8000|{oam_ipv4_addr}:8000|g' $HOME/.kube/config")

        output = self.ldap_ssh.send(f"oidc-auth -p {password}")
        raw = "\n".join(output) if isinstance(output, list) else output
        if "Login succeeded" not in raw:
            get_logger().log_error(f"oidc-auth failed for {username}: {raw[:200]}")
            raise KeywordException(f"oidc-auth failed for user {username}")

        self.ldap_ssh.send(f"source local_starlingxrc oidc <<< '{password}'")

        return self.ldap_ssh

    def close_session(self) -> None:
        """Close the OIDC SSH session and clear cached state."""
        if self.ldap_ssh:
            self.ldap_ssh.close()
            self.ldap_ssh = None
            self.authenticated_user = None

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
        ssh = SSHConnectionManager.create_ssh_connection(
            lab_oam_ip,
            username,
            password,
            name=f"oidc-dcm-{username}",
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )
        if not ssh:
            raise KeywordException(f"Failed to create SSH connection as LDAP user {username}@{lab_oam_ip}")
        return ssh
