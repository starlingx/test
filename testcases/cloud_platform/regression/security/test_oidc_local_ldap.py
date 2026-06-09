"""DEX Connector Attribute Mappings — Local LDAP and oidc-username-claim.

Tests the recommended emailAttr, nameAttr, and usernameAttr mappings
for the Local LDAP DEX connector, and validates oidc-username-claim
via service-parameter CLI.
"""

import json5
from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords


def _load_dex_config() -> dict:
    """Load DEX connector config from JSON5.

    Returns:
        dict: Configuration dictionary.
    """
    path = get_stx_resource_path("config/security/files/dex_connector_config.json5")
    with open(path) as f:
        return json5.load(f)["dex_connector"]


def _apply_ldap_attr_override(ssh_connection: SSHConnection, config: dict, email_attr: str, name_attr: str) -> None:
    """Generate and apply LDAP override with specified attribute mappings.

    Args:
        ssh_connection (SSHConnection): Active controller SSH.
        config (dict): DEX connector configuration.
        email_attr (str): emailAttr value.
        name_attr (str): nameAttr value.
    """
    yaml_keywords = YamlKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    dex_keywords = DexConnectorKeywords(ssh_connection)
    lab_config = ConfigurationManager.get_lab_config()

    working_dir = config["working_dir"]
    file_keywords.create_directory(working_dir)

    template = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-ldap-attr-mapping-overrides.yaml")
    replacements = {
        "mgmt_ip": lab_config.get_management_ip(),
        "bind_pw": ConfigurationManager.get_security_config().get_domain_name(),
        "email_attr": email_attr,
        "name_attr": name_attr,
    }
    override_file = yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-ldap-attr-test.yaml", working_dir)

    dex_keywords.apply_dex_override_and_reapply(override_file, config["oidc_app_name"], config["namespace"])


@mark.p1
@mark.lab_has_standby_controller
def test_local_ldap_recommended_attr_mappings(request):
    """Test recommended emailAttr/nameAttr for Local LDAP connector.

    Test Steps:
        - Apply DEX override with emailAttr=mail, nameAttr=gecos
        - Reapply oidc-auth-apps
        - Verify helm-override-show contains the recommended mappings
    """
    config = _load_dex_config()
    ldap = config["local_ldap"]
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        FileKeywords(ssh).remove_directory(config["working_dir"])

    request.addfinalizer(cleanup)

    get_logger().log_info(f"Applying Local LDAP attrs: emailAttr={ldap['email_attr']}, nameAttr={ldap['name_attr']}")
    _apply_ldap_attr_override(ssh_connection, config, ldap["email_attr"], ldap["name_attr"])

    dex_keywords = DexConnectorKeywords(ssh_connection)
    dex_keywords.helm_override_keywords.verify_helm_user_override(ldap["email_attr"], config["oidc_app_name"], "dex", config["namespace"])
    dex_keywords.helm_override_keywords.verify_helm_user_override(ldap["name_attr"], config["oidc_app_name"], "dex", config["namespace"])


@mark.p1
@mark.lab_has_standby_controller
def test_oidc_username_claim_set_via_service_parameter(request):
    """Test oidc-username-claim modification via service-parameter CLI.

    Test Steps:
        - Set oidc-username-claim to 'username', verify
        - Set oidc-username-claim to 'email', verify
        - Restore to 'username'
    """
    config = _load_dex_config()
    claim = config["oidc_username_claim"]
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dex_keywords = DexConnectorKeywords(ssh_connection)

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        DexConnectorKeywords(ssh).set_oidc_username_claim(claim["default"])

    request.addfinalizer(cleanup)

    get_logger().log_info("Setting oidc-username-claim='preferred_username'")
    dex_keywords.set_oidc_username_claim(claim["default"])
    validate_equals(dex_keywords.get_oidc_username_claim(), claim["default"], "Claim should be 'preferred_username'")

    get_logger().log_info("Setting oidc-username-claim='email'")
    dex_keywords.set_oidc_username_claim(claim["alternative"])
    validate_equals(dex_keywords.get_oidc_username_claim(), claim["alternative"], "Claim should be 'email'")


@mark.p2
@mark.lab_has_standby_controller
def test_oidc_username_claim_default_is_username():
    """Test default bootstrap oidc-username-claim is 'preferred_username'.

    Test Steps:
        - Query current oidc-username-claim service parameter
        - Verify value is 'preferred_username'
    """
    config = _load_dex_config()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dex_keywords = DexConnectorKeywords(ssh_connection)

    current = dex_keywords.get_oidc_username_claim()
    validate_equals(current, config["oidc_username_claim"]["default"], "Default oidc-username-claim should be 'preferred_username'")
