"""Keywords for session lockout and timeout configuration verification.

Provides methods to query and verify Keystone lockout parameters,
PAM faillock settings, SSH session timeout (TMOUT), and Horizon
session timeout configuration on StarlingX systems.
"""

import time
from typing import Union

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.service.objects.system_service_parameter_list_output import SystemServiceParameterListOutput
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords

CONFIG_OUT_OF_DATE_ALARM_ID = "250.001"


class SessionLockoutKeywords(BaseKeyword):
    """Keywords for session lockout and timeout operations.

    Provides methods to read and verify lockout configuration from
    keystone.conf, PAM faillock, SSH TMOUT, and Horizon session settings.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize session lockout keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection
        self.service_params = SystemServiceParameterKeywords(ssh_connection)
        self.alarm_keywords = AlarmListKeywords(ssh_connection)

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
            output = self.ssh_connection.send(
                f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {username}@{host} 'exit' 2>&1"
            )
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
        """Modify Horizon session timeout via service-parameter CLI.

        Uses try/except pattern: attempts modify first, falls back to add
        if the parameter does not yet exist.

        Args:
            timeout_seconds (str): SESSION_TIMEOUT value in seconds.
        """
        get_logger().log_info(f"Modifying Horizon session timeout: {timeout_seconds}s")
        output = self.service_params.list_service_parameters(service="horizon", section="auth")
        param_exists = False
        for param in output.get_parameters():
            if param.get_name() == "session_timeout":
                param_exists = True
                break
        if param_exists:
            self.service_params.modify_service_parameter("horizon", "auth", "session_timeout", timeout_seconds)
        else:
            self.service_params.add_service_parameter("horizon", "auth", "session_timeout", timeout_seconds)

    def apply_horizon_service_parameters(self) -> None:
        """Apply horizon service parameters and wait for config to propagate."""
        get_logger().log_info("Applying horizon service parameters")
        self.service_params.apply_service_parameters("horizon")
        self._wait_for_config_applied()

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
            output = self.ssh_connection.send(source_openrc(
                f"openstack token issue --os-username {username} --os-password 'placeholder' --os-project-name admin --os-identity-api-version 3 2>&1"
            ))
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
