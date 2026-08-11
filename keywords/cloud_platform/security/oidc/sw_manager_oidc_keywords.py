"""Run sw-manager CLI commands as an OIDC-authenticated user."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.security.oidc.oidc_cli_keywords import OidcCliKeywords


class SwManagerOidcKeywords(OidcCliKeywords):
    """Run sw-manager CLI commands as an OIDC-authenticated user."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        super().__init__(ssh_connection, cli_name="sw-manager")

    def build_command(self, command: str, password: str = "") -> str:
        """Build sw-manager command with --stx-auth-type=oidc.

        Args:
            command (str): sw-manager command (e.g. 'sw-manager sw-deploy-strategy show').
            password (str): User password for OS_PASSWORD.

        Returns:
            str: Full command string ready for execution.
        """
        cmd_with_arg = command.replace("sw-manager ", "sw-manager --stx-auth-type=oidc ", 1)
        return (
            f"source /etc/platform/openrc --no_credentials && "
            f"export KUBECONFIG=$HOME/.kube/config && "
            f"export OS_USERNAME=$(whoami) && "
            f"export OS_PASSWORD='{password}' && "
            f"{cmd_with_arg}"
        )
