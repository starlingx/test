"""OIDC token-revocation and authentication-precedence tests.

Net-new OIDC regression coverage:
    - revoking a user (removing the LDAP account) blocks that user's OIDC
      access on a subcloud
    - when both Keystone (X-Auth) credentials and an OIDC token are available,
      Keystone authentication takes precedence for the STX CLI

Lab preconditions, which these tests do not create:
    - oidc-auth-apps installed on the System Controller.
    - Local LDAP available for the dex connector.
    - For the revocation test: a Distributed Cloud with at least one subcloud.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.security.oidc.oidc_setup_keywords import OidcSetupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords

TEST_GROUP = "pvtestgroup"
ACCESS_REVOKED_TIMEOUT = 180


@mark.p2
@mark.lab_has_subcloud
def test_oidc_token_revocation_blocks_subcloud_access(request: FixtureRequest):
    """Verify revoking a user blocks that user's OIDC access on a subcloud.

    Test Steps:
        - Set up OIDC on the SC and point the subcloud at the SC dex
        - Create an LDAP user and verify OIDC access on the subcloud
        - Revoke the user by deleting the LDAP account
        - Verify the user can no longer gain OIDC access on the subcloud
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name = lab_config.get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_oam_ip = lab_config.get_subcloud(subcloud_name).get_floating_ip()
    sc_oam_ip = lab_config.get_floating_ip()
    sc_bracketed = f"[{sc_oam_ip}]" if ":" in sc_oam_ip else sc_oam_ip
    sc_oidc_issuer = f"https://{sc_bracketed}:30556/dex"
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_revoke_subcloud_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    sc_crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    subcloud_crb_keywords = KubectlCreateClusterRoleBindingKeywords(subcloud_ssh)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: sc_crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: subcloud_crb_keywords.cleanup_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC on the System Controller")
    oidc_setup.setup_oidc_environment()
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)
    subcloud_crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Point the subcloud kube-apiserver at the System Controller dex")
    oidc_setup.configure_subcloud_oidc_issuer(subcloud_ssh, sc_oidc_issuer)

    get_logger().log_test_case_step("Verify the user initially has OIDC access on the subcloud")
    oidc_setup.verify_user_access(subcloud_oam_ip, username, password, oidc_client_ip=sc_oam_ip)

    get_logger().log_test_case_step("Revoke the user by deleting the LDAP account")
    LdapKeywords(ssh_connection, password).delete_user(username)

    get_logger().log_test_case_step("Verify the revoked user can no longer gain OIDC access on the subcloud")
    validate_equals_with_retry(
        lambda: oidc_setup.is_oidc_login_denied(subcloud_oam_ip, username, password, oidc_client_ip=sc_oam_ip),
        True,
        "Revoked user must be denied OIDC access on the subcloud",
        timeout=ACCESS_REVOKED_TIMEOUT,
        polling_sleep_time=15,
    )


@mark.p2
def test_oidc_keystone_takes_precedence_over_oidc_token(request: FixtureRequest):
    """Verify Keystone (X-Auth) auth takes precedence when an OIDC token is also present.

    Test Steps:
        - Set up OIDC on the System Controller and acquire an OIDC token for a user
        - With both the Keystone admin credentials and the OIDC token available,
          run a system command using default (Keystone) auth
        - Verify the command succeeds via Keystone (X-Auth takes precedence)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_precedence_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC on the System Controller")
    oidc_setup.setup_oidc_environment()
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)
    crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Acquire an OIDC token for the user, then verify Keystone auth still works")
    oidc_setup.verify_user_access(oam_ip, username, password)

    get_logger().log_test_case_step("Verify Keystone (X-Auth) auth takes precedence for the STX CLI")
    host_list = SystemHostListKeywords(ssh_connection).get_system_host_list()
    validate_equals(len(host_list.get_hosts()) > 0, True, "Keystone (X-Auth) auth must return hosts even when an OIDC token is present")
