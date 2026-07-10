"""Keywords to run FM CLI commands as an OIDC-authenticated user."""

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.fm_oidc.object.fm_oidc_command_result_output import FmOidcCommandResultOutput
from keywords.cloud_platform.system.oam.system_oam_show_keywords import SystemOamShowKeywords


class FmOidcKeywords(BaseKeyword):
    """Run FM CLI commands as an OIDC-authenticated user.

    Flow:
    1. SSH as LDAP user
    2. kubeconfig-setup && source ~/.profile  (sets KUBECONFIG)
    3. oidc-auth -p <password>  (gets OIDC token into kubeconfig)
    4. source local_starlingxrc oidc <<< password  (sets OS_AUTH_URL etc)
    5. fm --stx-auth-type=oidc <command>  (uses CLI arg, not env var)
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.ldap_ssh = None
        self.authenticated_user = None

    def get_authenticated_session(
        self,
        username: str,
        password: str,
        lab_oam_ip: str,
        oidc_backend: str = None,
        oidc_username: str = None,
    ) -> SSHConnection:
        """Create and authenticate an OIDC session for the given user.

        Reuses existing session if already authenticated as the same user.
        Performs kubeconfig-setup, oidc-auth, and sources local_starlingxrc.

        Args:
            username (str): LDAP username for SSH login.
            password (str): Password for SSH and OIDC authentication.
            lab_oam_ip (str): Lab OAM IP address for SSH connection.
            oidc_backend (str): Optional OIDC backend name for WAD users.
            oidc_username (str): Optional OIDC username for WAD users.

        Returns:
            SSHConnection: Authenticated SSH session ready for FM commands.
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

        # Patch kubeconfig if platform OAM is IPv4 but kubeconfig-setup used IPv6
        # On dual-stack labs, NodePorts (30555/30556) only serve on IPv4 OAM
        oam_show_kw = SystemOamShowKeywords(self.ssh_connection)
        oam_ipv4_addr = oam_show_kw.oam_show().get_oam_ip()
        if oam_ipv4_addr and ":" not in oam_ipv4_addr:
            get_logger().log_info(f"Patching kubeconfig to use IPv4 OAM {oam_ipv4_addr} for NodePort access")
            self.ldap_ssh.send(f"sed -i " f"'s|\\[.*\\]:30556|{oam_ipv4_addr}:30556|g; " f"s|\\[.*\\]:30555|{oam_ipv4_addr}:30555|g; " f"s|\\[.*\\]:8000|{oam_ipv4_addr}:8000|g' " f"$HOME/.kube/config")

        if oidc_backend and oidc_username:
            output = self.ldap_ssh.send(f"oidc-auth -b {oidc_backend} -u {oidc_username} -p {password}")
        else:
            output = self.ldap_ssh.send(f"oidc-auth -p {password}")
        raw = "\n".join(output) if isinstance(output, list) else output
        if "Login succeeded" not in raw:
            get_logger().log_error(f"oidc-auth failed: {raw[:200]}")

        self.ldap_ssh.send(f"source local_starlingxrc oidc <<< '{password}'")

        return self.ldap_ssh

    def build_fm_command(self, fm_command: str) -> str:
        """Build the full FM command with OIDC auth type and environment setup.

        Prepends KUBECONFIG export and openrc source, then injects
        --stx-auth-type=oidc into the FM command.

        Args:
            fm_command (str): The FM command to run (e.g. 'fm alarm-list').

        Returns:
            str: Full command string ready for execution.
        """
        fm_with_arg = fm_command.replace("fm ", "fm --stx-auth-type=oidc ", 1)
        return f"export PATH=$PATH:/usr/sbin && " f"export KUBECONFIG=$HOME/.kube/config && " f"source /etc/platform/openrc --no_credentials && " f"export OS_USERNAME=$(whoami) && " f"{fm_with_arg}"

    def run_fm_command_as_oidc_user(
        self,
        username: str,
        password: str,
        lab_oam_ip: str,
        fm_command: str,
        timeout_sec: int = 120,
    ) -> FmOidcCommandResultOutput:
        """Run an FM command as an OIDC-authenticated user.

        Args:
            username (str): LDAP username.
            password (str): User password.
            lab_oam_ip (str): Lab OAM IP address.
            fm_command (str): FM command to execute (e.g. 'fm alarm-list').
            timeout_sec (int): Command timeout in seconds.

        Returns:
            FmOidcCommandResultOutput: Parsed command result with success/failure status.
        """
        ldap_ssh = self.get_authenticated_session(username, password, lab_oam_ip)
        combined = self.build_fm_command(fm_command)
        get_logger().log_info(f"Running FM command: {fm_command}")
        output = ldap_ssh.send(combined, command_timeout=timeout_sec)
        raw_output = "\n".join(output) if isinstance(output, list) else output
        return FmOidcCommandResultOutput(fm_command, raw_output)

    def run_fm_command_with_cli_arg(
        self,
        username: str,
        password: str,
        lab_oam_ip: str,
        fm_command: str,
        timeout_sec: int = 120,
    ) -> FmOidcCommandResultOutput:
        """Run an FM command with --stx-auth-type=oidc CLI argument.

        Same as run_fm_command_as_oidc_user since both use CLI arg approach.

        Args:
            username (str): LDAP username.
            password (str): User password.
            lab_oam_ip (str): Lab OAM IP address.
            fm_command (str): FM command to execute.
            timeout_sec (int): Command timeout in seconds.

        Returns:
            FmOidcCommandResultOutput: Parsed command result with success/failure status.
        """
        return self.run_fm_command_as_oidc_user(username, password, lab_oam_ip, fm_command, timeout_sec)

    def run_fm_command_as_wad_user(
        self,
        wad_login_username: str,
        password: str,
        lab_oam_ip: str,
        fm_command: str,
        oidc_backend: str,
        oidc_username: str,
        timeout_sec: int = 120,
    ) -> FmOidcCommandResultOutput:
        """Run an FM command as a WAD OIDC-authenticated user.

        Args:
            wad_login_username (str): LDAP username for SSH login.
            password (str): User password.
            lab_oam_ip (str): Lab OAM IP address.
            fm_command (str): FM command to execute.
            oidc_backend (str): OIDC backend name (e.g. 'wad-1').
            oidc_username (str): OIDC username for the WAD backend.
            timeout_sec (int): Command timeout in seconds.

        Returns:
            FmOidcCommandResultOutput: Parsed command result with success/failure status.
        """
        ldap_ssh = self.get_authenticated_session(wad_login_username, password, lab_oam_ip, oidc_backend, oidc_username)
        combined = self.build_fm_command(fm_command)
        get_logger().log_info(f"Running FM command as WAD user: {fm_command}")
        output = ldap_ssh.send(combined, command_timeout=timeout_sec)
        raw_output = "\n".join(output) if isinstance(output, list) else output
        return FmOidcCommandResultOutput(fm_command, raw_output)

    def close_session(self) -> None:
        """Close the OIDC SSH session and clear cached state."""
        if self.ldap_ssh:
            self.ldap_ssh.close()
            self.ldap_ssh = None
            self.authenticated_user = None

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
            name=f"oidc-{username}",
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )
