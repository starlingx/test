"""O-RAN O2 IMS API — walking skeleton (api_versions + O-Cloud root).

Proves the whole O2 IMS API stack end to end against a prepared environment:
configuration, mutual TLS with the client certificate, on-controller Bearer
token acquisition, and routing. Reads only; changes nothing.

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
    pytest starlingx/testcases/cloud_platform/regression/applications/o_ran_o2/test_o2_api_walking_skeleton.py \
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


@mark.p2
def test_o2_api_walking_skeleton(request: FixtureRequest):
    """WALKING-SKELETON: Read api_versions and the O-Cloud root over the O2 IMS API.

    Verifies the first authenticated O2 IMS API reads succeed end to end: the
    api_versions endpoint returns 200 with a non-empty version list, and the
    O-Cloud root returns 200 with a present, non-empty oCloudId and a present
    globalcloudId. Does not assert globalcloudId equals any configured value
    (its schema default is an empty string, and each deployment generates a
    different id).

    Preconditions:
        - The O2 bring-up has been run and left the environment standing.

    Setup:
        - Establish SSH connection to the active controller.
        - Verify the O2 environment is ready (certs, o2api pod, token).
        - Acquire an O2 Bearer token on the controller.

    Test Steps:
        1. GET api_versions and verify a non-empty version list.
        2. GET the O-Cloud root and verify oCloudId is present and non-empty and
           globalcloudId is present.

    Teardown:
        - None. The environment is left standing for subsequent API tests.
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    cert_dir = ConfigurationManager.get_o2ims_config().get_cert_dir()

    get_logger().log_setup_step("Verify the O2 environment is ready (certs, o2api pod, token)")
    O2EnvironmentKeywords(ssh_connection).verify_environment_ready(cert_dir)

    get_logger().log_setup_step("Acquire an O2 Bearer token on the controller")
    token = O2TokenKeywords(ssh_connection).get_token()

    inventory_keywords = O2InventoryKeywords(O2RestClient(cert_dir, ssh_connection, token=token))

    get_logger().log_test_case_step("GET api_versions and verify a non-empty version list")
    api_versions_output = inventory_keywords.get_api_versions()
    validate_not_equals(api_versions_output.is_empty(), True, "api_versions list is not empty")
    get_logger().log_info(f"API versions: {api_versions_output.get_versions()}")

    get_logger().log_test_case_step("GET the O-Cloud root and verify oCloudId present and globalcloudId present")
    ocloud_output = inventory_keywords.get_ocloud_root()
    validate_not_equals(ocloud_output.get_ocloud_id(), "", "O-Cloud root oCloudId is present and non-empty")
    validate_equals(ocloud_output.has_global_cloud_id(), True, "O-Cloud root globalcloudId is present")
    get_logger().log_info(f"oCloudId: {ocloud_output.get_ocloud_id()}")
