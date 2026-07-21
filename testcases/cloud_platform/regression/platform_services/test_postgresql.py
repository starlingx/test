from _pytest.fixtures import FixtureRequest
from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.events.fm_event_list_keywords import FmEventListKeywords
from keywords.cloud_platform.postgresql.postgresql_keywords import PostgresqlKeywords
from keywords.cloud_platform.sm.sm_keywords import SMKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.health_query.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_show_keywords import SystemHostShowKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.linux.drbd.drbd_keywords import DrbdKeywords
from keywords.linux.log.log_grep_keywords import LogGrepKeywords
from keywords.linux.mount.mount_keywords import MountKeywords
from keywords.openstack.openstack.secret.openstack_secret_keywords import OpenstackSecretKeywords
from keywords.openstack.openstack.user.openstack_user_keywords import OpenstackUserListKeywords


@mark.p2
def test_postgresql_health():
    """Verify PostgreSQL service health and system readiness.

    Validates that the PostgreSQL database service is properly installed,
    running, accepting connections, and that the overall system health
    is in a good state.

    Preconditions:
        - System is installed and accessible
        - PostgreSQL is deployed as part of the platform

    Setup:
        - None

    Test Steps:
        1. Verify psql client is installed
        2. Verify PostgreSQL is accepting connections via pg_isready
        3. Verify postgres service is enabled-active via SM
        4. Verify system health-query reports healthy state

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify psql client is installed")
    pg_keywords = PostgresqlKeywords(ssh_connection)
    psql_version = pg_keywords.get_psql_version()
    validate_str_contains(psql_version, "PostgreSQL", "psql version output contains PostgreSQL")
    get_logger().log_info(f"psql version: {psql_version}")

    get_logger().log_test_case_step("Verify PostgreSQL is accepting connections via pg_isready")
    pg_isready_output = pg_keywords.get_pg_isready()
    validate_equals(
        pg_isready_output.is_accepting_connections(),
        True,
        "PostgreSQL is accepting connections",
    )

    get_logger().log_test_case_step("Verify postgres service is enabled-active via SM")
    sm_keywords = SMKeywords(ssh_connection)
    validate_equals(
        sm_keywords.is_service_enabled("postgres"),
        True,
        "postgres service is enabled-active",
    )
    get_logger().log_info("postgres service: enabled-active")

    get_logger().log_test_case_step("Verify system health-query reports healthy state")
    health_output = SystemHealthQueryKeywords(ssh_connection).get_health_status()
    failed_checks = health_output.get_failed_checks()
    for check in failed_checks:
        get_logger().log_warning(f"Health check failed: {check.get_check_name()} - {check.get_status()}" + (f" ({check.get_reason()})" if check.get_reason() else ""))
    validate_equals(len(failed_checks), 0, f"No health checks should fail, but {len(failed_checks)} failed")
    get_logger().log_info(f"System health: {len(health_output.get_all_checks())} checks passed")


@mark.p2
def test_postgresql_database_connectivity():
    """Verify PostgreSQL platform databases exist, are queryable, and expected roles exist.

    Validates that the core platform databases (sysinv, keystone, barbican, fm)
    are present, can be queried successfully, and that the expected database
    roles are configured.

    Preconditions:
        - System is installed and accessible
        - PostgreSQL is deployed as part of the platform

    Setup:
        - None

    Test Steps:
        1. Verify platform databases exist via psql -l
        2. Verify each platform database is queryable
        3. Verify expected PostgreSQL roles exist

    Teardown:
        - None
    """
    expected_databases = ["sysinv", "keystone", "barbican", "fm"]
    expected_roles = ["postgres", "admin-sysinv", "admin-keystone", "admin-barbican", "admin-fm"]

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pg_keywords = PostgresqlKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify platform databases exist via psql -l")
    db_output = pg_keywords.list_databases()
    for db_name in expected_databases:
        validate_equals(
            db_output.is_database_present(db_name),
            True,
            f"Database '{db_name}' exists",
        )
    get_logger().log_info(f"All expected databases present: {expected_databases}")

    get_logger().log_test_case_step("Verify each platform database is queryable")
    for db_name in expected_databases:
        result = pg_keywords.query_database(db_name, "SELECT 1")
        validate_str_contains(result, "1", f"Database '{db_name}' responds to SELECT 1")
    get_logger().log_info(f"All databases queryable: {expected_databases}")

    get_logger().log_test_case_step("Verify expected PostgreSQL roles exist")
    roles_output = pg_keywords.list_roles()
    for role_name in expected_roles:
        validate_equals(
            roles_output.is_role_present(role_name),
            True,
            f"Role '{role_name}' exists",
        )
    get_logger().log_info(f"All expected roles present: {expected_roles}")


@mark.p2
def test_postgresql_platform_cli_crud(request: FixtureRequest):
    """Platform CLI exercises all DBs (CRUD) with database content verification.

    Validates that platform CLI commands can successfully perform operations
    against all core PostgreSQL databases (sysinv, fm, keystone, barbican)
    by executing read and write operations through their respective CLIs,
    and verifies that the actual database content is consistent with CLI
    operations (create reflects in DB, delete removes from DB).

    Preconditions:
        - System is installed and accessible
        - PostgreSQL is deployed as part of the platform

    Setup:
        - None

    Test Steps:
        1. Verify sysinv DB via system host-list and system host-show
        2. Verify fm DB via fm alarm-list and fm event-list
        3. Verify keystone DB via openstack user create and delete
        4. Verify user exists in keystone DB after creation
        5. Verify user is removed from keystone DB after deletion
        6. Verify barbican DB via openstack secret store and delete
        7. Verify secret exists in barbican DB after creation
        8. Verify secret is removed from barbican DB after deletion

    Teardown:
        - Delete test user if created
        - Delete test secret if created
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pg_keywords = PostgresqlKeywords(ssh_connection)
    test_user_name = "pgtest"
    test_user_password = "Test@12345678"
    test_secret_name = "pgtest"
    created_user = False
    secret_href = None

    def teardown_secret():
        get_logger().log_teardown_step("Delete test secret if created")
        if secret_href:
            OpenstackSecretKeywords(ssh_connection).delete_secret(secret_href)
            get_logger().log_info(f"Deleted secret: {secret_href}")

    def teardown_user():
        get_logger().log_teardown_step("Delete test user if created")
        if created_user:
            user_keywords = OpenstackUserListKeywords(ssh_connection)
            user_keywords.delete_user(test_user_name)
            get_logger().log_info(f"Deleted user: {test_user_name}")

    request.addfinalizer(teardown_secret)
    request.addfinalizer(teardown_user)

    # Clean up any stale test secrets from previous failed runs
    stale_check = pg_keywords.query_database("barbican", f"SELECT id FROM secrets WHERE name='{test_secret_name}' AND deleted=false")
    if "0 rows" not in stale_check:
        get_logger().log_info(f"Cleaning up stale '{test_secret_name}' secrets from previous runs")
        pg_keywords.query_database("barbican", f"UPDATE secrets SET deleted=true WHERE name='{test_secret_name}' AND deleted=false")

    get_logger().log_test_case_step("Verify sysinv DB via system host-list and system host-show")
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    host_output = host_list_keywords.get_system_host_list()
    hosts = host_output.get_hosts()
    validate_equals(len(hosts) > 0, True, "system host-list returns at least one host")
    controller_hostname = hosts[0].get_host_name()
    get_logger().log_info(f"Hosts found: {[h.get_host_name() for h in hosts]}")

    host_show_keywords = SystemHostShowKeywords(ssh_connection)
    host_show_output = host_show_keywords.get_system_host_show_output(controller_hostname)
    validate_str_contains(
        host_show_output.get_system_host_show_object().get_personality(),
        "controller",
        f"{controller_hostname} personality is controller",
    )
    get_logger().log_info(f"system host-show {controller_hostname}: personality=controller (sysinv DB OK)")

    get_logger().log_test_case_step("Verify fm DB via fm alarm-list and fm event-list")
    alarm_keywords = AlarmListKeywords(ssh_connection)
    alarm_keywords.get_alarm_list()
    get_logger().log_info("fm alarm-list executed successfully")

    event_keywords = FmEventListKeywords(ssh_connection)
    event_keywords.get_event_list(limit=5)
    get_logger().log_info("fm event-list executed successfully (fm DB OK)")

    get_logger().log_test_case_step("Verify keystone DB via openstack user create and delete")
    user_keywords = OpenstackUserListKeywords(ssh_connection)
    output = user_keywords.create_user(test_user_name, test_user_password)
    validate_str_contains(output, test_user_name, "User creation output contains username")
    created_user = True
    get_logger().log_info(f"Created user: {test_user_name}")

    get_logger().log_test_case_step("Verify user exists in keystone DB after creation")
    db_result = pg_keywords.query_database("keystone", f"SELECT id FROM local_user WHERE name='{test_user_name}'")
    validate_str_contains(db_result, "1 row", f"User '{test_user_name}' found in keystone DB after creation")
    get_logger().log_info(f"Confirmed '{test_user_name}' exists in keystone.local_user table")

    get_logger().log_test_case_step("Verify user is removed from keystone DB after deletion")
    user_keywords.delete_user(test_user_name)
    created_user = False
    get_logger().log_info(f"Deleted user: {test_user_name}")

    db_result = pg_keywords.query_database("keystone", f"SELECT id FROM local_user WHERE name='{test_user_name}'")
    validate_str_contains(db_result, "0 rows", f"User '{test_user_name}' absent from keystone DB after deletion")
    get_logger().log_info(f"Confirmed '{test_user_name}' removed from keystone.local_user table (keystone DB OK)")

    get_logger().log_test_case_step("Verify barbican DB via openstack secret store and delete")
    secret_keywords = OpenstackSecretKeywords(ssh_connection)
    secret_output = secret_keywords.store_secret(test_secret_name, "data")
    validate_str_contains(secret_output.get_raw_output(), "Secret href", "Secret store output contains Secret href")
    secret_href = secret_output.get_secret_href()

    get_logger().log_test_case_step("Verify secret exists in barbican DB after creation")
    db_result = pg_keywords.query_database("barbican", f"SELECT id FROM secrets WHERE name='{test_secret_name}' AND deleted=false")
    validate_str_contains(db_result, "1 row", f"Secret '{test_secret_name}' found in barbican DB after creation")
    get_logger().log_info(f"Confirmed '{test_secret_name}' exists in barbican.secrets table")

    get_logger().log_test_case_step("Verify secret is removed from barbican DB after deletion")
    secret_keywords.delete_secret(secret_href)
    secret_href = None
    get_logger().log_info(f"Deleted secret: {test_secret_name}")

    db_result = pg_keywords.query_database("barbican", f"SELECT id FROM secrets WHERE name='{test_secret_name}' AND deleted=false")
    validate_str_contains(db_result, "0 rows", f"Secret '{test_secret_name}' absent from barbican DB after deletion")
    get_logger().log_info(f"Confirmed '{test_secret_name}' removed from barbican.secrets table (barbican DB OK)")


