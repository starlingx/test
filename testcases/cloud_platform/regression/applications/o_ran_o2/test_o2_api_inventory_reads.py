"""O-RAN O2 IMS API — inventory reads (types, pools, resources, deployment managers).

Reads the O2 IMS inventory list and detail endpoints and verifies each returns
200 with populated, well-formed data. Detail ids are taken from the unfiltered
list. Reads only; changes nothing.

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
    pytest starlingx/testcases/cloud_platform/regression/applications/o_ran_o2/test_o2_api_inventory_reads.py \
        --lab_config_file=<LAB_CONFIG> \
        --o2ims_config_file=<O2IMS_CONFIG> -v

Outputs:
    None. The tests only read the O2 IMS inventory.

Retention:
    This suite must not release or reclaim the target on success and must not
    redeploy, restart the issuer, or modify the certificate material. It depends
    on the standing environment produced by the bring-up.

Markers:
    - @mark.p2: priority tier
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.rest.oran_o2.o2_environment_keywords import O2EnvironmentKeywords
from keywords.cloud_platform.rest.oran_o2.o2_inventory_keywords import O2InventoryKeywords
from keywords.cloud_platform.rest.oran_o2.o2_rest_client import O2RestClient
from keywords.cloud_platform.rest.oran_o2.o2_token_keywords import O2TokenKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


def _build_inventory_keywords() -> O2InventoryKeywords:
    """Establish the environment and build the O2 inventory keywords.

    Returns:
        O2InventoryKeywords: Inventory keywords backed by an authenticated O2 client.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    cert_dir = ConfigurationManager.get_o2ims_config().get_cert_dir()
    O2EnvironmentKeywords(ssh_connection).verify_environment_ready(cert_dir)
    token = O2TokenKeywords(ssh_connection).get_token()
    return O2InventoryKeywords(O2RestClient(cert_dir, ssh_connection, token=token))


@mark.p2
def test_o2_api_resource_types(request: FixtureRequest):
    """Read the O2 IMS resource types list and a detail.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.

    Test Steps:
        1. GET resourceTypes and verify a non-empty list, each entry carrying a
           resourceTypeId.
        2. GET a resourceType detail by an id from the unfiltered list and verify
           it returns that resourceTypeId.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 inventory keywords")
    inventory_keywords = _build_inventory_keywords()

    get_logger().log_test_case_step("GET resourceTypes and verify a non-empty list carrying ids")
    output = inventory_keywords.get_resource_types()
    validate_not_equals(output.is_empty(), True, "resourceTypes list is not empty")
    for resource_type in output.get_resource_types():
        validate_not_equals(resource_type.get_resource_type_id(), "", "resourceType entry has a resourceTypeId")

    get_logger().log_test_case_step("GET a resourceType detail by an id from the unfiltered list")
    detail_id = output.get_first().get_resource_type_id()
    get_logger().log_info(f"resourceType detail id: {detail_id}")
    detail_output = inventory_keywords.get_resource_type(detail_id)
    validate_equals(detail_output.get_first().get_resource_type_id(), detail_id, "resourceType detail returns the requested resourceTypeId")


@mark.p2
def test_o2_api_resource_pools(request: FixtureRequest):
    """Read the O2 IMS resource pools list and a detail.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.

    Test Steps:
        1. GET resourcePools and verify a non-empty list, each entry carrying a
           resourcePoolId.
        2. GET a resourcePool detail by an id from the list and verify it returns
           that resourcePoolId.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 inventory keywords")
    inventory_keywords = _build_inventory_keywords()

    get_logger().log_test_case_step("GET resourcePools and verify a non-empty list carrying ids")
    output = inventory_keywords.get_resource_pools()
    validate_not_equals(output.is_empty(), True, "resourcePools list is not empty")
    for resource_pool in output.get_resource_pools():
        validate_not_equals(resource_pool.get_resource_pool_id(), "", "resourcePool entry has a resourcePoolId")

    get_logger().log_test_case_step("GET a resourcePool detail by an id from the list")
    detail_id = output.get_first().get_resource_pool_id()
    get_logger().log_info(f"resourcePool detail id: {detail_id}")
    detail_output = inventory_keywords.get_resource_pool(detail_id)
    validate_equals(detail_output.get_first().get_resource_pool_id(), detail_id, "resourcePool detail returns the requested resourcePoolId")


@mark.p2
def test_o2_api_resources(request: FixtureRequest):
    """Read the O2 IMS resources list and a detail within a resource pool.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.

    Test Steps:
        1. GET resourcePools and verify the list is non-empty before selecting a pool.
        2. GET the resources of that pool; each entry carries a resourceId.
        3. GET a resource detail by an id from the list and verify it returns that
           resourceId.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 inventory keywords")
    inventory_keywords = _build_inventory_keywords()

    get_logger().log_test_case_step("GET resourcePools and verify the list is non-empty before selecting a pool")
    pools_output = inventory_keywords.get_resource_pools()
    validate_not_equals(pools_output.is_empty(), True, "resourcePools list is not empty")
    pool_id = pools_output.get_first().get_resource_pool_id()

    get_logger().log_test_case_step("GET the resources of the pool and verify a resourceId on each entry")
    resources_output = inventory_keywords.get_resources(pool_id)
    validate_not_equals(resources_output.is_empty(), True, "resources list is not empty")
    for resource in resources_output.get_resources():
        validate_not_equals(resource.get_resource_id(), "", "resource entry has a resourceId")

    get_logger().log_test_case_step("GET a resource detail by an id from the list")
    detail_id = resources_output.get_first().get_resource_id()
    get_logger().log_info(f"resource detail id: {detail_id} in pool {pool_id}")
    detail_output = inventory_keywords.get_resource(pool_id, detail_id)
    validate_equals(detail_output.get_first().get_resource_id(), detail_id, "resource detail returns the requested resourceId")


@mark.p2
def test_o2_api_deployment_managers(request: FixtureRequest):
    """Read the O2 IMS deployment managers list and a detail.

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH, verify the O2 environment is ready, acquire a Bearer token.

    Test Steps:
        1. GET deploymentManagers and verify a non-empty list, each entry carrying
           a deploymentManagerId.
        2. GET a deploymentManager detail by an id from the unfiltered list and
           verify it returns that deploymentManagerId.

    Teardown:
        - None.
    """
    get_logger().log_setup_step("Establish environment and build O2 inventory keywords")
    inventory_keywords = _build_inventory_keywords()

    get_logger().log_test_case_step("GET deploymentManagers and verify a non-empty list carrying ids")
    output = inventory_keywords.get_deployment_managers()
    validate_not_equals(output.is_empty(), True, "deploymentManagers list is not empty")
    for deployment_manager in output.get_deployment_managers():
        validate_not_equals(deployment_manager.get_deployment_manager_id(), "", "deploymentManager entry has a deploymentManagerId")

    get_logger().log_test_case_step("GET a deploymentManager detail by an id from the unfiltered list")
    detail_id = output.get_first().get_deployment_manager_id()
    get_logger().log_info(f"deploymentManager detail id: {detail_id}")
    detail_output = inventory_keywords.get_deployment_manager(detail_id)
    validate_equals(detail_output.get_first().get_deployment_manager_id(), detail_id, "deploymentManager detail returns the requested deploymentManagerId")
