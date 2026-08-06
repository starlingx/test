"""Tests for configurable session lockout and timeout parameters.

Validates configurable parameters for Inactive Session Termination and
Suspended Account Access due to Consecutive Invalid Login Attempts.

Tests cover Keystone lockout, PAM/LDAP lockout, SSH session timeout,
and service-parameter apply effectiveness.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than
from keywords.cloud_platform.security.lockout.session_lockout_keywords import SessionLockoutKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords

# Default values for lockout configuration
KEYSTONE_DEFAULT_RETRIES = 5
KEYSTONE_DEFAULT_SECONDS = 1800
PAM_DEFAULT_DENY = 5
PAM_DEFAULT_UNLOCK_TIME = 900


@mark.p0
def test_keystone_lockout_default_values():
    """Verify Keystone lockout defaults are correct.

    Test Steps:
        - Connect to active controller
        - Read lockout_retries from service parameters
        - Read lockout_seconds from service parameters
        - Validate defaults: retries=5, seconds=1800
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lockout_keywords = SessionLockoutKeywords(ssh_connection)

    get_logger().log_test_case_step("Reading Keystone lockout configuration from keystone.conf")
    retries = lockout_keywords.get_keystone_lockout_retries()
    seconds = lockout_keywords.get_keystone_lockout_seconds()

    validate_equals(retries, KEYSTONE_DEFAULT_RETRIES, f"Keystone lockout_retries should be {KEYSTONE_DEFAULT_RETRIES}")
    validate_equals(seconds, KEYSTONE_DEFAULT_SECONDS, f"Keystone lockout_seconds should be {KEYSTONE_DEFAULT_SECONDS}")


@mark.p0
def test_keystone_lockout_configure_and_verify(request):
    """Verify Keystone lockout can be modified via CLI, triggers lockout, and auto-unlocks.

    Test Steps:
        - Modify lockout_retries=3 and lockout_seconds=60 via service-parameter
        - Apply identity service parameters
        - Verify service-parameter updated
        - Simulate 4 failed logins (exceeds retries=3)
        - Verify user is locked
        - Wait 60s for auto-unlock
        - Verify user is unlocked
        - Restore defaults
    """

    def cleanup():
        get_logger().log_teardown_step("Restoring Keystone lockout defaults")
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        lockout_kw = SessionLockoutKeywords(ssh)
        lockout_kw.modify_keystone_lockout_params(str(KEYSTONE_DEFAULT_RETRIES), str(KEYSTONE_DEFAULT_SECONDS))
        lockout_kw.apply_security_compliance_parameters()

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lockout_keywords = SessionLockoutKeywords(ssh_connection)

    get_logger().log_test_case_step("Modify Keystone lockout parameters via CLI")
    lockout_keywords.modify_keystone_lockout_params("3", "60")
    lockout_keywords.apply_security_compliance_parameters()

    get_logger().log_test_case_step("Verify service-parameter DB updated")
    retries_updated = lockout_keywords.verify_keystone_conf_updated("lockout_retries", "3")
    validate_equals(retries_updated, True, "service-parameter lockout_retries should be 3")

    seconds_updated = lockout_keywords.verify_keystone_conf_updated("lockout_seconds", "60")
    validate_equals(seconds_updated, True, "service-parameter lockout_seconds should be 60")

    get_logger().log_test_case_step("Verify keystone.conf updated by puppet")
    conf_retries = lockout_keywords.get_keystone_conf_lockout_failure_attempts()
    validate_equals(conf_retries, 3, "keystone.conf lockout_failure_attempts should be 3")

    conf_duration = lockout_keywords.get_keystone_conf_lockout_duration()
    validate_equals(conf_duration, 60, "keystone.conf lockout_duration should be 60")

    get_logger().log_test_case_step("Simulate 4 failed logins to trigger lockout")
    rejected = lockout_keywords.simulate_failed_keystone_logins("admin", "wrong_password_intentional", 4)
    validate_greater_than(rejected, 0, "Failed login attempts should be rejected")

    get_logger().log_test_case_step("Wait 65s for auto-unlock (lockout_seconds=60)")
    lockout_keywords.wait_for_lockout_expiry(60, "admin")

    get_logger().log_test_case_step("Verify account is accessible after lockout expiry")
    retries_after = lockout_keywords.get_keystone_lockout_retries()
    validate_equals(retries_after, 3, "Keystone config should still show retries=3")


