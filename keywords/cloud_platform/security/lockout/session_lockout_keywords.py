"""Keywords for session lockout and timeout configuration verification.

Provides methods to query and verify Keystone lockout parameters,
PAM faillock settings, SSH session timeout (TMOUT), and Horizon
session timeout configuration on StarlingX systems.
"""

import time
from typing import Union

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.service.objects.system_service_parameter_list_output import SystemServiceParameterListOutput
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.files.file_keywords import FileKeywords

CONFIG_OUT_OF_DATE_ALARM_ID = "250.001"


class SessionLockoutKeywords(BaseKeyword):
    """Keywords for session lockout and timeout operations.

    Provides methods to read and verify lockout configuration from
    keystone.conf, PAM faillock, SSH TMOUT, and Horizon session settings.
    """

    # Horizon file-backed session store: files are named
    # <SESSION_COOKIE_NAME><session_key> under SESSION_FILE_PATH.
    _HORIZON_SESSION_COOKIE_NAME = "platformsessionid"
    _HORIZON_SESSION_FILE_PATH = "/var/tmp"

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize session lockout keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection
        self.service_params = SystemServiceParameterKeywords(ssh_connection)
        self.alarm_keywords = AlarmListKeywords(ssh_connection)
        self.file_keywords = FileKeywords(ssh_connection)

    def get_keystone_lockout_retries(self) -> int:
        """Read lockout_retries from identity service parameters.

        Returns:
            int: The configured lockout_retries value.
        """
        output = self.service_params.list_service_parameters(service="identity", section="security_compliance")
        return self._extract_table_value(output, "lockout_retries")

    def get_keystone_lockout_seconds(self) -> int:
        """Read lockout_seconds from identity service parameters.

        Returns:
            int: The configured lockout_seconds value.
        """
        output = self.service_params.list_service_parameters(service="identity", section="security_compliance")
        return self._extract_table_value(output, "lockout_seconds")

    def get_ldap_linux_lockout_retries(self) -> int:
        """Read lockout_retries from ldap-linux service parameters.

        Returns:
            int: The configured lockout retries value (max failed attempts).
        """
        output = self.service_params.list_service_parameters(service="identity", section="ldap-linux")
        return self._extract_table_value(output, "lockout_retries")

    def get_ldap_linux_lockout_seconds(self) -> int:
        """Read lockout_seconds from ldap-linux service parameters.

        Returns:
            int: The configured lockout_seconds value.
        """
        output = self.service_params.list_service_parameters(service="identity", section="ldap-linux")
        return self._extract_table_value(output, "lockout_seconds")

    def get_ssh_tmout(self) -> int:
        """Read the inactive_session_term_timeout_seconds from service parameters.

        This value controls SSH session idle timeout (TMOUT) on the platform.

        Returns:
            int: The configured timeout value in seconds (0 if not set).
        """
        output = self.service_params.list_service_parameters(service="identity", section="security_compliance")
        return self._extract_table_value(output, "inactive_session_term_timeout_seconds")

    def simulate_failed_keystone_logins(self, username: str, password: str, attempts: int) -> int:
        """Simulate failed Keystone login attempts using openstack token issue.

        Args:
            username (str): Username to attempt login with.
            password (str): Incorrect password to use.
            attempts (int): Number of failed attempts to simulate.

        Returns:
            int: Number of attempts that were rejected (HTTP 401 or error).
        """
        rejected_count = 0
        for i in range(attempts):
            get_logger().log_info(f"Simulating failed login attempt {i + 1}/{attempts} for user '{username}'")
            output = self.ssh_connection.send(source_openrc(f"openstack token issue --os-username {username} --os-password '{password}' --os-project-name admin --os-identity-api-version 3 2>&1 || true"))
            raw = "\n".join(output) if isinstance(output, list) else str(output)
            if "Unauthorized" in raw or "HTTP 401" in raw or "Could not find token" in raw or "error" in raw.lower():
                rejected_count += 1
        get_logger().log_info(f"Failed login simulation complete: {rejected_count}/{attempts} rejected")
        return rejected_count

    def is_keystone_user_locked(self, username: str) -> bool:
        """Check if a Keystone user account is currently locked.

        Args:
            username (str): Username to check.

        Returns:
            bool: True if user is locked out.
        """
        output = self.ssh_connection.send(source_openrc(f"openstack user show {username} -f value -c enabled 2>&1"))
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        return "False" in raw

    def get_faillock_status(self, username: str) -> int:
        """Get the current failed attempt count for a user via faillock.

        Args:
            username (str): Username to check.

        Returns:
            int: Number of failed attempts recorded.
        """
        output = self.ssh_connection.send_as_sudo(f"faillock --user {username} 2>/dev/null || true")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        count = 0
        for line in raw.strip().split("\n"):
            if line.strip() and "/" in line and ":" in line:
                count += 1
        return count

    def reset_faillock(self, username: str) -> None:
        """Reset faillock counter for a user.

        Args:
            username (str): Username to reset.
        """
        get_logger().log_info(f"Resetting faillock counter for user '{username}'")
        self.ssh_connection.send_as_sudo(f"faillock --user {username} --reset 2>/dev/null || true")

    def simulate_failed_ssh_logins(self, host: str, username: str, password: str, attempts: int) -> int:
        """Simulate failed SSH login attempts against a host.

        Uses sshpass to attempt logins with an incorrect password.

        Args:
            host (str): Target hostname or IP.
            username (str): Username to attempt login with.
            password (str): Incorrect password to use.
            attempts (int): Number of failed attempts to simulate.

        Returns:
            int: Number of attempts that failed (expected to be all).
        """
        failed_count = 0
        for i in range(attempts):
            get_logger().log_info(f"SSH login attempt {i + 1}/{attempts} for '{username}@{host}'")
            output = self.ssh_connection.send(f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {username}@{host} 'exit' 2>&1")
            raw = "\n".join(output) if isinstance(output, list) else str(output)
            if "Permission denied" in raw or "Authentication failed" in raw or "Connection refused" in raw:
                failed_count += 1
            else:
                rc = self.ssh_connection.get_return_code()
                if rc != 0:
                    failed_count += 1
        get_logger().log_info(f"SSH login simulation: {failed_count}/{attempts} failed")
        return failed_count

    def modify_keystone_lockout_params(self, retries: str, seconds: str) -> None:
        """Modify Keystone lockout parameters via service-parameter CLI.

        Uses modify (parameters exist by default on 26.10+).

        Args:
            retries (str): Number of failed attempts before lockout.
            seconds (str): Duration of lockout in seconds.
        """
        get_logger().log_info(f"Modifying Keystone lockout params: retries={retries}, seconds={seconds}")
        self.service_params.modify_service_parameter("identity", "security_compliance", "lockout_retries", retries)
        self.service_params.modify_service_parameter("identity", "security_compliance", "lockout_seconds", seconds)

    def apply_identity_service_parameters(self, section: str = "") -> None:
        """Apply identity service parameters and wait for config to propagate.

        Section-specific apply is required for correct puppet runtime class
        triggering. A bare apply (no section) may only trigger one section's
        puppet manifest.

        Args:
            section (str): Section to apply. Use 'security_compliance' for
                Keystone lockout or 'ldap-linux' for PAM faillock. Empty
                string applies without section filter.
        """
        if section:
            get_logger().log_info(f"Applying identity service parameters for section {section}")
        else:
            get_logger().log_info("Applying identity service parameters")
        self.service_params.apply_service_parameters("identity", section=section)
        self._wait_for_config_applied()

    def apply_security_compliance_parameters(self) -> None:
        """Apply identity security_compliance service parameters.

        Triggers openstack::keystone::lockout::runtime puppet class which
        updates keystone.conf lockout settings on controllers.
        """
        self.apply_identity_service_parameters(section="security_compliance")

    def apply_ldap_linux_parameters(self) -> None:
        """Apply identity ldap-linux service parameters.

        Triggers platform::faillock::runtime puppet class which updates
        faillock.conf on all nodes (controllers, workers, storage).
        """
        self.apply_identity_service_parameters(section="ldap-linux")

    def modify_ldap_lockout_params(self, retries: str, seconds: str) -> None:
        """Modify LDAP/PAM lockout parameters via service-parameter CLI.

        Args:
            retries (str): Number of failed attempts before lockout.
            seconds (str): Duration of lockout in seconds.
        """
        get_logger().log_info(f"Modifying LDAP lockout params: retries={retries}, seconds={seconds}")
        self.service_params.modify_service_parameter("identity", "ldap-linux", "lockout_retries", retries)
        self.service_params.modify_service_parameter("identity", "ldap-linux", "lockout_seconds", seconds)

    def modify_ssh_timeout(self, timeout_seconds: str) -> None:
        """Modify SSH/session inactive timeout via service-parameter CLI.

        Args:
            timeout_seconds (str): Inactive session timeout in seconds.
        """
        get_logger().log_info(f"Modifying session timeout: {timeout_seconds}s")
        try:
            self.service_params.modify_service_parameter("identity", "security_compliance", "inactive_session_term_timeout_seconds", timeout_seconds)
        except AssertionError:
            self.service_params.add_service_parameter("identity", "security_compliance", "inactive_session_term_timeout_seconds", timeout_seconds)

    def modify_horizon_session_timeout(self, timeout_seconds: str) -> None:
        """Modify the Horizon idle session timeout via service-parameter CLI.

        Horizon's SESSION_TIMEOUT is driven by the identity security_compliance
        inactive_session_term_timeout_seconds service parameter (puppet maps it
        into the dashboard local_settings). There is no dedicated 'horizon'
        service parameter, so this sets the identity parameter that supersedes
        the token expiry with a shorter idle session timeout.

        Args:
            timeout_seconds (str): SESSION_TIMEOUT value in seconds.
        """
        get_logger().log_info(f"Modifying Horizon session timeout (inactive_session_term_timeout_seconds): {timeout_seconds}s")
        self.service_params.modify_service_parameter("identity", "security_compliance", "inactive_session_term_timeout_seconds", timeout_seconds)

    def apply_horizon_service_parameters(self) -> None:
        """Apply the identity security_compliance parameters that drive Horizon.

        The Horizon SESSION_TIMEOUT is applied through the identity
        security_compliance section (there is no 'horizon' service), so this
        applies that section and waits for config to propagate.
        """
        get_logger().log_info("Applying identity security_compliance service parameters for Horizon session timeout")
        self.apply_security_compliance_parameters()

    def get_horizon_session_timeout(self) -> int:
        """Read SESSION_TIMEOUT from Horizon local_settings.

        The session timeout is configured in the StarlingX customization file
        at /etc/openstack-dashboard/local_settings.d/_30_stx_local_settings.py.
        This value is updated by puppet when inactive_session_term_timeout_seconds
        is modified via service-parameter-apply identity.

        Returns:
            int: The configured SESSION_TIMEOUT value in seconds.
        """
        lines = self._grep_config_with_sudo("/etc/openstack-dashboard/local_settings.d/_30_stx_local_settings.py", "SESSION_TIMEOUT")
        return self._extract_ini_value(lines, "SESSION_TIMEOUT")

    def is_websso_oidc_enabled(self) -> bool:
        """Check whether Horizon WebSSO/OIDC federated login is enabled.

        The session idle-timeout fix lives in the shared Horizon middleware and
        governs any authenticated session regardless of the authentication
        method. This confirms the OIDC/WebSSO login path is active on the system
        (WEBSSO_ENABLED = True and an 'oidc' auth choice is offered), so the same
        idle-timeout behavior applies to OIDC/WebSSO Horizon sessions.

        Returns:
            bool: True if WebSSO is enabled and an OIDC choice is configured.
        """
        config_file = "/etc/openstack-dashboard/local_settings.d/_30_stx_local_settings.py"
        websso_lines = self._grep_config_with_sudo(config_file, "WEBSSO_ENABLED")
        websso_raw = "\n".join(websso_lines) if isinstance(websso_lines, list) else str(websso_lines)
        websso_enabled = "true" in websso_raw.lower()

        oidc_lines = self._grep_config_with_sudo(config_file, "oidc")
        oidc_raw = "\n".join(oidc_lines) if isinstance(oidc_lines, list) else str(oidc_lines)
        oidc_choice = "oidc" in oidc_raw.lower()

        get_logger().log_info(f"WebSSO enabled={websso_enabled}, OIDC choice present={oidc_choice}")
        return websso_enabled and oidc_choice

    def is_horizon_login_page_ready(self) -> bool:
        """Check whether the Horizon login page is served and contains a CSRF token.

        Fetches the login page and confirms it returns HTTP 200 with a
        csrfmiddlewaretoken field. Used to detect when Horizon is fully up
        (e.g. after a service-parameter apply that restarts the dashboard),
        so a login is not attempted while the backend returns 5xx.

        Returns:
            bool: True if the login page is ready with a CSRF token present.
        """
        lab_config = ConfigurationManager.get_lab_config()
        horizon_url = lab_config.get_horizon_url().rstrip("/")
        login_url = f"{horizon_url}/auth/login/"

        output = self.ssh_connection.send(f"curl -sk -o /dev/null -w '%{{http_code}}' '{login_url}'")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        status_code = raw.strip().split("\n")[-1].strip()
        if status_code != "200":
            get_logger().log_info(f"Horizon login page not ready (HTTP {status_code})")
            return False

        probe_page = "/tmp/horizon_login_probe.html"
        self.ssh_connection.send(f"curl -sk '{login_url}' -o {probe_page}")
        csrf_token = self._extract_horizon_csrf_token(probe_page)
        ready = len(csrf_token) > 0
        get_logger().log_info(f"Horizon login page ready={ready} (HTTP 200, csrf_present={ready})")
        return ready

    def wait_for_horizon_ready(self, timeout: int = 180) -> None:
        """Wait until the Horizon login page is ready to accept a login.

        Polls the login page until it returns HTTP 200 with a CSRF token,
        allowing time for the dashboard to come back up after a
        service-parameter apply restarts it.

        Args:
            timeout (int): Maximum seconds to wait for Horizon to be ready.
        """
        get_logger().log_info("Waiting for Horizon login page to be ready")
        validate_equals_with_retry(
            function_to_execute=self.is_horizon_login_page_ready,
            expected_value=True,
            validation_description="Horizon login page ready (HTTP 200 with CSRF token)",
            timeout=timeout,
            polling_sleep_time=10,
        )

    def establish_horizon_session_with_effective_timeout(self, session_timeout: int, margin: int = 30, timeout: int = 300) -> str:
        """Establish a Horizon session once the running dashboard honors the timeout.

        After a service-parameter apply, the config file is updated before the
        running Horizon reloads, and the dashboard briefly returns 5xx while it
        restarts. This logs in repeatedly until a freshly created session's
        stored expiry reflects the configured SESSION_TIMEOUT (capped at
        session_timeout + margin), so the caller gets a session that the running
        dashboard actually governs with the new idle timeout.

        Args:
            session_timeout (int): Expected SESSION_TIMEOUT in seconds.
            margin (int): Allowed slack above session_timeout in seconds.
            timeout (int): Maximum seconds to wait for the effective timeout.

        Returns:
            str: Path to the cookie jar holding the effective authenticated session.
        """
        get_logger().log_info(f"Establishing Horizon session until effective timeout is <= {session_timeout + margin}s")

        def _login_and_check_expiry() -> bool:
            cookie_jar = self.establish_horizon_session()
            if not self.is_horizon_session_authenticated(cookie_jar):
                return False
            return self.is_horizon_session_expiry_capped(cookie_jar, session_timeout, margin)

        validate_equals_with_retry(
            function_to_execute=_login_and_check_expiry,
            expected_value=True,
            validation_description="Horizon running dashboard honors the configured SESSION_TIMEOUT",
            timeout=timeout,
            polling_sleep_time=15,
        )
        return "/tmp/horizon_session_cookies.txt"

    def establish_horizon_session(self, username: str = "", password: str = "") -> str:
        """Establish an authenticated Horizon session and return the cookie jar path.

        Waits for Horizon to be ready, then performs a full Horizon keystone
        login over HTTP from the active controller using curl: fetches the
        login page to obtain the CSRF token and session cookie, then POSTs
        credentials. The resulting authenticated cookies are stored in a cookie
        jar file on the controller so that subsequent requests reuse the same
        session.

        Args:
            username (str): Horizon username. Defaults to the lab Horizon user.
            password (str): Horizon password. Defaults to the lab Horizon password.

        Returns:
            str: Path to the cookie jar file holding the authenticated session.
        """
        lab_config = ConfigurationManager.get_lab_config()
        horizon_url = lab_config.get_horizon_url().rstrip("/")
        credentials = lab_config.get_horizon_credentials()
        user = username if username else credentials.get_user_name()
        secret = password if password else credentials.get_password()

        cookie_jar = "/tmp/horizon_session_cookies.txt"
        login_page = "/tmp/horizon_login_page.html"
        login_url = f"{horizon_url}/auth/login/"

        self.wait_for_horizon_ready()
        get_logger().log_info(f"Establishing Horizon session for user '{user}' at {login_url}")

        # GET the login page to obtain the CSRF token and initial session cookie.
        self.ssh_connection.send(f"curl -sk -c {cookie_jar} -b {cookie_jar} '{login_url}' -o {login_page}")
        csrf_token = self._extract_horizon_csrf_token(login_page)
        region = self._extract_horizon_login_region(login_page)

        # POST credentials with the CSRF token and region to authenticate.
        self.ssh_connection.send(f"curl -sk -c {cookie_jar} -b {cookie_jar} " f"-e '{login_url}' " f"-d 'csrfmiddlewaretoken={csrf_token}' " f"--data-urlencode 'username={user}' " f"--data-urlencode 'password={secret}' " f"--data-urlencode 'region={region}' " f"'{login_url}' -o /dev/null")
        return cookie_jar

    def is_horizon_session_authenticated(self, cookie_jar: str) -> bool:
        """Check whether a Horizon session cookie jar is still authenticated.

        Requests the Horizon dashboard root with the stored cookies and follows
        redirects. An authenticated session lands on a dashboard page (its
        effective URL is NOT the login page); a terminated session is
        redirected back to ``/auth/login/``. Inspecting the final effective URL
        is more reliable than a fixed status code, because the landing page and
        RBAC differ by user (an admin may receive 403/302 on ``/project/`` while
        still authenticated).

        Args:
            cookie_jar (str): Path to the cookie jar file on the controller.

        Returns:
            bool: True if the session is still authenticated, False if terminated.
        """
        lab_config = ConfigurationManager.get_lab_config()
        horizon_url = lab_config.get_horizon_url().rstrip("/")
        dashboard_url = f"{horizon_url}/"

        output = self.ssh_connection.send(f"curl -sk -L -o /dev/null -b {cookie_jar} -w '%{{http_code}} %{{url_effective}}' '{dashboard_url}'")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        result = raw.strip().split("\n")[-1].strip()
        get_logger().log_info(f"Horizon dashboard request result: {result}")
        status_code = result.split(" ", 1)[0].strip()
        redirected_to_login = "/auth/login" in result
        # Authenticated only when the dashboard returns HTTP 200 and did not
        # redirect to the login page. A 5xx (e.g. Horizon restarting) is NOT
        # authenticated and must not be treated as a valid session.
        return status_code == "200" and not redirected_to_login

    def is_horizon_session_expiry_capped(self, cookie_jar: str, session_timeout: int, margin: int = 30) -> bool:
        """Check that a Horizon session expiry is capped at SESSION_TIMEOUT.

        Reads the session's stored expiry age and confirms it does not exceed
        the configured SESSION_TIMEOUT (within a small margin). Before the fix,
        the session expiry followed the longer token lifetime and SESSION_TIMEOUT
        was ignored; after the fix, the shorter SESSION_TIMEOUT supersedes it.
        This is checked deterministically from the stored session, avoiding
        polling requests that would themselves refresh the session expiry.

        Args:
            cookie_jar (str): Path to the authenticated session cookie jar.
            session_timeout (int): Configured SESSION_TIMEOUT in seconds.
            margin (int): Allowed slack above session_timeout in seconds.

        Returns:
            bool: True if the stored expiry age is at or below
                session_timeout + margin, False otherwise.
        """
        expiry_age = self.get_horizon_session_expiry_age(cookie_jar)
        capped = 0 < expiry_age <= session_timeout + margin
        get_logger().log_info(f"Horizon session expiry_age={expiry_age}s, SESSION_TIMEOUT={session_timeout}s, capped={capped}")
        return capped

    def ajax_request_extends_session(self, cookie_jar: str, settle_seconds: int = 5) -> bool:
        """Check whether an AJAX request extends an authenticated Horizon session.

        Sends a single request carrying the ``X-Requested-With: XMLHttpRequest``
        header (as browser background polling does) and compares the Horizon
        session store file modification time before and after. When the session
        idle timeout fix is present, AJAX requests must NOT refresh the session
        expiry, so the session file modification time is unchanged.

        Args:
            cookie_jar (str): Path to the authenticated session cookie jar.
            settle_seconds (int): Seconds to wait between baseline and the AJAX
                request so a genuine expiry refresh would produce a different
                modification time.

        Returns:
            bool: True if the AJAX request extended the session (modification
                time changed), False if it did not extend the session.
        """
        lab_config = ConfigurationManager.get_lab_config()
        horizon_url = lab_config.get_horizon_url().rstrip("/")
        ajax_url = f"{horizon_url}/admin/"

        get_logger().log_info("Checking that an AJAX request does not extend the Horizon session")
        mtime_before = self._get_horizon_session_file_mtime(cookie_jar)

        time.sleep(settle_seconds)
        self.ssh_connection.send(f"curl -sk -o /dev/null -b {cookie_jar} -H 'X-Requested-With: XMLHttpRequest' '{ajax_url}'")

        mtime_after = self._get_horizon_session_file_mtime(cookie_jar)
        extended = mtime_before != mtime_after
        get_logger().log_info(f"AJAX session file mtime before={mtime_before} after={mtime_after} extended={extended}")
        return extended

    def non_ajax_request_extends_session(self, cookie_jar: str, settle_seconds: int = 5) -> bool:
        """Check whether a normal (non-AJAX) request extends the Horizon session.

        Sends a single request without the ``X-Requested-With`` header (genuine
        user navigation) and compares the Horizon session store file
        modification time before and after. Real user activity is expected to
        refresh the session expiry, so the modification time should change.
        This is the positive counterpart to ``ajax_request_extends_session``.

        Args:
            cookie_jar (str): Path to the authenticated session cookie jar.
            settle_seconds (int): Seconds to wait between baseline and the
                request so a genuine expiry refresh produces a different
                modification time.

        Returns:
            bool: True if the request extended the session (modification time
                changed), False otherwise.
        """
        lab_config = ConfigurationManager.get_lab_config()
        horizon_url = lab_config.get_horizon_url().rstrip("/")
        page_url = f"{horizon_url}/admin/"

        get_logger().log_info("Checking that a non-AJAX request extends the Horizon session")
        mtime_before = self._get_horizon_session_file_mtime(cookie_jar)

        time.sleep(settle_seconds)
        self.ssh_connection.send(f"curl -sk -o /dev/null -b {cookie_jar} '{page_url}'")

        mtime_after = self._get_horizon_session_file_mtime(cookie_jar)
        extended = mtime_before != mtime_after
        get_logger().log_info(f"Non-AJAX session file mtime before={mtime_before} after={mtime_after} extended={extended}")
        return extended

    def _get_horizon_session_file_mtime(self, cookie_jar: str) -> int:
        """Get the modification time of the Django session file for a session.

        Horizon uses a file-backed session store whose files are named
        ``<SESSION_COOKIE_NAME><session_key>`` under the configured
        ``SESSION_FILE_PATH``. The session key is read from the cookie jar and
        the file modification time is read with sudo (the files are owned by
        the web server user). The modification time acts as a proxy for the
        last time the session expiry was refreshed.

        Args:
            cookie_jar (str): Path to the authenticated session cookie jar.

        Returns:
            int: Session file modification time as a Unix timestamp, or 0 if
                the session key or file could not be resolved.
        """
        session_key = self._get_horizon_session_key(cookie_jar)
        if not session_key:
            return 0

        session_file = f"{self._HORIZON_SESSION_FILE_PATH}/{self._HORIZON_SESSION_COOKIE_NAME}{session_key}"
        mtime_output = self.ssh_connection.send_as_sudo(f"stat -c %Y {session_file} 2>/dev/null || echo 0")
        raw_mtime = "\n".join(mtime_output) if isinstance(mtime_output, list) else str(mtime_output)
        for token in reversed(raw_mtime.strip().split("\n")):
            candidate = token.strip()
            if candidate.isdigit():
                return int(candidate)
        return 0

    def _get_horizon_session_key(self, cookie_jar: str) -> str:
        """Read the Horizon session key from a cookie jar file.

        Args:
            cookie_jar (str): Path to the cookie jar file on the controller.

        Returns:
            str: The session key value, or empty string if not present.
        """
        output = self.ssh_connection.send(f"awk '/{self._HORIZON_SESSION_COOKIE_NAME}/ {{print $NF}}' {cookie_jar} | tail -1")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        return raw.strip().split("\n")[-1].strip()

    def get_horizon_session_expiry_age(self, cookie_jar: str) -> int:
        """Read the stored expiry age (seconds) of a Horizon session.

        Loads the file-backed Django session for the authenticated cookie jar
        and returns ``SessionStore.get_expiry_age()``. This is the effective
        idle lifetime the server assigned to the session. When SESSION_TIMEOUT
        is shorter than the token lifetime, the fix caps this value at
        SESSION_TIMEOUT; the pre-fix behavior left it at the token lifetime.
        Reading the stored value is deterministic and does not require polling
        with requests that would themselves refresh the session.

        Args:
            cookie_jar (str): Path to the authenticated session cookie jar.

        Returns:
            int: The session expiry age in seconds, or 0 if it could not be read.
        """
        session_key = self._get_horizon_session_key(cookie_jar)
        if not session_key:
            return 0

        python_snippet = "import os,django;" "os.environ.setdefault('DJANGO_SETTINGS_MODULE','openstack_dashboard.settings');" "django.setup();" "from django.contrib.sessions.backends.file import SessionStore;" "import sys;" "s=SessionStore(session_key=sys.argv[1]);" "s.load();" "print(s.get_expiry_age())"
        command = f'DJANGO_SETTINGS_MODULE=openstack_dashboard.settings python3 -c "{python_snippet}" {session_key} 2>/dev/null'
        output = self.ssh_connection.send_as_sudo(command)
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        for token in reversed(raw.strip().split("\n")):
            candidate = token.strip()
            if candidate.isdigit():
                return int(candidate)
        return 0

    def _extract_horizon_csrf_token(self, login_page: str) -> str:
        """Extract the CSRF token from the Horizon login page HTML.

        The login form embeds a hidden input
        ``<input ... name="csrfmiddlewaretoken" value="...">`` that must be
        echoed back on the authentication POST. Reading the value from the
        cookie is not reliable, so it is parsed from the rendered login page.

        Args:
            login_page (str): Path to the saved login page HTML on the controller.

        Returns:
            str: The csrfmiddlewaretoken value, or empty string if not found.
        """
        output = self.ssh_connection.send(f'grep -oE \'name="csrfmiddlewaretoken"[^>]*value="[^"]+"\' {login_page} | grep -oE \'value="[^"]+"\' | head -1 | sed \'s/value="//;s/"//\'')
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        return raw.strip().split("\n")[-1].strip()

    def _extract_horizon_login_region(self, login_page: str) -> str:
        """Extract the region value from the Horizon login page HTML.

        The login form includes a hidden ``region`` input whose value must be
        submitted with the credentials. Defaults to ``default`` when the field
        is absent.

        Args:
            login_page (str): Path to the saved login page HTML on the controller.

        Returns:
            str: The region value, or 'default' if not found.
        """
        output = self.ssh_connection.send(f'grep -oE \'name="region"[^>]*value="[^"]+"\' {login_page} | grep -oE \'value="[^"]+"\' | head -1 | sed \'s/value="//;s/"//\'')
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        region = raw.strip().split("\n")[-1].strip()
        return region if region else "default"

    def apply_platform_service_parameters(self) -> None:
        """Apply platform service parameters and wait for config to propagate."""
        get_logger().log_info("Applying platform service parameters")
        self.service_params.apply_service_parameters("platform")
        self._wait_for_config_applied()

    def verify_keystone_conf_updated(self, parameter: str, expected_value: str) -> bool:
        """Verify a service parameter value matches expected after apply.

        Checks the service-parameter DB (not the config file).

        Args:
            parameter (str): Parameter name (e.g., lockout_retries).
            expected_value (str): Expected value.

        Returns:
            bool: True if the parameter matches the expected value.
        """
        output = self.service_params.list_service_parameters(service="identity", section="security_compliance")
        for param in output.get_parameters():
            if param.get_name() == parameter:
                return param.get_value() == expected_value
        return False

    def get_keystone_conf_lockout_failure_attempts(self) -> int:
        """Read lockout_failure_attempts directly from /etc/keystone/keystone.conf.

        This verifies that puppet actually wrote the value to the config file
        after service-parameter-apply (regression for service-parameter apply).

        Returns:
            int: The lockout_failure_attempts value from keystone.conf, or 0 if not found.
        """
        lines = self._grep_config_with_sudo("/etc/keystone/keystone.conf", "^lockout_failure_attempts")
        return self._extract_ini_value(lines, "lockout_failure_attempts")

    def get_keystone_conf_lockout_duration(self) -> int:
        """Read lockout_duration directly from /etc/keystone/keystone.conf.

        This verifies that puppet actually wrote the value to the config file
        after service-parameter-apply (regression for service-parameter apply).

        Returns:
            int: The lockout_duration value from keystone.conf, or 0 if not found.
        """
        lines = self._grep_config_with_sudo("/etc/keystone/keystone.conf", "^lockout_duration")
        return self._extract_ini_value(lines, "lockout_duration")

    def get_faillock_conf_deny(self) -> int:
        """Read deny value directly from /etc/security/faillock.conf.

        This verifies that puppet actually wrote the value to the config file
        after service-parameter-apply for ldap-linux section.

        Returns:
            int: The deny value from faillock.conf, or 0 if not found.
        """
        lines = self._grep_config_with_sudo("/etc/security/faillock.conf", "^deny")
        return self._extract_key_value_from_lines(lines, "deny")

    def get_faillock_conf_unlock_time(self) -> int:
        """Read unlock_time value directly from /etc/security/faillock.conf.

        This verifies that puppet actually wrote the value to the config file
        after service-parameter-apply for ldap-linux section.

        Returns:
            int: The unlock_time value from faillock.conf, or 0 if not found.
        """
        lines = self._grep_config_with_sudo("/etc/security/faillock.conf", "^unlock_time")
        return self._extract_key_value_from_lines(lines, "unlock_time")

    def wait_for_lockout_expiry(self, lockout_seconds: int, username: str, margin: int = 10) -> bool:
        """Wait for a lockout period to expire by polling until authentication succeeds.

        Args:
            lockout_seconds (int): Expected lockout duration.
            username (str): Username to test authentication for.
            margin (int): Extra seconds to allow beyond lockout_seconds.

        Returns:
            bool: True if account became accessible within timeout.
        """
        get_logger().log_info(f"Polling for lockout expiry (max {lockout_seconds + margin}s)")
        deadline = time.time() + lockout_seconds + margin
        while time.time() < deadline:
            output = self.ssh_connection.send(source_openrc(f"openstack token issue --os-username {username} --os-password 'placeholder' --os-project-name admin --os-identity-api-version 3 2>&1"))
            raw = "\n".join(output) if isinstance(output, list) else str(output)
            if "locked" not in raw.lower() and "maximum" not in raw.lower():
                get_logger().log_info("Account no longer locked — lockout expired")
                return True
            time.sleep(5)
        get_logger().log_info("Lockout expiry wait timed out")
        return False

    def verify_user_can_execute_command(self, username: str) -> bool:
        """Verify that the current SSH session can still execute commands.

        Used to confirm that the user (e.g., sysadmin) is not locked out.

        Args:
            username (str): Expected username from whoami output.

        Returns:
            bool: True if the session is active and user matches.
        """
        output = self.ssh_connection.send("whoami")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        return username in raw

    def get_sudo_lockout_message(self, username: str) -> str:
        """Attempt sudo as a locked-out user and capture the error message.

        After pam_faillock locks a user, sudo should report a lockout message
        rather than the confusing "incorrect password" error.

        Args:
            username (str): Username to attempt sudo as.

        Returns:
            str: The error/output message from the sudo attempt.
        """
        get_logger().log_info(f"Attempting sudo as locked-out user '{username}'")
        output = self.ssh_connection.send_as_sudo(f"su - {username} -c 'sudo -n whoami' 2>&1 || true")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        return raw

    def get_subcloud_keystone_lockout_retries(self, subcloud_ssh: SSHConnection) -> int:
        """Read lockout_failure_attempts from keystone.conf on a subcloud.

        Args:
            subcloud_ssh (SSHConnection): SSH connection to the subcloud controller.

        Returns:
            int: The configured lockout_failure_attempts value on the subcloud.
        """
        output = subcloud_ssh.send_as_sudo("grep -E '^lockout_failure_attempts' /etc/keystone/keystone.conf || true")
        return self._extract_ini_value(output, "lockout_failure_attempts")

    def get_subcloud_keystone_lockout_seconds(self, subcloud_ssh: SSHConnection) -> int:
        """Read lockout_duration from keystone.conf on a subcloud.

        Args:
            subcloud_ssh (SSHConnection): SSH connection to the subcloud controller.

        Returns:
            int: The configured lockout_duration value on the subcloud.
        """
        output = subcloud_ssh.send_as_sudo("grep -E '^lockout_duration' /etc/keystone/keystone.conf || true")
        return self._extract_ini_value(output, "lockout_duration")

    def _extract_table_value(self, output: SystemServiceParameterListOutput, parameter_name: str) -> int:
        """Extract a parameter value from SystemServiceParameterListOutput.

        Args:
            output (SystemServiceParameterListOutput): The service parameter list output.
            parameter_name (str): The parameter name to find.

        Returns:
            int: The parameter value as integer, or 0 if not found.
        """
        for param in output.get_parameters():
            if param.get_name() == parameter_name:
                try:
                    return int(param.get_value())
                except ValueError:
                    return 0
        return 0

    def _grep_config_with_sudo(self, file_path: str, pattern: str) -> str:
        """Read matching lines from a root-owned config file using sudo grep.

        Used for large config files (keystone.conf, local_settings) where
        reading the entire file would exceed SSH buffer limits.

        Args:
            file_path (str): Absolute path to the config file.
            pattern (str): Grep-compatible regex pattern.

        Returns:
            str: Matching lines from the file.
        """
        return self.file_keywords.grep_file_with_sudo(file_path, pattern)

    def _wait_for_config_applied(self, timeout: int = 60, interval: int = 10) -> None:
        """Wait for identity service-parameter-apply to take effect.

        After service-parameter-apply, waits for the config-out-of-date alarm
        (250.001) on controllers to clear. If no controller alarm appears,
        waits a brief period for the apply to propagate.

        Args:
            timeout (int): Maximum seconds to wait.
            interval (int): Seconds between polls.
        """
        get_logger().log_info("Waiting for service-parameter apply to take effect")
        time.sleep(10)

        deadline = time.time() + timeout
        while time.time() < deadline:
            alarms = self.alarm_keywords.alarm_list()
            controller_config_alarm = False
            for alarm in alarms:
                if alarm.get_alarm_id() == CONFIG_OUT_OF_DATE_ALARM_ID:
                    entity = alarm.get_entity_id()
                    if "controller" in entity:
                        controller_config_alarm = True
                        break
            if not controller_config_alarm:
                get_logger().log_info("No controller config-out-of-date alarm — apply complete")
                return
            get_logger().log_info(f"Controller config alarm still active, waiting {interval}s")
            time.sleep(interval)

        get_logger().log_info("Config apply wait timed out, proceeding")

    def _extract_ini_value(self, lines: Union[str, list], key: str) -> int:
        """Extract an integer value from INI-style config file lines.

        Handles formats: 'key=value', 'key = value', and skips comments.

        Args:
            lines (Union[str, list]): File content lines.
            key (str): The parameter name to find.

        Returns:
            int: Parsed integer value, or 0 if not found.
        """
        raw = "\n".join(lines) if isinstance(lines, list) else str(lines)
        for line in raw.strip().split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if key in stripped and "=" in stripped:
                # Handle both 'key=value' and 'key = value'
                value_str = stripped.split("=", 1)[1].strip()
                try:
                    return int(value_str)
                except ValueError:
                    continue
        return 0

    def _extract_key_value_from_lines(self, lines: Union[str, list], key: str) -> int:
        """Extract a key=value integer from faillock-style config lines.

        Handles formats like 'deny = 5', 'deny=5', and 'unlock_time = 900'.

        Args:
            lines (Union[str, list]): File content lines.
            key (str): The key to search for.

        Returns:
            int: Parsed integer value, or 0 if not found.
        """
        raw = "\n".join(lines) if isinstance(lines, list) else str(lines)
        for line in raw.strip().split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Match 'key = value' or 'key=value' — key must be at start of line
            if stripped.startswith(key) and "=" in stripped:
                value_str = stripped.split("=", 1)[1].strip()
                try:
                    return int(value_str)
                except ValueError:
                    continue
        return 0
