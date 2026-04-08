import threading

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.web.webdriver_core import WebDriverCore
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.keycloak.objects.keycloak_kubectl_result_object import KubectlResultObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from web_pages.keycloak.login.keycloak_login_page import KeycloakLoginPage


class KeycloakMfaKeywords(BaseKeyword):
    """Keywords for Keycloak MFA browser-based kubectl authentication flows."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Active controller SSH connection.
        """
        self.ssh_connection = ssh_connection

    def run_kubectl_with_browser_login(self, kubeconfig_path: str, login_url: str, username: str, password: str, totp_secret: str = None) -> KubectlResultObject:
        """Start kubectl in background and authenticate via Keycloak browser login.

        Launches kubectl in a background thread. kubelogin binds port 8000 and
        prints the listener URL to stdout. The browser navigates to login_url,
        retrying until the port is ready, then completes the Keycloak MFA flow.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.
            login_url (str): The kubelogin listener URL (e.g. http://[oam_ip]:8000/).
            username (str): Keycloak username.
            password (str): Keycloak password.
            totp_secret (str): Base32 TOTP secret. Pass None for CONFIGURE_TOTP flow.

        Returns:
            KubectlResultObject: Result containing output and error state.
        """
        kubectl_ssh = LabConnectionKeywords().get_active_controller_ssh()
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A'"
        result = KubectlResultObject()

        def run_kubectl() -> None:
            if not kubectl_ssh.is_connected:
                kubectl_ssh.connect()
            _, stdout, _ = kubectl_ssh.client.exec_command(kubectl_cmd, timeout=None)
            stdout.channel.set_combine_stderr(True)
            result.set_output("".join(stdout.readlines()))

        kubectl_thread = threading.Thread(target=run_kubectl, daemon=True)
        kubectl_thread.start()

        get_logger().log_info(f"Navigating to OIDC login URL: {login_url}")
        driver = WebDriverCore()
        keycloak_login_page = KeycloakLoginPage(driver)
        keycloak_login_page.navigate_to_login_url(login_url)
        keycloak_login_page.login(username=username, password=password, totp_secret=totp_secret)

        kubectl_thread.join(timeout=300)
        driver.quit()

        return result

    def validate_token_cache_exists(self, cache_dir: str) -> None:
        """Validate that the OIDC token cache directory exists on the remote host.

        This must be called before run_kubectl_with_cached_token to ensure a prior
        browser login has populated the cache. Raises KeywordException immediately
        if the cache is missing, preventing a 3-minute kubectl timeout.

        Args:
            cache_dir (str): Path to the OIDC token cache directory on the remote host.

        Raises:
            KeywordException: If the token cache directory does not exist.
        """
        if not FileKeywords(self.ssh_connection).file_exists(cache_dir):
            raise KeywordException(f"OIDC token cache not found at '{cache_dir}'. " "Run test_oidc_keycloak_mfa_first_login first to populate the cache.")
        get_logger().log_info(f"OIDC token cache found at '{cache_dir}'")

    def run_kubectl_with_cached_token(self, kubeconfig_path: str) -> KubectlResultObject:
        """Run kubectl using the cached OIDC token without browser interaction.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.

        Returns:
            KubectlResultObject: Result containing kubectl output.
        """
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A'"
        get_logger().log_info("Running kubectl using cached OIDC token")
        if not self.ssh_connection.is_connected:
            self.ssh_connection.connect()
        _, stdout, _ = self.ssh_connection.client.exec_command(kubectl_cmd, timeout=None)
        stdout.channel.set_combine_stderr(True)
        result = KubectlResultObject()
        result.set_output("".join(stdout.readlines()))
        return result

    def clear_oidc_token_cache(self, cache_dir: str) -> None:
        """Delete the OIDC token cache using kubectl oidc-login clean.

        Args:
            cache_dir (str): Unused - kept for API compatibility.
        """
        get_logger().log_info("Clearing OIDC token cache via kubectl oidc-login clean")
        self.ssh_connection.send("bash -lc 'kubectl oidc-login clean'")