@mark.p2
def test_postgresql_conf_and_pg_hba_validation():
    """postgresql.conf and pg_hba.conf validation.

    Validates PostgreSQL configuration settings and pg_hba.conf access rules
    to ensure encryption uses scram-sha-256, no removed/deprecated settings
    are present, and no puppet errors related to postgresql exist.

    Preconditions:
        - System is installed and accessible
        - PostgreSQL is deployed as part of the platform

    Setup:
        - None

    Test Steps:
        1. Verify password_encryption is scram-sha-256
        2. Verify max_connections and shared_buffers are set
        3. Verify pg_hba.conf uses scram-sha-256 and is puppet-managed
        4. Verify no removed/deprecated pg_settings variables exist
        5. Verify no postgresql errors in puppet log

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pg_keywords = PostgresqlKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify password_encryption is scram-sha-256")
    result = pg_keywords.query_database("postgres", "SHOW password_encryption")
    get_logger().log_info(f"Raw query_database return (repr): {repr(result)}")
    get_logger().log_info(f"Return length: {len(result)}")
    validate_str_contains(result, "scram-sha-256", "password_encryption is scram-sha-256")
    get_logger().log_info("password_encryption: scram-sha-256")

    get_logger().log_test_case_step("Verify max_connections and shared_buffers are set")
    max_conn_result = pg_keywords.query_database("postgres", "SHOW max_connections")
    validate_str_contains(max_conn_result, "1 row", "max_connections returns a value")
    get_logger().log_info(f"max_connections result: {max_conn_result.strip()}")

    shared_buf_result = pg_keywords.query_database("postgres", "SHOW shared_buffers")
    validate_str_contains(shared_buf_result, "1 row", "shared_buffers returns a value")
    get_logger().log_info(f"shared_buffers result: {shared_buf_result.strip()}")

    get_logger().log_test_case_step("Verify pg_hba.conf uses scram-sha-256 and is puppet-managed")
    hba_file_result = pg_keywords.query_database("postgres", "SHOW hba_file")
    validate_str_contains(hba_file_result, "pg_hba.conf", "hba_file points to pg_hba.conf")

    hba_content_result = pg_keywords.query_database("postgres", "SELECT pg_read_file(setting) FROM pg_settings WHERE name='hba_file'")
    validate_str_contains(hba_content_result, "scram-sha-256", "pg_hba.conf contains scram-sha-256 auth method")
    validate_str_contains(hba_content_result, "Puppet", "pg_hba.conf is managed by Puppet")
    get_logger().log_info("pg_hba.conf uses scram-sha-256 and is puppet-managed")

    get_logger().log_test_case_step("Verify no removed/deprecated pg_settings variables exist")
    deprecated_check = pg_keywords.query_database("postgres", "SELECT name FROM pg_settings WHERE name IN " "('old_snapshot_threshold','trace_recovery_messages','db_user_namespace')")
    validate_str_contains(deprecated_check, "0 rows", "No removed/deprecated settings found")
    get_logger().log_info("No deprecated pg_settings variables present")

    get_logger().log_test_case_step("Verify no postgresql errors in puppet log")
    # /var/log/puppet/latest/ is root-only; LogGrepKeywords handles sudo access.
    output_str = LogGrepKeywords(ssh_connection).grep_log_for_errors("/var/log/puppet/latest/puppet.log", "postgresql.*error")
    validate_equals(output_str, "", "No postgresql errors in puppet log")
    get_logger().log_info("No postgresql errors found in puppet log")


@mark.p2
@mark.lab_has_standby_controller
def test_postgresql_db_replication_between_controllers(request: FixtureRequest):
    """TC5: Verify DB replication between controllers (AIO-DX).

    Validates that PostgreSQL data written on the active controller is
    replicated and available on the standby after a swact, using DRBD
    synchronous replication.

    Preconditions:
        - AIO-DX system with both controllers unlocked/enabled/available

    Setup:
        - None

    Test Steps:
        1. Verify both controllers are unlocked/enabled/available
        2. Verify DRBD shows Connected and UpToDate/UpToDate
        3. Verify /var/lib/postgresql is mounted via drbd
        4. Verify postgres service is enabled-active via sm-dump
        5. Create a test user via openstack user create
        6. Perform host-swact to switch active controller
        7. Verify DRBD still shows Connected and UpToDate on new active
        8. Verify postgres service is enabled-active on new active
        9. Verify test user persists after swact via openstack user show

    Teardown:
        - Delete test user if created
        - Swact back to original controller
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    test_user_name = "repltest"
    test_user_password = "Test@12345678"
    created_user = False

    def teardown():
        get_logger().log_teardown_step("Delete test user if created")
        if created_user:
            ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
            user_keywords = OpenstackUserListKeywords(ssh_conn)
            user_keywords.delete_user(test_user_name)
            get_logger().log_info(f"Deleted user: {test_user_name}")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Verify both controllers are unlocked/enabled/available")
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    host_output = host_list_keywords.get_system_host_list()
    hosts = host_output.get_hosts()
    controllers = [h for h in hosts if "controller" in h.get_personality()]
    validate_equals(len(controllers), 2, "Two controllers present")
    for ctrl in controllers:
        validate_equals(ctrl.get_administrative(), "unlocked", f"{ctrl.get_host_name()} is unlocked")
        validate_equals(ctrl.get_operational(), "enabled", f"{ctrl.get_host_name()} is enabled")
        validate_equals(ctrl.get_availability(), "available", f"{ctrl.get_host_name()} is available")
    get_logger().log_info("Both controllers are unlocked/enabled/available")

    get_logger().log_test_case_step("Verify DRBD shows Connected and UpToDate/UpToDate")
    drbd_str = DrbdKeywords(ssh_connection).get_drbd_status()
    validate_str_contains(drbd_str, "cs:Connected", "DRBD shows Connected")
    validate_str_contains(drbd_str, "UpToDate/UpToDate", "DRBD shows UpToDate/UpToDate")
    get_logger().log_info("DRBD: Connected, UpToDate/UpToDate")

    get_logger().log_test_case_step("Verify /var/lib/postgresql is mounted via drbd")
    mount_str = MountKeywords(ssh_connection).get_mounts("postgresql")
    validate_str_contains(mount_str, "/var/lib/postgresql", "postgresql mount is present")
    validate_str_contains(mount_str, "drbd", "postgresql is mounted via drbd")
    get_logger().log_info(f"postgresql mount: {mount_str.strip()}")

    get_logger().log_test_case_step("Verify postgres service is enabled-active via sm-dump")
    sm_keywords = SMKeywords(ssh_connection)
    validate_equals(sm_keywords.is_service_enabled("postgres"), True, "postgres service is enabled-active")
    get_logger().log_info("postgres: enabled-active on active controller")

    get_logger().log_test_case_step("Create a test user via openstack user create")
    user_keywords = OpenstackUserListKeywords(ssh_connection)
    output = user_keywords.create_user(test_user_name, test_user_password)
    validate_str_contains(output, test_user_name, "User creation output contains username")
    created_user = True
    get_logger().log_info(f"Created user: {test_user_name}")

    get_logger().log_test_case_step("Perform host-swact to switch active controller")
    SystemHostSwactKeywords(ssh_connection).host_swact()
    get_logger().log_info("Swact completed successfully")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify DRBD still shows Connected and UpToDate on new active")
    drbd_str = DrbdKeywords(ssh_connection).get_drbd_status()
    validate_str_contains(drbd_str, "cs:Connected", "DRBD shows Connected on new active")
    validate_str_contains(drbd_str, "UpToDate/UpToDate", "DRBD shows UpToDate/UpToDate on new active")
    get_logger().log_info("DRBD on new active: Connected, UpToDate/UpToDate")

    get_logger().log_test_case_step("Verify postgres service is enabled-active on new active")
    sm_keywords = SMKeywords(ssh_connection)
    validate_equals(sm_keywords.is_service_enabled("postgres"), True, "postgres service is enabled-active on new active")
    get_logger().log_info("postgres: enabled-active on new active controller")

    get_logger().log_test_case_step("Verify test user persists after swact via openstack user show")
    user_keywords = OpenstackUserListKeywords(ssh_connection)
    output = user_keywords.show_user(test_user_name)
    validate_str_contains(output, test_user_name, "User data persists after swact")
    get_logger().log_info(f"User '{test_user_name}' confirmed present on new active controller - DB replication verified")


