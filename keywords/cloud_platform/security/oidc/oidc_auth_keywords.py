"""Keywords for OIDC authentication operations.

Provides methods for authenticating users via oidc-auth CLI,
verifying kubectl access with OIDC tokens, and managing
kubeconfig setup for OIDC-authenticated sessions.
"""

from config.configuration_manager import ConfigurationManager
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

    def restore_admin_kubeconfig(self) -> None:
        """Restore the admin user's default kubeconfig to the cluster-admin context.

        OIDC authentication on the admin session (kubeconfig-setup + oidc-auth)
        overwrites ~/.kube/config with an OIDC user/token. Once that token expires
        (or in a fresh session) plain ``kubectl`` falls into interactive auth and
        prompts "Please enter Username:", which breaks any later test — including
        the CGCS framework, which relies on the admin user's default ~/.kube/config.

        This resets ~/.kube/config to /etc/kubernetes/admin.conf so subsequent
        kubectl calls use the known-good cluster-admin context. It is best-effort
        and never raises, so it is safe to register as a teardown finalizer
        regardless of prior OIDC state.
        """
        # Derive the admin user from lab config rather than hardcoding, so the
        # path/ownership are correct on labs that use a non-default admin user.
        admin_user = ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()
        kube_config = f"/home/{admin_user}/.kube/config"

        get_logger().log_teardown_step("Restoring admin default kubeconfig to admin.conf")
        # Use send_as_sudo_non_interactive: sudo requires a password on most labs,
        # so a plain send("sudo cp ...") silently fails and leaves ~/.kube/config
        # broken (the exact interactive-auth symptom). It feeds the sudo password via
        # stdin and omits the literal "sudo" prefix (added by the helper).
        #
        # Best-effort: this runs as a teardown finalizer, so an exception here
        # could mask the real test result or block other finalizers. On failure we
        # log loudly (with manual recovery steps) but do not re-raise.
        try:
            self.ssh_connection.send_as_sudo_non_interactive(f"cp /etc/kubernetes/admin.conf {kube_config}")
            self.ssh_connection.send_as_sudo_non_interactive(f"chown {admin_user}:sys_protected {kube_config}")
            # Verify the restore actually took effect so silent failures surface.
            output = self.ssh_connection.send("kubectl config current-context 2>&1")
            context = "".join(output) if isinstance(output, list) else str(output)
            if "kubernetes-admin" not in context:
                get_logger().log_error(f"kubeconfig restore did not yield admin context (current-context: {context.strip()}). " f"Lab {kube_config} may still be broken — subsequent kubectl calls could prompt for " f"credentials. Manual recovery: sudo cp /etc/kubernetes/admin.conf {kube_config}")
        except Exception as exc:
            # Broad by design: teardown must not raise. See method docstring.
            get_logger().log_error(f"restore_admin_kubeconfig failed (non-fatal): {exc}")

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
