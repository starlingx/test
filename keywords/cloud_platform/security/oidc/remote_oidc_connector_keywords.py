"""Keywords for Remote OIDC (Keycloak) DEX connector operations."""

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords


class RemoteOidcConnectorKeywords(DexConnectorKeywords):
    """Keywords for Remote OIDC (Keycloak) DEX connector claim mapping and authentication."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize Remote OIDC connector keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        super().__init__(ssh_connection)
        self.yaml_keywords = YamlKeywords(ssh_connection)
        self.file_keywords = FileKeywords(ssh_connection)

    def apply_remote_oidc_override(self, config: dict, claim_mapping: dict) -> None:
        """Generate Remote OIDC connector override YAML and apply to oidc-auth-apps.

        Generates a DEX helm override file from the Keycloak connector template
        with the specified claim mapping, then applies it and re-applies
        the oidc-auth-apps application.

        Args:
            config (dict): DEX connector configuration with working_dir, oidc_app_name, namespace.
            claim_mapping (dict): Claim mapping with keys 'email', 'name',
                'preferred_username' mapping to the corresponding IdP claim names.
        """
        lab_config = ConfigurationManager.get_lab_config()
        security_config = ConfigurationManager.get_security_config()

        self.file_keywords.create_directory(config["working_dir"])

        template = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-remote-oidc-claim-mapping-overrides.yaml")
        replacements = {
            "oam_ip": lab_config.get_floating_ip(),
            "client_id": security_config.get_keycloak_client_id(),
            "client_secret": security_config.get_keycloak_client_secret(),
            "external_idp_issuer_url": security_config.get_keycloak_issuer_url(),
            "oidc_client_secret": security_config.get_oidc_client_secret(),
            "email_claim": claim_mapping.get("email", "email"),
            "name_claim": claim_mapping.get("name", "name"),
            "preferred_username_claim": claim_mapping.get("preferred_username", "preferred_username"),
        }

        get_logger().log_info(f"Applying Remote OIDC override with claimMapping: {claim_mapping}")
        override_file = self.yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-remote-oidc-claim-test.yaml", config["working_dir"])
        self.apply_dex_override_and_reapply(override_file, config["oidc_app_name"], config["namespace"])

    def get_keycloak_token(self, oam_ip: str, username: str, password: str, client_id: str, client_secret: str, realm: str) -> str:
        """Authenticate via Keycloak and return an ID token.

        Uses oidc-auth or kubelogin flow to authenticate against the
        Keycloak realm and retrieve the OIDC ID token.

        Args:
            oam_ip (str): OAM floating IP of the lab.
            username (str): Keycloak username.
            password (str): Keycloak user password.
            client_id (str): Keycloak OIDC client ID.
            client_secret (str): Keycloak OIDC client secret.
            realm (str): Keycloak realm name.

        Returns:
            str: The OIDC ID token string.
        """
        get_logger().log_info(f"Authenticating Keycloak user '{username}' in realm '{realm}'")
        self.ssh_connection.send(f"oidc-auth -client-id {client_id} -client-secret {client_secret} " f"-p {password} -u {username}")
        self.validate_success_return_code(self.ssh_connection)
        self.ssh_connection.send("cat ~/.kube/oidc-login/id-token")
        self.validate_success_return_code(self.ssh_connection)
        token = self.ssh_connection.get_output()
        sanitized = token.strip()
        if not sanitized or "error" in sanitized.lower():
            get_logger().log_error(f"Invalid token output for Keycloak user '{username}': {sanitized[:100]}")
        return sanitized