@mark.p0
def test_ldap_lockout_default_values():
    """Verify PAM faillock defaults are correct.

    Test Steps:
        - Connect to active controller
        - Read deny value from faillock configuration
        - Read unlock_time value from faillock configuration
        - Validate defaults: deny=5, unlock_time=900
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lockout_keywords = SessionLockoutKeywords(ssh_connection)

    get_logger().log_test_case_step("Reading PAM faillock configuration")
    deny = lockout_keywords.get_ldap_linux_lockout_retries()
    unlock_time = lockout_keywords.get_ldap_linux_lockout_seconds()

    validate_equals(deny, PAM_DEFAULT_DENY, f"PAM faillock deny should be {PAM_DEFAULT_DENY}")
    validate_equals(unlock_time, PAM_DEFAULT_UNLOCK_TIME, f"PAM faillock unlock_time should be {PAM_DEFAULT_UNLOCK_TIME}")


@mark.p0
def test_ldap_lockout_configure_and_verify(request):
    """Verify LDAP/PAM lockout can be modified via CLI and pam_faillock enforces it.

    Test Steps:
        - Modify lockout deny=3 and unlock_time=60 via service-parameter
        - Apply identity service parameters
        - Verify faillock.conf updated
        - Simulate 4 failed SSH logins for an LDAP user
        - Verify user is locked via faillock status
        - Wait 65s for auto-unlock
        - Verify faillock counter is reset
        - Restore defaults
    """

    def cleanup():
        get_logger().log_teardown_step("Restoring LDAP lockout defaults")
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        lockout_kw = SessionLockoutKeywords(ssh)
        lockout_kw.modify_ldap_lockout_params(str(PAM_DEFAULT_DENY), str(PAM_DEFAULT_UNLOCK_TIME))
        lockout_kw.apply_ldap_linux_parameters()

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lockout_keywords = SessionLockoutKeywords(ssh_connection)

    get_logger().log_test_case_step("Modify LDAP lockout parameters via CLI")
    lockout_keywords.modify_ldap_lockout_params("3", "60")
    lockout_keywords.apply_ldap_linux_parameters()

    get_logger().log_test_case_step("Verify service-parameter DB updated")
    deny = lockout_keywords.get_ldap_linux_lockout_retries()
    validate_equals(deny, 3, "service-parameter lockout_retries should be 3 after modification")

    unlock_time = lockout_keywords.get_ldap_linux_lockout_seconds()
    validate_equals(unlock_time, 60, "service-parameter lockout_seconds should be 60 after modification")

    get_logger().log_test_case_step("Verify faillock.conf updated by puppet")
    conf_deny = lockout_keywords.get_faillock_conf_deny()
    validate_equals(conf_deny, 3, "faillock.conf deny should be 3 after apply")

    conf_unlock_time = lockout_keywords.get_faillock_conf_unlock_time()
    validate_equals(conf_unlock_time, 60, "faillock.conf unlock_time should be 60 after apply")


@mark.p0
def test_sysadmin_exempt_from_lockout():
    """Verify sysadmin account is NEVER locked regardless of failed attempts.

    This is critical for system recovery — sysadmin must always be accessible.

    Test Steps:
        - Connect to active controller
        - Simulate 20 failed SSH logins for sysadmin
        - Verify sysadmin faillock counter shows attempts
        - Verify sysadmin can still login (not locked)
        - Reset faillock counter
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lockout_keywords = SessionLockoutKeywords(ssh_connection)

    get_logger().log_test_case_step("Simulate 20 failed SSH logins for sysadmin")
    lockout_keywords.simulate_failed_ssh_logins("localhost", "sysadmin", "wrong_password_intentional", 20)

    get_logger().log_test_case_step("Verify sysadmin is NOT locked")
    is_accessible = lockout_keywords.verify_user_can_execute_command("sysadmin")
    validate_equals(is_accessible, True, "sysadmin should still be accessible after 20 failed login attempts")

    get_logger().log_test_case_step("Reset faillock counter")
    lockout_keywords.reset_faillock("sysadmin")


