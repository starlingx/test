"""REST API GET on Fault Management (FM) endpoints."""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.rest.fm.get_fm_keywords import GetFmKeywords


@mark.p1
def test_get_fm_alarms() -> None:
    """Test GET /alarms returns 200 with valid authentication.

    Test Steps:
        - GET the FM /alarms endpoint with valid authentication
        - Validate the response contains a valid alarm list
    """
    get_logger().log_test_case_step("GET FM /alarms endpoint")
    alarm_output = GetFmKeywords().get_alarms()
    get_logger().log_test_case_step("Validate alarm output is not None")
    validate_equals(alarm_output is not None, True, "FM /alarms returns a valid output")
    validate_equals(alarm_output.get_alarm_objects() is not None, True, "FM /alarms alarm objects list is not None")


@mark.p1
def test_get_fm_v1() -> None:
    """Test GET /v1 returns 200 with valid authentication.

    Test Steps:
        - GET the FM /v1 endpoint with valid authentication
        - Validate the response contains API links
    """
    get_logger().log_test_case_step("GET FM /v1 endpoint")
    v1_output = GetFmKeywords().get_v1()
    get_logger().log_test_case_step("Validate v1 output contains links")
    validate_equals(v1_output is not None, True, "FM /v1 returns a valid output")
    validate_equals(v1_output.get_links() is not None, True, "FM /v1 links is not None")


@mark.p1
def test_get_fm_event_log() -> None:
    """Test GET /event_log returns 200 with valid authentication.

    Test Steps:
        - GET the FM /event_log endpoint with valid authentication
        - Validate the response contains a valid event log list
    """
    get_logger().log_test_case_step("GET FM /event_log endpoint")
    event_log_output = GetFmKeywords().get_event_log()
    get_logger().log_test_case_step("Validate event log output is not None")
    validate_equals(event_log_output is not None, True, "FM /event_log returns a valid output")
    validate_equals(event_log_output.get_event_log_objects() is not None, True, "FM /event_log objects list is not None")


@mark.p1
def test_get_fm_event_suppression() -> None:
    """Test GET /event_suppression returns 200 with valid authentication.

    Test Steps:
        - GET the FM /event_suppression endpoint with valid authentication
        - Validate the response contains a valid event suppression list
    """
    get_logger().log_test_case_step("GET FM /event_suppression endpoint")
    suppression_output = GetFmKeywords().get_event_suppression()
    get_logger().log_test_case_step("Validate event suppression output is not None")
    validate_equals(suppression_output is not None, True, "FM /event_suppression returns a valid output")
    validate_equals(suppression_output.get_event_suppression_objects() is not None, True, "FM /event_suppression objects list is not None")
