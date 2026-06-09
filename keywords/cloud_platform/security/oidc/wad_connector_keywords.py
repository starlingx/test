"""Keywords for WAD (Windows Active Directory) DEX connector operations."""

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords


class WadConnectorKeywords(DexConnectorKeywords):
    """Keywords for WAD (Windows Active Directory) DEX connector attribute mapping and authentication."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize WAD connector keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        super().__init__(ssh_connection)
        self.yaml_keywords = YamlKeywords(ssh_connection)
        self.file_keywords = FileKeywords(ssh_connection)

    def apply_wad_override(self, config: dict, email_attr: str, username_attr: str, name_attr: str) -> None:
        """Generate WAD-specific helm override YAML and apply to oidc-auth-apps.

        Generates a DEX helm override file from the WAD connector template
        with the specified attribute mappings, then applies it and re-applies
        the oidc-auth-apps application.

        Args:
            config (dict): DEX connector configuration with working_dir, oidc_app_name, namespace.
            email_attr (str): WAD emailAttr mapping (e.g., 'mail').
            username_attr (str): WAD usernameAttr mapping (e.g., 'sAMAccountName').
            name_attr (str): WAD nameAttr mapping (e.g., 'displayName').
        """
        lab_config = ConfigurationManager.get_lab_config()
        security_config = ConfigurationManager.get_security_config()

        self.file_keywords.create_directory(config["working_dir"])

        template = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-wad-attr-mapping-overrides.yaml")
        replacements = {
            "oam_ip": lab_config.get_floating_ip(),
            "wad_server": security_config.get_wad_server(),
            "bind_dn": security_config.get_wad_bind_dn(),
            "bind_pw": security_config.get_wad_bind_password(),
            "email_attr": email_attr,
            "username_attr": username_attr,
            "name_attr": name_attr,
        }

        get_logger().log_info(f"Applying WAD override: emailAttr={email_attr}, " f"usernameAttr={username_attr}, nameAttr={name_attr}")
        override_file = self.yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-wad-attr-test.yaml", config["working_dir"])
        self.apply_dex_override_and_reapply(override_file, config["oidc_app_name"], config["namespace"])

    def get_wad_token(self, oam_ip: str, username: str, password: str) -> str:
        """Authenticate via WAD connector and return an ID token.

        Uses oidc-auth on the controller to authenticate the WAD user
        and retrieve the OIDC ID token from the token cache.

        Args:
            oam_ip (str): OAM floating IP of the lab.
            username (str): WAD username (sAMAccountName).
            password (str): WAD user password.

        Returns:
            str: The OIDC ID token string.
        """
        get_logger().log_info(f"Authenticating WAD user '{username}' via oidc-auth")
        self.ssh_connection.send(f"oidc-auth -client-id stx-oidc-client-app -p {password} -u {username}")
        self.validate_success_return_code(self.ssh_connection)
        self.ssh_connection.send("cat ~/.kube/oidc-login/id-token")
        self.validate_success_return_code(self.ssh_connection)
        token = self.ssh_connection.get_output()
        sanitized = token.strip()
        if not sanitized or "error" in sanitized.lower():
            get_logger().log_error(f"Invalid token output for WAD user '{username}': {sanitized[:100]}")
        return sanitized
