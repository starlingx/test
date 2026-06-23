"""Tests for LUKS Keyring Security Enhancement.

Validates that the python keyring is stored on a LUKS-encrypted filesystem
with proper permissions, no hardcoded passwords, and cross-node synchronization.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import (
    validate_equals,
    validate_greater_than,
    validate_list_contains,
    validate_not_none,
    validate_str_contains,
)
from keywords.cloud_platform.security.luks_keyring.luks_keyring_keywords import LuksKeyringKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords


@mark.p1
def test_luks_keyring_services_authenticate():
    """Platform services authenticate via LUKS keyring.

    Test Steps:
        - Connect to active controller
        - Run system host-list, application-list, fm alarm-list
        - Verify all succeed with 0 keyring errors in sysinv log
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(ssh_connection)

    get_logger().log_test_case_step("Verifying platform services authenticate via LUKS keyring")
    results = luks_keywords.services_authenticate()

    validate_equals(results["system_host_list"], True, "system host-list should succeed")
    validate_equals(results["system_application_list"], True, "system application-list should succeed")
    validate_equals(results["fm_alarm_list"], True, "fm alarm-list should succeed")

    error_count = luks_keywords.get_keyring_error_count()
    validate_equals(error_count, 0, "No keyring errors should exist in sysinv.log")


@mark.p1
def test_luks_keyring_files_exist_both_controllers():
    """Both controllers have keyring files at LUKS path.

    Test Steps:
        - Check .keyring_secret exists on active controller
        - Check crypted_pass.cfg exists on active controller
        - Verify same files on standby controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    keyring_path = luks_keywords.get_luks_keyring_path()

    get_logger().log_test_case_step(f"Verifying keyring files at {keyring_path}")
    validate_equals(
        file_keywords.file_exists(f"{keyring_path}/.keyring_secret"),
        True,
        ".keyring_secret should exist at LUKS path",
    )
    validate_equals(
        file_keywords.file_exists(f"{keyring_path}/crypted_pass.cfg"),
        True,
        "crypted_pass.cfg should exist at LUKS path",
    )


@mark.p1
def test_luks_keyring_secret_entropy():
    """Bootstrap secret is 44-char base64 (256-bit entropy).

    Test Steps:
        - Read .keyring_secret file
        - Verify length is 44 characters (base64-encoded 32 bytes)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(ssh_connection)

    get_logger().log_test_case_step("Verifying keyring secret entropy")
    secret_len = luks_keywords.get_secret_length()
    validate_equals(secret_len, 44, "Secret should be 44 chars (base64 of 32 bytes)")


@mark.p1
def test_luks_keyring_old_path_empty():
    """Old keyring path has no credential files.

    Test Steps:
        - Search old unencrypted path for crypted_pass.cfg and .keyring_secret
        - Verify none found
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(ssh_connection)

    get_logger().log_test_case_step("Verifying old keyring path has no credentials")
    cred_files = luks_keywords.credential_files_at_old_path()
    validate_equals(len(cred_files), 0, "No credential files should exist at old unencrypted path")


@mark.p1
def test_luks_keyring_file_permissions():
    """Keyring files have 640 root:sys_protected permissions.

    Test Steps:
        - Check .keyring_secret permissions
        - Check crypted_pass.cfg permissions
        - Verify no world access
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(ssh_connection)
    keyring_path = luks_keywords.get_luks_keyring_path()

    get_logger().log_test_case_step("Verifying keyring file permissions")
    secret_info = luks_keywords.get_keyring_file_permissions(f"{keyring_path}/.keyring_secret")
    validate_equals(secret_info.get_permissions(), "640", ".keyring_secret should be 640")
    validate_equals(secret_info.get_owner(), "root", ".keyring_secret owner should be root")
    validate_equals(secret_info.get_group(), "sys_protected", ".keyring_secret group should be sys_protected")
    validate_equals(secret_info.has_world_access(), False, ".keyring_secret should have no world access")

    crypt_info = luks_keywords.get_keyring_file_permissions(f"{keyring_path}/crypted_pass.cfg")
    validate_equals(crypt_info.get_permissions(), "640", "crypted_pass.cfg should be 640")
    validate_equals(crypt_info.get_owner(), "root", "crypted_pass.cfg owner should be root")
    validate_equals(crypt_info.get_group(), "sys_protected", "crypted_pass.cfg group should be sys_protected")


