"""O-RAN O2 IMS API — enforcement negatives (401 / 405 / 404).

Verifies the O2 IMS API enforces authentication and method/resource rules: an
unauthenticated read and a malformed-token read are rejected with 401, a POST to
a read-only collection is rejected with 405, and a DELETE of a nonexistent
subscription returns 404. Six further method-and-path combinations spanning both
the inventory and monitoring namespaces are each rejected with 405, and a PATCH of
a nonexistent alarm returns 404. Creates and destroys nothing.

Prerequisites:
    - Target system accessible (--lab_config_file)
    - O2 IMS config (--o2ims_config_file), or its defaults
    - The O2 bring-up has been run against the target and left standing: the
      oran-o2 application applied, the OAuth2 token issuer running, and the
      client certificate material present on the test runner. This suite
      consumes that environment and never recreates it. The bring-up lives in
      testcases/cloud_platform/apps_setup/o_ran_o2/, so a plan that runs
      apps_setup before regression establishes it in the right order.

Run with:
    pytest starlingx/testcases/cloud_platform/regression/applications/o_ran_o2/test_o2_api_enforcement.py \
        --lab_config_file=<LAB_CONFIG> \
        --o2ims_config_file=<O2IMS_CONFIG> -v

Outputs:
    None. The tests only probe enforcement; nothing is created or destroyed.

Retention:
    This suite must not release or reclaim the target on success and must not
    redeploy, restart the issuer, or modify the certificate material. It depends
    on the standing environment produced by the bring-up.

Markers:
    - @mark.p2: priority tier
"""

import uuid

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.rest.oran_o2.o2_environment_keywords import O2EnvironmentKeywords
from keywords.cloud_platform.rest.oran_o2.o2_negative_keywords import NONEXISTENT_SUBSCRIPTION_ID, O2NegativeKeywords
from keywords.cloud_platform.rest.oran_o2.o2_rest_client import O2RestClient
from keywords.cloud_platform.rest.oran_o2.o2_token_keywords import O2TokenKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


def _build_negative_keywords() -> O2NegativeKeywords:
    """Establish the environment and build the O2 negative-path keywords.

    Returns:
        O2NegativeKeywords: Negative-path keywords backed by an O2 client.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    cert_dir = ConfigurationManager.get_o2ims_config().get_cert_dir()
    O2EnvironmentKeywords(ssh_connection).verify_environment_ready(cert_dir)
    token = O2TokenKeywords(ssh_connection).get_token()
    return O2NegativeKeywords(O2RestClient(cert_dir, ssh_connection, token=token))


@mark.p2
def test_o2_api_no_auth_rejected(request: FixtureRequest):
    """Reject an unauthenticated O-Cloud root read with exactly 401.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.

    Test Steps:
        1. GET the O-Cloud root with the client cert but no Authorization header,
           and verify the status is exactly 401.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 negative keywords")
    negative_keywords = _build_negative_keywords()

    get_logger().log_test_case_step("GET the O-Cloud root with no Authorization header and verify exactly 401")
    response = negative_keywords.get_ocloud_root_no_auth()
    validate_equals(response.get_status_code(), 401, "Unauthenticated O-Cloud root read is rejected with 401")


@mark.p2
def test_o2_api_malformed_token_rejected(request: FixtureRequest):
    """Reject a malformed-token O-Cloud root read with exactly 401.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.

    Test Steps:
        1. GET the O-Cloud root (a param-free endpoint) with a malformed Bearer
           token, and verify the status is exactly 401.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 negative keywords")
    negative_keywords = _build_negative_keywords()

    get_logger().log_test_case_step("GET the O-Cloud root with a malformed Bearer token and verify exactly 401")
    response = negative_keywords.get_ocloud_root_invalid_token("this-is-not-a-valid-token")
    validate_equals(response.get_status_code(), 401, "Malformed-token O-Cloud root read is rejected with 401")


@mark.p2
def test_o2_api_post_read_only_collection_rejected(request: FixtureRequest):
    """Reject a POST to the read-only resourcePools collection with exactly 405.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.

    Test Steps:
        1. POST to the resourcePools collection and verify the status is exactly 405.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 negative keywords")
    negative_keywords = _build_negative_keywords()

    get_logger().log_test_case_step("POST to the read-only resourcePools collection and verify exactly 405")
    response = negative_keywords.post_resource_pools()
    validate_equals(response.get_status_code(), 405, "POST to read-only resourcePools is rejected with 405")


