"""Keywords for running StarlingX platform CLI commands via browser-based OIDC login.

Runs an STX platform CLI command (e.g. 'system host-list') as the OIDC user in a
dedicated SSH session so the oidc-login listener starts on the OAM IP (port 8000),
then completes the OIDC login with a headless Selenium browser and captures the
command output.

The STX CLI command and the kubeconfig/oidc prep (kubeconfig-setup, source
local_starlingxrc oidc) run in the OIDC user's own SSH session — NOT on the
sysadmin/admin connection — so the admin kubeconfig on the controller is never
modified.

Supports all three DEX connectors:
    - Local LDAP  (DEX-native login form, via DexLoginPage)
    - WAD / AD    (DEX-native login form, via DexLoginPage)
    - Keycloak    (redirect to Keycloak, via KeycloakLoginPage, with optional MFA/TOTP)

Connector selection and the DEX-native login form are handled by DexLoginPage.
All element locators live in their respective page-object locator classes.

This is a standalone keyword module dedicated to the STX CLI OIDC login flow; it
does not modify the existing OIDC keywords.
"""

import threading

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.web.webdriver_core import WebDriverCore
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.keycloak.objects.keycloak_kubectl_result_object import KubectlResultObject
from web_pages.dex.login.dex_login_page import DexLoginPage
from web_pages.keycloak.login.keycloak_login_page import KeycloakLoginPage


class StxOidcLoginKeywords(BaseKeyword):
    """Run STX platform CLI commands authenticated via browser-based OIDC login (LDAP/WAD/Keycloak)."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Active SSH connection to the controller
                (used only for cleanup helpers; the OIDC command runs in a separate
                OIDC-user session).
        """
        self.ssh_connection = ssh_connection

    def run_stx_command_with_browser_login(
        self,
        stx_cli_cmd: str,
        login_url: str,
        oam_ip: str,
        username: str,
        password: str,
        connector: str = "",
        is_keycloak: bool = False,
        totp_secret: str = None,
    ) -> KubectlResultObject:
        """Run an STX platform CLI command as the OIDC user and authenticate via headless browser.

        Opens a dedicated SSH session as the OIDC user, then in the background runs:
        clear oidc-login cache -> kubeconfig-setup -> source local_starlingxrc oidc
        -> the STX CLI command. Sourcing local_starlingxrc oidc starts the oidc-login
        listener on port 8000 and prints the login URL. The browser then navigates to
        login_url, selects the requested DEX connector (if a connector-selection page
        is shown), and completes the login (DEX-native for LDAP/WAD, or Keycloak with
        optional MFA), after which the command proceeds and its output is captured.

        The prep + command run in the OIDC user's own session, so the sysadmin/admin
        kubeconfig on the controller is never modified.

        Args:
            stx_cli_cmd (str): STX platform CLI command (e.g. 'system host-list').
            login_url (str): The oidc-login listener URL (e.g. http://[oam_ip]:8000/).
            oam_ip (str): Lab OAM IP to SSH into as the OIDC user (bare, no brackets).
            username (str): OIDC login username (also the SSH user).
            password (str): OIDC login password (also the SSH password).
            connector (str): DEX connector to select (e.g. 'ldap', 'wad', 'keycloak').
                Empty selects the first connector or skips selection if only one exists.
            is_keycloak (bool): True if the selected connector redirects to Keycloak
                (uses the Keycloak login form + optional MFA). False for DEX-native
                LDAP/WAD login forms.
            totp_secret (str): Base32 TOTP secret for the Keycloak MFA challenge.
                Pass None for the CONFIGURE_TOTP first-login flow. Ignored for LDAP/WAD.

        Returns:
            KubectlResultObject: Result containing the command output.
        """
        # Open a dedicated SSH session AS THE OIDC USER so kubeconfig-setup and
        # source local_starlingxrc oidc run in the OIDC user's home, never touching
        # the sysadmin/admin kubeconfig on the controller.
        oidc_ssh = SSHConnectionManager.create_ssh_connection(oam_ip, username, password)
        oidc_ssh.connect()

        # Match the manual oidc-login flow (run as the OIDC user):
        #   rm -rf ~/.kube/cache/oidc-login/ ; kubeconfig-setup ;
        #   source local_starlingxrc oidc <<< '<password>' ; <stx command>
        prep = "rm -rf ~/.kube/cache/oidc-login/ && kubeconfig-setup"
        source_oidc = f"source local_starlingxrc oidc <<< '{password}'"
        full_cmd = f'bash -lc "{prep} && {source_oidc} && {stx_cli_cmd}"'

        output_lines = []
        thread = self._start_background_cmd(oidc_ssh, full_cmd, output_lines)

        get_logger().log_info(f"Authenticating via headless browser at {login_url} (connector='{connector}', keycloak={is_keycloak})")
        driver = WebDriverCore()
        try:
            dex_login_page = DexLoginPage(driver)
            # navigate_to_login_url retries/reloads until DEX is reachable, so it
            # tolerates the few seconds the oidc-login listener needs to start.
            dex_login_page.navigate_to_login_url(login_url)
            dex_login_page.select_connector_if_present(connector)
            if is_keycloak:
                # Keycloak login form (+ MFA) is handled by the existing page object.
                KeycloakLoginPage(driver).login(username=username, password=password, totp_secret=totp_secret)
            else:
                # DEX-native login form for Local LDAP / WAD connectors.
                dex_login_page.submit_native_login(username, password)
        finally:
            thread.join(timeout=300)
            driver.quit()
            oidc_ssh.close()

        result = KubectlResultObject()
        result.set_output("".join(output_lines))
        return result

    def _start_background_cmd(self, ssh_connection: SSHConnection, cmd: str, output_lines: list) -> threading.Thread:
        """Start a command in a background thread on the given SSH connection, capturing output.

        exec_command is used directly because the STX CLI command must run
        non-blocking while the browser login proceeds concurrently on the main
        thread; the synchronous SSH command helpers would block instead.

        Args:
            ssh_connection (SSHConnection): SSH connection to run the command on (OIDC-user session).
            cmd (str): Command to execute on the remote host.
            output_lines (list): Shared list to append captured output lines to.

        Returns:
            threading.Thread: The running background thread.
        """

        def run_cmd() -> None:
            if not ssh_connection.is_connected:
                ssh_connection.connect()
            _, stdout, _ = ssh_connection.client.exec_command(cmd, timeout=None)
            stdout.channel.set_combine_stderr(True)
            output_lines.extend(stdout)

        thread = threading.Thread(target=run_cmd, daemon=True)
        thread.start()
        return thread