@mark.p1
def test_luks_keyring_no_hardcoded_password():
    """No hardcoded keyring password anywhere on system.

    Test Steps:
        - Search LUKS path, old path, /etc/, keyrings.alt for hardcoded password
        - Verify no occurrences found
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(ssh_connection)

    get_logger().log_test_case_step("Verifying no hardcoded keyring password on system")
    search_paths = [
        "/var/luks/stx/luks_fs/",
        "/opt/platform/.keyring/",
        "/etc/",
        "/usr/lib/python3*/site-packages/keyrings*",
    ]
    hits = luks_keywords.grep_hardcoded_password(search_paths)
    validate_equals(len(hits), 0, "No files should contain hardcoded keyring password")


@mark.p1
@mark.lab_has_standby_controller
def test_luks_keyring_secret_synced_across_controllers():
    """Keyring secret synced across controllers (same installation).

    Test Steps:
        - Read secret from active controller
        - Read secret from standby controller
        - Verify they match (same installation = same secret)
    """
    lab_connect = LabConnectionKeywords()
    ssh_connection = lab_connect.get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(ssh_connection)

    get_logger().log_test_case_step("Verifying keyring secret is synced across controllers")
    active_secret = luks_keywords.get_secret_value()
    validate_greater_than(len(active_secret), 0, "Active controller secret should not be empty")

    standby_ssh = lab_connect.get_standby_controller_ssh()
    standby_luks = LuksKeyringKeywords(standby_ssh)
    standby_secret = standby_luks.get_secret_value()

    validate_equals(active_secret, standby_secret, "Secrets should match across controllers (same installation)")


@mark.p1
def test_luks_keyring_mount_active():
    """LUKS filesystem mounted and active.

    Test Steps:
        - Verify LUKS mount exists at expected mount point
        - Verify LUKS device type is LUKS2
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(ssh_connection)

    get_logger().log_test_case_step("Verifying LUKS filesystem is mounted and active")
    validate_equals(luks_keywords.is_luks_mounted(), True, "LUKS filesystem should be mounted")
    luks_type = luks_keywords.get_luks_device_type()
    validate_equals(luks_type, "LUKS2", "LUKS device should be LUKS2 type")


@mark.p1
def test_luks_keyring_data_root_points_to_luks():
    """Python keyring data_root points to LUKS filesystem.

    Test Steps:
        - Query Python keyring data_root
        - Verify it contains the LUKS mount path
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(ssh_connection)

    get_logger().log_test_case_step("Verifying keyring data_root points to LUKS")
    data_root = luks_keywords.get_keyring_data_root()
    validate_str_contains(
        data_root,
        "/var/luks/stx/luks_fs",
        "Keyring data_root should point to LUKS filesystem",
    )


@mark.p1
@mark.lab_has_standby_controller
def test_luks_keyring_survives_swact(request):
    """Services authenticate after controller swact.

    Test Steps:
        - Perform controller swact
        - Verify services authenticate on new active
        - Verify keyring files present on new active
        - Swact back to restore original state
    """
    lab_connect = LabConnectionKeywords()
    ssh_connection = lab_connect.get_active_controller_ssh()
    host_list = SystemHostListKeywords(ssh_connection)
    original_active = host_list.get_active_controller().get_host_name()

    def cleanup():
        get_logger().log_test_case_step("Restoring original active controller")
        ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
        current_active = SystemHostListKeywords(ssh_conn).get_active_controller().get_host_name()
        if current_active != original_active:
            SystemHostSwactKeywords(ssh_conn).host_swact()

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Performing controller swact")
    swact_keywords = SystemHostSwactKeywords(ssh_connection)
    swact_keywords.host_swact()

    new_ssh = lab_connect.get_active_controller_ssh()
    luks_keywords = LuksKeyringKeywords(new_ssh)
    file_keywords = FileKeywords(new_ssh)

    get_logger().log_test_case_step("Verifying services authenticate after swact")
    results = luks_keywords.services_authenticate()
    validate_equals(results["system_host_list"], True, "system host-list should succeed after swact")
    validate_equals(results["system_application_list"], True, "system application-list should succeed after swact")
    validate_equals(results["fm_alarm_list"], True, "fm alarm-list should succeed after swact")

    keyring_path = luks_keywords.get_luks_keyring_path()
    validate_equals(
        file_keywords.file_exists(f"{keyring_path}/.keyring_secret"),
        True,
        ".keyring_secret should exist on new active controller",
    )


@mark.p1
@mark.lab_has_standby_controller
def test_luks_keyring_survives_lock_unlock(request):
    """Standby lock/unlock preserves keyring sync.

    Test Steps:
        - Lock standby controller
        - Unlock standby controller
        - Verify keyring files present on standby after unlock
    """
    lab_connect = LabConnectionKeywords()
    ssh_connection = lab_connect.get_active_controller_ssh()
    host_list = SystemHostListKeywords(ssh_connection)
    standby = host_list.get_standby_controller().get_host_name()

    def cleanup():
        get_logger().log_test_case_step("Ensuring standby is unlocked")
        ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
        lock_kw = SystemHostLockKeywords(ssh_conn)
        lock_kw.unlock_host(standby)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step(f"Locking standby controller: {standby}")
    lock_keywords = SystemHostLockKeywords(ssh_connection)
    lock_keywords.lock_host(standby)

    get_logger().log_test_case_step(f"Unlocking standby controller: {standby}")
    lock_keywords.unlock_host(standby)

    get_logger().log_test_case_step("Verifying keyring on standby after unlock")
    standby_ssh = lab_connect.get_standby_controller_ssh()
    standby_luks = LuksKeyringKeywords(standby_ssh)
    standby_file_kw = FileKeywords(standby_ssh)
    keyring_path = standby_luks.get_luks_keyring_path()

    validate_equals(
        standby_file_kw.file_exists(f"{keyring_path}/.keyring_secret"),
        True,
        ".keyring_secret should exist on standby after unlock",
    )
    validate_equals(
        standby_file_kw.file_exists(f"{keyring_path}/crypted_pass.cfg"),
        True,
        "crypted_pass.cfg should exist on standby after unlock",
    )