@mark.p2
def test_o2_api_delete_nonexistent_subscription(request: FixtureRequest):
    """Return 404 for a DELETE of a nonexistent subscription, creating nothing.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.

    Test Steps:
        1. DELETE a syntactically valid but nonexistent subscription id and verify
           the status is exactly 404.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 negative keywords")
    negative_keywords = _build_negative_keywords()

    get_logger().log_test_case_step("DELETE a nonexistent subscription and verify exactly 404")
    response = negative_keywords.delete_subscription(NONEXISTENT_SUBSCRIPTION_ID)
    validate_equals(response.get_status_code(), 404, "DELETE of a nonexistent subscription returns 404")


@mark.p2
def test_o2_api_unsupported_methods_rejected(request: FixtureRequest):
    """Reject six unsupported method-and-path combinations with exactly 405.

    Covers both API namespaces and both write verbs the API refuses: POST to three
    read-only inventory paths, PATCH to the inventory subscriptions collection, POST
    to the monitoring alarms collection, and PATCH to the monitoring
    alarmSubscriptions collection. Every path is registered, so each rejection is a
    method rejection rather than a missing route, and each is produced while the
    request is being routed rather than by application code. No step depends on
    another, and nothing is created or destroyed.

    The resource pool id is generated rather than fetched because it is never
    dereferenced: the rejection precedes any pool lookup, so a generated id removes a
    dependency on lab inventory state without weakening the assertion.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.
        - Generate a resource pool id for the nested-resources path.

    Test Steps:
        1. POST to the nested resources sub-collection and verify exactly 405.
        2. POST to the deploymentManagers collection and verify exactly 405.
        3. POST to the inventory version root and verify exactly 405.
        4. PATCH the inventory subscriptions collection and verify exactly 405.
        5. POST to the monitoring alarms collection and verify exactly 405.
        6. PATCH the monitoring alarmSubscriptions collection and verify exactly 405.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 negative keywords")
    negative_keywords = _build_negative_keywords()
    resource_pool_id = str(uuid.uuid4())

    get_logger().log_test_case_step("POST to the nested resources sub-collection and verify exactly 405")
    response = negative_keywords.post_nested_resources(resource_pool_id)
    validate_equals(response.get_status_code(), 405, "POST to the nested resources sub-collection is rejected with 405")
    validate_str_contains(response.get_body(), "405 Method Not Allowed", "Rejection detail carries the framework-rendered 405 form")

    get_logger().log_test_case_step("POST to the deploymentManagers collection and verify exactly 405")
    response = negative_keywords.post_deployment_managers()
    validate_equals(response.get_status_code(), 405, "POST to the deploymentManagers collection is rejected with 405")
    validate_str_contains(response.get_body(), "405 Method Not Allowed", "Rejection detail carries the framework-rendered 405 form")

    get_logger().log_test_case_step("POST to the inventory version root and verify exactly 405")
    response = negative_keywords.post_version_root()
    validate_equals(response.get_status_code(), 405, "POST to the inventory version root is rejected with 405")
    validate_str_contains(response.get_body(), "405 Method Not Allowed", "Rejection detail carries the framework-rendered 405 form")

    get_logger().log_test_case_step("PATCH the inventory subscriptions collection and verify exactly 405")
    response = negative_keywords.patch_subscriptions()
    validate_equals(response.get_status_code(), 405, "PATCH of the inventory subscriptions collection is rejected with 405")
    validate_str_contains(response.get_body(), "405 Method Not Allowed", "Rejection detail carries the framework-rendered 405 form")

    get_logger().log_test_case_step("POST to the monitoring alarms collection and verify exactly 405")
    response = negative_keywords.post_alarms()
    validate_equals(response.get_status_code(), 405, "POST to the monitoring alarms collection is rejected with 405")
    validate_str_contains(response.get_body(), "405 Method Not Allowed", "Rejection detail carries the framework-rendered 405 form")

    get_logger().log_test_case_step("PATCH the monitoring alarmSubscriptions collection and verify exactly 405")
    response = negative_keywords.patch_alarm_subscriptions()
    validate_equals(response.get_status_code(), 405, "PATCH of the monitoring alarmSubscriptions collection is rejected with 405")
    validate_str_contains(response.get_body(), "405 Method Not Allowed", "Rejection detail carries the framework-rendered 405 form")


@mark.p2
def test_o2_api_patch_nonexistent_alarm_rejected(request: FixtureRequest):
    """Return 404 for a PATCH of a nonexistent alarm, creating nothing.

    Sends exactly one of the two mutually exclusive modification fields, as a quoted
    JSON string, so the request reaches the not-found path rather than being turned
    away by body validation first. The alarm id is generated, so no alarm needs to
    exist and none is created.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.
        - Generate an alarm id that cannot exist.

    Test Steps:
        1. PATCH a nonexistent alarm and verify the status is exactly 404.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 negative keywords")
    negative_keywords = _build_negative_keywords()
    alarm_id = str(uuid.uuid4())

    get_logger().log_test_case_step("PATCH a nonexistent alarm and verify exactly 404")
    response = negative_keywords.patch_alarm(alarm_id)
    validate_equals(response.get_status_code(), 404, "PATCH of a nonexistent alarm returns 404")
    validate_str_contains(response.get_body(), "doesn't exist", "Rejection detail names the absent alarm record")
