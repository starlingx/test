import re
import threading

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
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
        self.file_keywords = FileKeywords(ssh_connection)
        self.lab_connection_keywords = LabConnectionKeywords()

    def run_kubectl_with_browser_login(self, kubeconfig_path: str, login_url: str, username: str, password: str, totp_secret: str = None) -> KubectlResultObject:
        """Start kubectl in background and authenticate via Keycloak browser login.

        Launches kubectl in a background thread. kubelogin binds port 8000 and
        prints the listener URL to stdout. The browser navigates to login_url,
        retrying until the port is ready, then completes the Keycloak MFA flow.

        Direct ssh_connection.client.exec_command is used intentionally here
        because the kubectl command must run non-blocking in a background thread
        while the browser login completes concurrently. ssh_connection.send()
        is synchronous and would block the main thread.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.
            login_url (str): The kubelogin listener URL (e.g. http://[oam_ip]:8000/).
            username (str): Keycloak username.
            password (str): Keycloak password.
            totp_secret (str): Base32 TOTP secret. Pass None for CONFIGURE_TOTP flow.

        Returns:
            KubectlResultObject: Result containing output and error state.
        """
        kubectl_ssh = self.lab_connection_keywords.get_active_controller_ssh()
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A'"
        result = KubectlResultObject()

        def run_kubectl() -> None:
            if not kubectl_ssh.is_connected:
                kubectl_ssh.connect()
            # exec_command used directly: non-blocking execution required so the
            # browser login can proceed concurrently on the main thread.
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

    def expire_cached_id_token(self, cache_dir: str) -> None:
        """Replace the cached id_token with an expired token, preserving the refresh_token.

        Reads the cache file, replaces the id_token value with a structurally valid
        JWT whose exp claim is set to 0 (epoch 1970, always expired), and writes it
        back. The refresh_token is preserved so kubelogin can silently exchange it.

        Args:
            cache_dir (str): Path to the OIDC token cache directory on the remote host.

        Raises:
            Exception: If no cache files are found in the cache directory.
        """
        cache_files = self.file_keywords.get_files_in_dir(cache_dir)
        validate_equals(len(cache_files) > 0, True, f"OIDC cache files should exist in '{cache_dir}'")
        cache_file = f"{cache_dir}/{cache_files[0]}"
        get_logger().log_info(f"Expiring id_token in cache file: {cache_file}")
        # Expired JWT: header.payload.signature where payload has exp=0
        # eyJhbGciOiJSUzI1NiJ9 = {"alg":"RS256"}
        # eyJleHAiOjB9 = {"exp":0}
        expired_id_token = "eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjB9.invalid"
        content = "".join(self.file_keywords.read_file(cache_file))
        updated = re.sub(r'"id_token"\s*:\s*"[^"]+"', f'"id_token":"{expired_id_token}"', content)
        self.file_keywords.create_file_with_heredoc(cache_file, updated)
        get_logger().log_info("id_token replaced with expired token in cache")

    def invalidate_cached_refresh_token(self, cache_dir: str) -> None:
        """Replace the cached refresh_token with an invalid value, preserving the id_token.

        Reads the cache file and replaces the refresh_token value with a garbage
        string so kubelogin cannot use it for silent refresh. The id_token is
        preserved. kubelogin will detect the invalid refresh token and open the
        browser for full re-authentication.

        Args:
            cache_dir (str): Path to the OIDC token cache directory on the remote host.

        Raises:
            Exception: If no cache files are found in the cache directory.
        """
        cache_files = self.file_keywords.get_files_in_dir(cache_dir)
        validate_equals(len(cache_files) > 0, True, f"OIDC cache files should exist in '{cache_dir}'")
        cache_file = f"{cache_dir}/{cache_files[0]}"
        get_logger().log_info(f"Invalidating refresh_token in cache file: {cache_file}")
        content = "".join(self.file_keywords.read_file(cache_file))
        updated = re.sub(r'"refresh_token"\s*:\s*"[^"]+"', '"refresh_token":"invalid"', content)
        self.file_keywords.create_file_with_heredoc(cache_file, updated)
        get_logger().log_info("refresh_token replaced with invalid value in cache")

    def validate_token_cache_exists(self, cache_dir: str) -> None:
        """Validate that the OIDC token cache directory exists on the remote host.

        This must be called before run_kubectl_with_cached_token to ensure a prior
        browser login has populated the cache. Fails immediately if the cache is
        missing, preventing a 3-minute kubectl timeout.

        Args:
            cache_dir (str): Path to the OIDC token cache directory on the remote host.
        """
        validate_equals(self.file_keywords.file_exists(cache_dir), True, f"OIDC token cache should exist at '{cache_dir}'")
        get_logger().log_info(f"OIDC token cache found at '{cache_dir}'")

    def run_kubectl_with_cached_token(self, kubeconfig_path: str, timeout: int = 30) -> KubectlResultObject:
        """Run kubectl using the cached OIDC token without browser interaction.

        Uses a timeout to confirm kubectl completes without waiting for a browser
        login prompt. If kubectl hangs beyond the timeout it means kubelogin is
        waiting for browser interaction, which indicates the cached token was not
        usable for silent refresh.

        Direct ssh_connection.client.exec_command is used intentionally here
        because a thread-level read timeout is required to detect when kubelogin
        is waiting for browser input. ssh_connection.send() blocks until the
        command exits and cannot be interrupted by a timeout.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.
            timeout (int): Maximum seconds to wait for kubectl to complete.

        Returns:
            KubectlResultObject: Result containing kubectl output.
        """
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A'"
        get_logger().log_info(f"Running kubectl using cached OIDC token (timeout={timeout}s)")
        result = KubectlResultObject()
        if not self.ssh_connection.is_connected:
            self.ssh_connection.connect()
        # exec_command used directly: a thread-level read timeout is required to
        # detect when kubelogin is waiting for browser input rather than exiting.
        _, stdout, _ = self.ssh_connection.client.exec_command(kubectl_cmd, timeout=None)
        stdout.channel.set_combine_stderr(True)
        output_lines = []

        def read_output() -> None:
            for line in stdout:
                output_lines.append(line)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        reader.join(timeout=timeout)
        output = "".join(output_lines)
        get_logger().log_info(f"kubectl output: {output}")
        result.set_output(output)
        result.set_browser_prompt_shown("Please visit the following URL in your browser" in output)
        return result

    def run_kubectl_run_with_cached_token(self, kubeconfig_path: str, pod_name: str, image: str, namespace: str, timeout: int = 30) -> KubectlResultObject:
        """Run kubectl run using the cached OIDC token without browser interaction.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.
            pod_name (str): Name for the pod to create.
            image (str): Container image to use.
            namespace (str): Namespace to create the pod in.
            timeout (int): Maximum seconds to wait for kubectl to complete.

        Returns:
            KubectlResultObject: Result containing kubectl output.
        """
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} run {pod_name} --image={image} --restart=Never -n {namespace}'"
        get_logger().log_info(f"Running kubectl run using cached OIDC token (timeout={timeout}s)")
        result = KubectlResultObject()
        if not self.ssh_connection.is_connected:
            self.ssh_connection.connect()
        _, stdout, _ = self.ssh_connection.client.exec_command(kubectl_cmd, timeout=None)
        stdout.channel.set_combine_stderr(True)
        output_lines = []

        def read_output() -> None:
            for line in stdout:
                output_lines.append(line)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        reader.join(timeout=timeout)
        output = "".join(output_lines)
        get_logger().log_info(f"kubectl run output: {output}")
        result.set_output(output)
        return result

    def patch_kubeconfig_issuer_url(self, kubeconfig_path: str, invalid_issuer_url: str) -> None:
        """Replace the oidc-issuer-url in an existing kubeconfig with an invalid value.

        Reads the kubeconfig file on the remote host, replaces the
        --oidc-issuer-url argument value, and writes it back in-place.
        Used to test authentication failure behaviour without regenerating
        the full OIDC environment.

        Args:
            kubeconfig_path (str): Full path to the kubeconfig file on the remote host.
            invalid_issuer_url (str): The invalid issuer URL to substitute.
        """
        get_logger().log_info(f"Patching oidc-issuer-url in kubeconfig: {kubeconfig_path}")
        content = "".join(self.file_keywords.read_file(kubeconfig_path))
        updated = re.sub(r"--oidc-issuer-url=[^\s'\"]+", f"--oidc-issuer-url={invalid_issuer_url}", content)
        self.file_keywords.create_file_with_heredoc(kubeconfig_path, updated)
        get_logger().log_info(f"oidc-issuer-url replaced with '{invalid_issuer_url}'")

    def run_kubectl_run_with_browser_login(self, kubeconfig_path: str, login_url: str, pod_name: str, image: str, namespace: str, username: str, password: str, totp_secret: str = None) -> KubectlResultObject:
        """Start kubectl run in background and authenticate via Keycloak browser login.

        Launches kubectl run in a background thread then completes the Keycloak
        MFA browser flow concurrently. exec_command is used directly so the
        kubectl command runs non-blocking while the browser login proceeds.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.
            login_url (str): The kubelogin listener URL (e.g. http://[oam_ip]:8000/).
            pod_name (str): Name for the pod to create.
            image (str): Container image to use.
            namespace (str): Namespace to create the pod in.
            username (str): Keycloak username.
            password (str): Keycloak password.
            totp_secret (str): Base32 TOTP secret. Pass None for CONFIGURE_TOTP flow.

        Returns:
            KubectlResultObject: Result containing output and error state.
        """
        kubectl_ssh = self.lab_connection_keywords.get_active_controller_ssh()
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} run {pod_name} --image={image} --restart=Never -n {namespace}'"
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

    def run_kubectl_auth_can_i_with_cached_token(self, kubeconfig_path: str, verb: str, resource: str, all_namespaces: bool = False, timeout: int = 30) -> KubectlResultObject:
        """Run kubectl auth can-i using the cached OIDC token without browser interaction.

        Uses a timeout to confirm kubectl completes without waiting for a browser
        login prompt. exec_command is used directly so a thread-level read timeout
        can detect when kubelogin is waiting for browser input.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.
            verb (str): The verb to check (e.g. 'list', 'create').
            resource (str): The resource to check (e.g. 'pods').
            all_namespaces (bool): Whether to check across all namespaces (-A flag).
            timeout (int): Maximum seconds to wait for kubectl to complete.

        Returns:
            KubectlResultObject: Result containing kubectl auth can-i output.
        """
        ns_flag = " -A" if all_namespaces else ""
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} auth can-i {verb} {resource}{ns_flag}'"
        get_logger().log_info(f"Running kubectl auth can-i {verb} {resource}{ns_flag} (timeout={timeout}s)")
        result = KubectlResultObject()
        if not self.ssh_connection.is_connected:
            self.ssh_connection.connect()
        # exec_command used directly: a thread-level read timeout is required to
        # detect when kubelogin is waiting for browser input rather than exiting.
        _, stdout, _ = self.ssh_connection.client.exec_command(kubectl_cmd, timeout=None)
        stdout.channel.set_combine_stderr(True)
        output_lines = []

        def read_output() -> None:
            output_lines.extend(stdout.readlines())

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        reader.join(timeout=timeout)
        output = "".join(output_lines)
        get_logger().log_info(f"kubectl auth can-i output: {output}")
        result.set_output(output)
        return result

    def clear_oidc_token_cache(self) -> None:
        """Delete the OIDC token cache using kubectl oidc-login clean.

        Runs kubectl oidc-login clean on the remote host to remove all cached
        OIDC tokens. The next kubectl invocation will require browser authentication.
        """
        get_logger().log_info("Clearing OIDC token cache via kubectl oidc-login clean")
        self.ssh_connection.send("bash -lc 'kubectl oidc-login clean'")
        self.validate_success_return_code(self.ssh_connection)