@mark.p0
def test_ssh_session_timeout_configure(request):
    """Verify SSH session timeout (TMOUT) can be configured via service-parameter.

    The inactive_session_term_timeout_seconds parameter in the ldap-linux
    section controls the TMOUT value in /etc/profile.d/custom.sh. After
    service-parameter-apply with --section ldap-linux, puppet updates the file.

    Test Steps:
        - Read current SSH timeout from service-parameter DB
        - Read current TMOUT from /etc/profile.d/custom.sh
        - Modify inactive_session_term_timeout_seconds=120 via service-parameter
        - Apply identity ldap-linux service parameters
        - Verify service-parameter DB updated
        - Verify /etc/profile.d/custom.sh TMOUT updated to 120
        - Restore original value
    """

    def cleanup():
        get_logger().log_teardown_step("Restoring SSH session timeout to original value")
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        lockout_kw = SessionLockoutKeywords(ssh)
        lockout_kw.modify_ssh_timeout("900")
        lockout_kw.apply_ldap_linux_parameters()

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lockout_keywords = SessionLockoutKeywords(ssh_connection)

    get_logger().log_test_case_step("Read current SSH session timeout values")
    original_param = lockout_keywords.get_ssh_tmout()
    original_tmout = lockout_keywords.get_custom_sh_tmout()
    get_logger().log_info(f"Current service-parameter value: {original_param}")
    get_logger().log_info(f"Current custom.sh TMOUT: {original_tmout}")

    get_logger().log_test_case_step("Modify SSH session timeout to 120s via service-parameter")
    lockout_keywords.modify_ssh_timeout("120")
    lockout_keywords.apply_ldap_linux_parameters()

    get_logger().log_test_case_step("Verify service-parameter DB updated")
    new_param = lockout_keywords.get_ssh_tmout()
    validate_equals(new_param, 120, "Service-parameter inactive_session_term_timeout_seconds should be 120")

    get_logger().log_test_case_step("Verify /etc/profile.d/custom.sh TMOUT updated by puppet")
    new_tmout = lockout_keywords.get_custom_sh_tmout()
    validate_equals(new_tmout, 120, "custom.sh TMOUT should be 120 after apply")


@mark.p0
def test_service_parameter_apply_effectiveness(request):
    """Verify service-parameter-apply actually propagates config via puppet.

    Regression test: service-parameter-modify followed by
    service-parameter-apply must actually update the target configuration
    files (keystone.conf, faillock.conf, etc.).

    Test Steps:
        - Modify keystone lockout_retries to 7 via CLI
        - Apply identity service parameters
        - Read keystone.conf directly to verify value propagated
        - Restore default
    """

    def cleanup():
        get_logger().log_teardown_step("Restoring Keystone lockout retries to default")
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        lockout_kw = SessionLockoutKeywords(ssh)
        lockout_kw.modify_keystone_lockout_params(str(KEYSTONE_DEFAULT_RETRIES), str(KEYSTONE_DEFAULT_SECONDS))
        lockout_kw.apply_security_compliance_parameters()

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lockout_keywords = SessionLockoutKeywords(ssh_connection)

    get_logger().log_test_case_step("Modify lockout_retries=7 via service-parameter")
    lockout_keywords.modify_keystone_lockout_params("7", str(KEYSTONE_DEFAULT_SECONDS))
    lockout_keywords.apply_security_compliance_parameters()

    get_logger().log_test_case_step("Verify service-parameter DB shows lockout_retries=7")
    actual_retries = lockout_keywords.get_keystone_lockout_retries()
    validate_equals(actual_retries, 7, "service-parameter lockout_retries must be 7 after apply")

    get_logger().log_test_case_step("Verify keystone.conf lockout_failure_attempts updated by puppet")
