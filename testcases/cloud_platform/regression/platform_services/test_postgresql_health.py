from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.postgresql.postgresql_keywords import PostgresqlKeywords
from keywords.cloud_platform.sm.sm_keywords import SMKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.health_query.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.system_test.patching_keywords import PatchingKeywords
from pytest import mark


@mark.p0
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
        1. Verify build version from /etc/build.info
        2. Verify psql client is installed
        3. Verify PostgreSQL is accepting connections via pg_isready
        4. Verify postgres service is enabled-active via SM
        5. Verify system health-query reports healthy state

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify build version from /etc/build.info")
    patching_keywords = PatchingKeywords(ssh_connection)
    build_info = patching_keywords.get_and_validate_build_info()
    get_logger().log_info(f"SW_VERSION: {build_info['SW_VERSION']}, BUILD_ID: {build_info['BUILD_ID']}")

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
    get_logger().log_info(f"pg_isready: {pg_isready_output.get_pg_is_ready_object()}")

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
