import re
import subprocess
import threading
import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from framework.web.webdriver_core import WebDriverCore
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.keycloak.objects.keycloak_kubectl_result_object import KubectlResultObject
from keywords.files.file_keywords import FileKeywords
from keywords.linux.pkill.pkill_keywords import PkillKeywords
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
        self.pkill_keywords = PkillKeywords(ssh_connection)

    def kill_kubelogin_processes(self) -> None:
        """Kill any lingering kubectl and kubelogin processes on the remote host.

        Ensures port 8000 is free before starting a new browser-based kubectl
        authentication flow. Uses pkill with || true so the command succeeds
        even when no matching processes are running.
        """
        get_logger().log_info("Killing any lingering kubectl and kubelogin processes")
        self.pkill_keywords.pkill_by_pattern("kubelogin")
        self.pkill_keywords.pkill_by_pattern("kubectl.*oidc")

    def start_kubectl_background_thread(self, kubectl_cmd: str, ssh_connection: SSHConnection) -> tuple[threading.Thread, list[str]]:
        """Launch a kubectl command in a background thread and return the thread and output buffer.

        exec_command is used directly because the kubectl command must run
        non-blocking while browser login or token operations proceed concurrently
        on the main thread. ssh_connection.send() is synchronous and would block.

        Args:
            kubectl_cmd (str): Full kubectl command string to execute on the remote host.
            ssh_connection (SSHConnection): SSH connection to use for command execution.

        Returns:
            tuple[threading.Thread, list[str]]: The background thread and the shared output buffer.
        """
        output_lines = []

        def run_kubectl() -> None:
            if not ssh_connection.is_connected:
                ssh_connection.connect()
            _, stdout, _ = ssh_connection.client.exec_command(kubectl_cmd, timeout=None)
            stdout.channel.set_combine_stderr(True)
            output_lines.extend(stdout)

        thread = threading.Thread(target=run_kubectl, daemon=True)
        thread.start()
        return thread, output_lines

    def execute_kubectl_with_timeout(self, kubectl_cmd: str, timeout: int) -> str:
        """Execute a kubectl command on self.ssh_connection and collect output with a timeout.

        Uses a reader thread that reads lines one at a time so output printed
        before kubelogin hangs (e.g. the browser URL prompt) is captured before
        the join timeout expires. ssh_connection.send() blocks until the command
        exits and cannot be interrupted by a timeout.

        Args:
            kubectl_cmd (str): Full kubectl command string to execute.
            timeout (int): Maximum seconds to wait for output.

        Returns:
            str: Collected output, which may be partial if the timeout expired first.
        """
        if not self.ssh_connection.is_connected:
            self.ssh_connection.connect()
        _, stdout, _ = self.ssh_connection.client.exec_command(kubectl_cmd, timeout=None)
        stdout.channel.set_combine_stderr(True)
        output_lines = []

        def read_output() -> None:
            output_lines.extend(stdout)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        reader.join(timeout=timeout)
        return "".join(output_lines)

    def run_kubectl_with_browser_login(self, kubeconfig_path: str, login_url: str, username: str, password: str, totp_secret: str = None) -> KubectlResultObject:
        """Start kubectl get pods -A in background and authenticate via Keycloak browser login.

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
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A'"
        self.kill_kubelogin_processes()
        kubectl_thread, output_lines = self.start_kubectl_background_thread(kubectl_cmd, self.ssh_connection)

        get_logger().log_info(f"Navigating to OIDC login URL: {login_url}")
        driver = WebDriverCore()
        keycloak_login_page = KeycloakLoginPage(driver)
        keycloak_login_page.navigate_to_login_url(login_url)
        keycloak_login_page.login(username=username, password=password, totp_secret=totp_secret)

        kubectl_thread.join(timeout=300)
        driver.quit()

        result = KubectlResultObject()
        result.set_output("".join(output_lines))
        return result

    def run_kubectl_with_browser_login_no_mfa(self, kubeconfig_path: str, login_url: str, username: str, password: str) -> KubectlResultObject:
        """Start kubectl get pods -A in background and authenticate via Keycloak without MFA.

        Launches kubectl in a background thread then completes the Keycloak
        login with username and password only. No OTP step is expected because
        the user has no MFA policy configured.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.
            login_url (str): The kubelogin listener URL (e.g. http://[oam_ip]:8000/).
            username (str): Keycloak username.
            password (str): Keycloak password.

        Returns:
            KubectlResultObject: Result containing output and error state.
        """
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A'"
        self.kill_kubelogin_processes()
        kubectl_thread, output_lines = self.start_kubectl_background_thread(kubectl_cmd, self.ssh_connection)

        get_logger().log_info(f"Navigating to OIDC login URL: {login_url}")
        driver = WebDriverCore()
        keycloak_login_page = KeycloakLoginPage(driver)
        keycloak_login_page.navigate_to_login_url(login_url)
        keycloak_login_page.login_no_mfa(username=username, password=password)

        kubectl_thread.join(timeout=300)
        driver.quit()

        result = KubectlResultObject()
        result.set_output("".join(output_lines))
        return result

    def run_kubectl_with_invalid_otp(self, kubeconfig_path: str, login_url: str, username: str, password: str, timeout: int = 30) -> KubectlResultObject:
        """Start kubectl get pods -A in background and attempt Keycloak login with an invalid OTP.

        Launches kubectl in a background thread. The browser submits valid
        credentials but an invalid OTP code. Keycloak rejects the OTP and
        the browser stays on the error page. kubectl hangs waiting for the
        OIDC callback that never arrives. The thread join expires with empty
        output, confirming authentication did not succeed.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.
            login_url (str): The kubelogin listener URL (e.g. http://[oam_ip]:8000/).
            username (str): Keycloak username.
            password (str): Keycloak password.
            timeout (int): Maximum seconds to wait for kubectl output after OTP rejection.

        Returns:
            KubectlResultObject: Result containing kubectl output.
        """
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A'"
        self.kill_kubelogin_processes()
        kubectl_thread, output_lines = self.start_kubectl_background_thread(kubectl_cmd, self.ssh_connection)

        get_logger().log_info(f"Navigating to OIDC login URL: {login_url}")
        driver = WebDriverCore()
        keycloak_login_page = KeycloakLoginPage(driver)
        keycloak_login_page.navigate_to_login_url(login_url)
        keycloak_login_page.login_with_invalid_otp(username=username, password=password)
        driver.quit()

        kubectl_thread.join(timeout=timeout)

        output = "".join(output_lines)
        get_logger().log_info(f"kubectl output after invalid OTP: {output}")
        result = KubectlResultObject()
        result.set_output(output)
        return result

    def run_kubectl_remote_with_browser_login(self, kubeconfig_path: str, username: str, password: str, totp_secret: str = None) -> KubectlResultObject:
        """Run kubectl get pods -A on the test machine and authenticate via Keycloak browser login.

        Launches kubectl as a local subprocess. kubelogin fails to open the
        browser in a headless environment and prints the login URL to stdout.
        A reader thread drains stdout line by line to avoid pipe buffer deadlocks.
        Once the browser URL is detected, Selenium navigates to it and completes
        the Keycloak MFA flow. kubectl and the kubelogin plugin must be installed
        on the local test machine.

        Args:
            kubeconfig_path (str): Local path to the OIDC kubeconfig file.
            username (str): Keycloak username.
            password (str): Keycloak password.
            totp_secret (str): Base32 TOTP secret. Pass None for CONFIGURE_TOTP flow.

        Returns:
            KubectlResultObject: Result containing output and error state.
        """
        kubectl_cmd = ["kubectl", "--kubeconfig", kubeconfig_path, "get", "pods", "-A"]
        proc = subprocess.Popen(kubectl_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        output_lines = []
        login_url = None
        deadline = time.time() + 60

        for line in proc.stdout:
            output_lines.append(line)
            if "Please visit the following URL in your browser" in line:
                parts = line.split("http", 1)
                if len(parts) > 1:
                    login_url = "http" + parts[1].strip()
                break
            if time.time() > deadline:
                break

        remaining_lines = []

        def drain_stdout() -> None:
            for line in proc.stdout:
                remaining_lines.append(line)

        drain_thread = threading.Thread(target=drain_stdout, daemon=True)
        drain_thread.start()

        if login_url is None:
            get_logger().log_error("kubelogin browser URL not found in kubectl output within deadline; aborting login")
            proc.kill()
            drain_thread.join(timeout=10)
            result = KubectlResultObject()
            result.set_output("".join(output_lines))
            return result

        get_logger().log_info(f"kubelogin browser URL: {login_url}")
        driver = WebDriverCore()
        keycloak_login_page = KeycloakLoginPage(driver)
        keycloak_login_page.navigate_to_login_url(login_url)
        keycloak_login_page.login(username=username, password=password, totp_secret=totp_secret)
        driver.quit()

        drain_thread.join(timeout=60)
        proc.wait(timeout=10)
        output_lines.extend(remaining_lines)

        result = KubectlResultObject()
        result.set_output("".join(output_lines))
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
        """Run kubectl get pods -A using the cached OIDC token without browser interaction.

        Uses a timeout to confirm kubectl completes without waiting for a browser
        login prompt. If kubectl hangs beyond the timeout it means kubelogin is
        waiting for browser interaction, which indicates the cached token was not
        usable for silent refresh.

        Args:
            kubeconfig_path (str): Path to the OIDC kubeconfig on the remote host.
            timeout (int): Maximum seconds to wait for kubectl to complete.

        Returns:
            KubectlResultObject: Result containing kubectl output.
        """
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} get pods -A'"
        get_logger().log_info(f"Running kubectl using cached OIDC token (timeout={timeout}s)")
        output = self.execute_kubectl_with_timeout(kubectl_cmd, timeout)
        get_logger().log_info(f"kubectl output: {output}")
        result = KubectlResultObject()
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
        output = self.execute_kubectl_with_timeout(kubectl_cmd, timeout)
        get_logger().log_info(f"kubectl run output: {output}")
        result = KubectlResultObject()
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
        MFA browser flow concurrently.

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
        kubectl_cmd = f"bash -lc 'kubectl --kubeconfig {kubeconfig_path} run {pod_name} --image={image} --restart=Never -n {namespace}'"
        self.kill_kubelogin_processes()
        kubectl_thread, output_lines = self.start_kubectl_background_thread(kubectl_cmd, self.ssh_connection)

        get_logger().log_info(f"Navigating to OIDC login URL: {login_url}")
        driver = WebDriverCore()
        keycloak_login_page = KeycloakLoginPage(driver)
        keycloak_login_page.navigate_to_login_url(login_url)
        keycloak_login_page.login(username=username, password=password, totp_secret=totp_secret)

        kubectl_thread.join(timeout=300)
        driver.quit()

        result = KubectlResultObject()
        result.set_output("".join(output_lines))
        return result

    def run_kubectl_auth_can_i_with_cached_token(self, kubeconfig_path: str, verb: str, resource: str, all_namespaces: bool = False, timeout: int = 30) -> KubectlResultObject:
        """Run kubectl auth can-i using the cached OIDC token without browser interaction.

        Uses a timeout to confirm kubectl completes without waiting for a browser
        login prompt.

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
        output = self.execute_kubectl_with_timeout(kubectl_cmd, timeout)
        get_logger().log_info(f"kubectl auth can-i output: {output}")
        result = KubectlResultObject()
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
