"""Keywords for OIDC authentication operations.

Provides methods for authenticating users via oidc-auth CLI,
verifying kubectl access with OIDC tokens, and managing
kubeconfig setup for OIDC-authenticated sessions.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords


class OidcAuthKeywords(BaseKeyword):
    """Keywords for OIDC authentication and kubectl access verification.

    Encapsulates the oidc-auth CLI workflow: kubeconfig setup,
    token acquisition, and kubectl access validation.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OIDC auth keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)

    def setup_kubeconfig(self) -> None:
        """Initialize kubeconfig for OIDC authentication.

        Removes existing kubeconfig and runs kubeconfig-setup
        to prepare for oidc-auth token acquisition.
        """
        self.file_keywords.delete_directory("~/.kube")
        self.file_keywords.create_directory("~/.kube")
        self.ssh_connection.send("kubeconfig-setup")
        self.ssh_connection.send("source ~/.profile")

    def authenticate_ldap_user(self, password: str) -> None:
        """Authenticate as LDAP user via oidc-auth.

        Assumes the SSH session is already connected as the LDAP user
        so oidc-auth auto-detects the username from the login session.

        Args:
            password (str): LDAP user password.
        """
        self.setup_kubeconfig()
        self.ssh_connection.send(f"oidc-auth -p {password}")
        self.validate_success_return_code(self.ssh_connection)

    def authenticate_wad_user(self, username: str, password: str, backend: str = "wad") -> None:
        """Authenticate WAD user via oidc-auth from an existing SSH session.

        Args:
            username (str): WAD username.
            password (str): WAD user password.
            backend (str): DEX connector backend ID for WAD.
        """
        self.setup_kubeconfig()
        self.ssh_connection.send(f"oidc-auth -u {username} -p {password} -b {backend}")
        self.validate_success_return_code(self.ssh_connection)

    @staticmethod
    def create_ldap_user_ssh(oam_ip: str, username: str, password: str) -> SSHConnection:
        """Create SSH session as LDAP user and authenticate via oidc-auth.

        SSHes as the LDAP user directly so oidc-auth auto-detects the username
        from the login session, avoiding mechanize form-fill issues with
        readonly fields.

        Args:
            oam_ip (str): Lab OAM IP address.
            username (str): LDAP username.
            password (str): LDAP password.

        Returns:
            SSHConnection: Authenticated SSH session with OIDC token.
        """
        ldap_ssh = SSHConnectionManager.create_ssh_connection(oam_ip, username, password)
        ldap_ssh.connect()
        get_logger().log_info(f"Created LDAP user SSH session for {username}")
        oidc_keywords = OidcAuthKeywords(ldap_ssh)
        oidc_keywords.authenticate_ldap_user(password)
        return ldap_ssh
