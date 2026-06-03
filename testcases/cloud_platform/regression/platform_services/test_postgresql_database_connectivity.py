from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.postgresql.postgresql_keywords import PostgresqlKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from pytest import mark

EXPECTED_DATABASES = ["sysinv", "keystone", "barbican", "fm"]
EXPECTED_ROLES = ["postgres", "admin-sysinv", "admin-keystone", "admin-barbican", "admin-fm"]


@mark.p0
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
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pg_keywords = PostgresqlKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify platform databases exist via psql -l")
    db_output = pg_keywords.list_databases()
    for db_name in EXPECTED_DATABASES:
        validate_equals(
            db_output.is_database_present(db_name),
            True,
            f"Database '{db_name}' exists",
        )
    get_logger().log_info(f"All expected databases present: {EXPECTED_DATABASES}")

    get_logger().log_test_case_step("Verify each platform database is queryable")
    for db_name in EXPECTED_DATABASES:
        result = pg_keywords.query_database(db_name, "SELECT 1")
        validate_str_contains(result, "1", f"Database '{db_name}' responds to SELECT 1")
    get_logger().log_info(f"All databases queryable: {EXPECTED_DATABASES}")

    get_logger().log_test_case_step("Verify expected PostgreSQL roles exist")
    roles_output = pg_keywords.list_roles()
    for role_name in EXPECTED_ROLES:
        validate_equals(
            roles_output.is_role_present(role_name),
            True,
            f"Role '{role_name}' exists",
        )
    get_logger().log_info(f"All expected roles present: {EXPECTED_ROLES}")