@mark.p2
@mark.lab_has_standby_controller
def test_postgresql_controller_lock_unlock(request: FixtureRequest):
    """TC7: Controller lock/unlock - verify DB persists through lock/unlock cycle.

    Validates that PostgreSQL on the active controller continues serving
    while the standby is locked, data created during degraded state persists
    after unlock, and DRBD re-syncs to Connected/UpToDate.



    Preconditions:
        - AIO-DX system with both controllers unlocked/enabled/available

    Setup:
        - None

    Test Steps:
        1. Verify both controllers unlocked/enabled/available and no alarms
        2. Verify DRBD shows Connected and UpToDate/UpToDate
        3. Lock standby controller and verify active continues serving
        4. Create test data while standby is locked
        5. Unlock standby controller and wait for available
        6. Verify DRBD re-establishes Connected/UpToDate after unlock
        7. Verify test data persists after standby rejoins

    Teardown:
        - Delete test user if created
        - Unlock standby if still locked
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    test_user_name = "reduntest1"
    test_user_password = "Test@12345678"
    created_user = False
    standby_locked = False
    standby_hostname = None

    def teardown_unlock_standby():
        get_logger().log_teardown_step("Unlock standby if still locked")
        if standby_locked and standby_hostname:
            ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
            SystemHostLockKeywords(ssh_conn).unlock_host(standby_hostname)
            get_logger().log_info(f"Unlocked: {standby_hostname}")

    def teardown_user():
        get_logger().log_teardown_step("Delete test user if created")
        if created_user:
            ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
            OpenstackUserListKeywords(ssh_conn).delete_user(test_user_name)
            get_logger().log_info(f"Deleted user: {test_user_name}")

    request.addfinalizer(teardown_unlock_standby)
    request.addfinalizer(teardown_user)

    get_logger().log_test_case_step("Verify both controllers unlocked/enabled/available and no alarms")
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    host_output = host_list_keywords.get_system_host_list()
    hosts = host_output.get_hosts()
    controllers = [h for h in hosts if "controller" in h.get_personality()]
    validate_equals(len(controllers), 2, "Two controllers present")
    for ctrl in controllers:
        validate_equals(ctrl.get_administrative(), "unlocked", f"{ctrl.get_host_name()} is unlocked")
        validate_equals(ctrl.get_operational(), "enabled", f"{ctrl.get_host_name()} is enabled")
        validate_equals(ctrl.get_availability(), "available", f"{ctrl.get_host_name()} is available")

    alarm_keywords = AlarmListKeywords(ssh_connection)
    alarm_output = alarm_keywords.get_alarm_list()
    alarms = alarm_output.get_alarms()
    validate_equals(len(alarms), 0, "No active alarms before test")
    get_logger().log_info("Both controllers available, no alarms")

    get_logger().log_test_case_step("Verify DRBD shows Connected and UpToDate/UpToDate")
    drbd_str = DrbdKeywords(ssh_connection).get_drbd_status()
    validate_str_contains(drbd_str, "cs:Connected", "DRBD shows Connected")
    validate_str_contains(drbd_str, "UpToDate/UpToDate", "DRBD shows UpToDate/UpToDate")
    get_logger().log_info("DRBD: Connected, UpToDate/UpToDate")

    get_logger().log_test_case_step("Lock standby controller and verify active continues serving")
    standby = host_list_keywords.get_standby_controller()
    standby_hostname = standby.get_host_name()
    lock_keywords = SystemHostLockKeywords(ssh_connection)
    lock_keywords.lock_host(standby_hostname)
    standby_locked = True
    get_logger().log_info(f"Locked standby: {standby_hostname}")

    # Verify active still serves CLI requests
    host_output = host_list_keywords.get_system_host_list()
    validate_equals(len(host_output.get_hosts()) > 0, True, "system host-list works with standby locked")
    get_logger().log_info("Active controller continues serving requests")

    get_logger().log_test_case_step("Create test data while standby is locked")
    user_keywords = OpenstackUserListKeywords(ssh_connection)
    output = user_keywords.create_user(test_user_name, test_user_password)
    validate_str_contains(output, test_user_name, "User created while standby locked")
    created_user = True
    get_logger().log_info(f"Created user '{test_user_name}' while standby locked")

    get_logger().log_test_case_step("Unlock standby controller and wait for available")
    lock_keywords.unlock_host(standby_hostname)
    standby_locked = False
    get_logger().log_info(f"Unlocked standby: {standby_hostname}")

    get_logger().log_test_case_step("Verify DRBD re-establishes Connected/UpToDate after unlock")
    drbd_str = DrbdKeywords(ssh_connection).get_drbd_status()
    validate_str_contains(drbd_str, "cs:Connected", "DRBD re-established Connected after unlock")
    validate_str_contains(drbd_str, "UpToDate/UpToDate", "DRBD re-established UpToDate/UpToDate after unlock")
    get_logger().log_info("DRBD re-synced: Connected, UpToDate/UpToDate")

    get_logger().log_test_case_step("Verify test data persists after standby rejoins")
    output = user_keywords.show_user(test_user_name)
    validate_str_contains(output, test_user_name, "User data persists after standby unlock")
    get_logger().log_info(f"User '{test_user_name}' confirmed present - data persists through lock/unlock cycle")


@mark.p2
@mark.lab_has_subcloud
def test_postgresql_dc_system_controller(request: FixtureRequest):
    """TC9: DC basic - PG17 on system controller.

    Validates that PostgreSQL 17 is running on the DC system controller,
    dcmanager/dcorch databases exist, subcloud operations work correctly,
    dcorch sync functions properly, and no DB errors in logs.

    Preconditions:
        - DC system controller bootstrapped on Trixie
        - At least one subcloud managed/online/in-sync

    Setup:
        - None

    Test Steps:
        1. Verify PostgreSQL 17 is installed via psql --version
        2. Verify dcmanager and dcorch databases exist
        3. Verify subclouds are managed/online/in-sync via dcmanager subcloud list
        4. Verify dcmanager subcloud show and update operations succeed
        5. Verify dcorch sync status and manage/unmanage subcloud
        6. Check dcmanager/dcorch logs for DB errors

    Teardown:
        - Re-manage subcloud if left unmanaged
        - Revert subcloud description if changed
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pg_keywords = PostgresqlKeywords(ssh_connection)
    subcloud_unmanaged = False
    target_subcloud = None

    def teardown():
        get_logger().log_teardown_step("Re-manage subcloud if left unmanaged")
        if subcloud_unmanaged and target_subcloud:
            ssh_conn = LabConnectionKeywords().get_active_controller_ssh()
            DcManagerSubcloudManagerKeywords(ssh_conn).get_dcmanager_subcloud_manage(target_subcloud, timeout=300)
            get_logger().log_info(f"Re-managed subcloud: {target_subcloud}")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Verify PostgreSQL 17 is installed via psql --version")
    psql_version = pg_keywords.get_psql_version()
    validate_str_contains(psql_version, "PostgreSQL", "psql is installed")
    validate_str_contains(psql_version, "17.", "PostgreSQL version is 17.x")
    get_logger().log_info(f"psql version: {psql_version}")

    get_logger().log_test_case_step("Verify dcmanager and dcorch databases exist")
    db_output = pg_keywords.list_databases()
    validate_equals(db_output.is_database_present("dcmanager"), True, "dcmanager database exists")
    validate_equals(db_output.is_database_present("dcorch"), True, "dcorch database exists")
    get_logger().log_info("Both dcmanager and dcorch databases present")

    get_logger().log_test_case_step("Verify subclouds are managed/online/in-sync via dcmanager subcloud list")
    dc_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    subcloud_list = dc_list_keywords.get_dcmanager_subcloud_list()
    subclouds = subcloud_list.get_dcmanager_subcloud_list_objects()
    validate_equals(len(subclouds) > 0, True, "At least one subcloud exists")
    target_subcloud = subclouds[0].get_name()

    for sc in subclouds:
        validate_equals(sc.get_management(), "managed", f"{sc.get_name()} is managed")
        validate_equals(sc.get_availability(), "online", f"{sc.get_name()} is online")
        validate_equals(sc.get_sync(), "in-sync", f"{sc.get_name()} is in-sync")
    get_logger().log_info(f"All {len(subclouds)} subclouds are managed/online/in-sync")

    get_logger().log_test_case_step("Verify dcmanager subcloud show and update operations succeed")
    dc_show_keywords = DcManagerSubcloudShowKeywords(ssh_connection)
    show_output = dc_show_keywords.get_dcmanager_subcloud_show(target_subcloud)
    validate_equals(show_output.get_dcmanager_subcloud_show_object().get_name(), target_subcloud, "subcloud show returns correct name")
    get_logger().log_info(f"dcmanager subcloud show {target_subcloud}: OK")

    dc_update_keywords = DcManagerSubcloudUpdateKeywords(ssh_connection)
    dc_update_keywords.dcmanager_subcloud_update(target_subcloud, "description", "pg17-test-update")
    get_logger().log_info(f"dcmanager subcloud update {target_subcloud} --description: OK")

    # Revert description
    dc_update_keywords.dcmanager_subcloud_update(target_subcloud, "description", " ")
    get_logger().log_info("Reverted subcloud description")

    get_logger().log_test_case_step("Verify dcorch sync status and manage/unmanage subcloud")
    # Check dcorch sync status via DB
    sync_result = pg_keywords.query_database("dcorch", "SELECT sync_status_reported FROM subcloud_sync LIMIT 5")
    validate_str_contains(sync_result, "in-sync", "dcorch subcloud_sync shows in-sync entries")
    get_logger().log_info("dcorch sync status confirmed in-sync")

    # Unmanage subcloud
    dc_mgr_keywords = DcManagerSubcloudManagerKeywords(ssh_connection)
    dc_mgr_keywords.get_dcmanager_subcloud_unmanage(target_subcloud, timeout=120)
    subcloud_unmanaged = True
    get_logger().log_info(f"Unmanaged subcloud: {target_subcloud}")

    # Re-manage subcloud
    dc_mgr_keywords.get_dcmanager_subcloud_manage(target_subcloud, timeout=300)
    subcloud_unmanaged = False
    get_logger().log_info(f"Re-managed subcloud: {target_subcloud}")

    # Verify sync re-establishes
    dc_list_keywords.validate_subcloud_sync_status(target_subcloud, "in-sync")
    get_logger().log_info(f"Subcloud {target_subcloud} back to in-sync after manage/unmanage cycle")

    get_logger().log_test_case_step("Check dcmanager/dcorch logs for DB errors")
    # /var/log/dcmanager and /var/log/dcorch are root-only; LogGrepKeywords handles sudo access.
    output_str = LogGrepKeywords(ssh_connection).grep_log_for_errors("/var/log/dcmanager/dcmanager.log", "error", secondary_pattern="database\\|postgres\\|psql\\|sqlalchemy")
    get_logger().log_info(f"Subcloud log {output_str}")
    validate_equals(output_str, "", "No DB errors in dcmanager log")
    get_logger().log_info("No DB errors in dcmanager log")

    output_str = LogGrepKeywords(ssh_connection).grep_log_for_errors("/var/log/dcorch/dcorch.log", "error", secondary_pattern="database\\|postgres\\|psql\\|sqlalchemy")
    validate_equals(output_str, "", "No DB errors in dcorch log")
    get_logger().log_info("No DB errors in dcorch log")
