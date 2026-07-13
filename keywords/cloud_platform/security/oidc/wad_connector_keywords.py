"""Keywords for WAD (Windows Active Directory) DEX connector operations."""

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config


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

    def apply_wad_override(self, config: dict, email_attr: str, username_attr: str, name_attr: str, reuse_values: bool = False) -> None:
        """Generate WAD-specific helm override YAML and apply to oidc-auth-apps.

        Generates a DEX helm override file from the WAD connector template
        with the specified attribute mappings, then applies it and re-applies
        the oidc-auth-apps application.

        Args:
            config (dict): DEX connector configuration with working_dir, oidc_app_name, namespace.
            email_attr (str): WAD emailAttr mapping (e.g., 'mail').
            username_attr (str): WAD usernameAttr mapping (e.g., 'sAMAccountName').
            name_attr (str): WAD nameAttr mapping (e.g., 'displayName').
            reuse_values (bool): If True, merge with existing overrides (preserves LDAP connector).
        """
        self.file_keywords.create_directory(config["working_dir"])

        template = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-wad-attr-mapping-overrides.yaml")
        wad_config = config["wad_connector"]
        replacements = {
            "wad_server": wad_config["wad_server"],
            "bind_dn": wad_config["bind_dn"],
            "bind_pw": wad_config["bind_pw"],
            "user_search_base": wad_config["user_search_base"],
            "group_search_base": wad_config["group_search_base"],
            "email_attr": email_attr,
            "username_attr": username_attr,
            "name_attr": name_attr,
        }

        get_logger().log_info(f"Applying WAD override: emailAttr={email_attr}, " f"usernameAttr={username_attr}, nameAttr={name_attr}, reuse_values={reuse_values}")
        override_file = self.yaml_keywords.generate_yaml_file_from_template(template, replacements, "dex-wad-attr-test.yaml", config["working_dir"])

        if reuse_values:
            # Merge with existing override (preserves other connectors like LDAP)
            self.helm_override_keywords.update_helm_override(override_file, config["oidc_app_name"], "dex", config["namespace"], reuse_values=True)
            SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply(config["oidc_app_name"])
            self.wait_for_dex_ready(config["namespace"], raise_on_timeout=True)
        else:
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
        self.ssh_connection.send(f"oidc-auth -p {password} -u {username}")
        self.validate_success_return_code(self.ssh_connection)
        self.ssh_connection.send("cat ~/.kube/oidc-login/id-token")
        self.validate_success_return_code(self.ssh_connection)
        token = self.ssh_connection.get_output()
        sanitized = token.strip()
        if not sanitized or "error" in sanitized.lower():
            get_logger().log_error(f"Invalid token output for WAD user '{username}': {sanitized[:100]}")
        return sanitized

    def ensure_wad_user_mail_attribute(self, config: dict, username: str, email: str) -> None:
        """Ensure a WAD user has the mail attribute set in Active Directory.

        Uses ldapmodify over LDAPS to add or replace the mail attribute on
        the WAD user entry. This is required before tests that configure
        Dex with emailAttr=mail, since Dex rejects login if the attribute
        is missing from the AD entry.

        If the WAD server is unreachable from the controller via ldapmodify,
        falls back to running ldapmodify from inside the Dex pod (which has
        proven network access to the WAD server based on connector operation).

        Args:
            config (dict): DEX connector configuration containing wad_connector settings.
            username (str): WAD username (sAMAccountName).
            email (str): Email address to set on the WAD user.
        """
        wad_config = config["wad_connector"]
        wad_server = wad_config["wad_server"]
        bind_dn = wad_config["bind_dn"]
        bind_pw = wad_config["bind_pw"]
        user_search_base = wad_config["user_search_base"]

        user_dn = f"CN={username},{user_search_base}"
        get_logger().log_info(f"Ensuring WAD user '{username}' has mail attribute set to '{email}'")

        # First verify the attribute is actually missing by querying via Dex pod
        # Try direct ldapmodify from controller first
        ldif = f"dn: {user_dn}\\nchangetype: modify\\nreplace: mail\\nmail: {email}"
        cmd = f"echo -e '{ldif}' | ldapmodify -x -H ldaps://{wad_server} -D '{bind_dn}' -w '{bind_pw}'"
        self.ssh_connection.send(cmd)
        rc = self.ssh_connection.get_return_code()
        if rc == 0:
            get_logger().log_info(f"WAD user '{username}' mail attribute set to '{email}' via controller ldapmodify")
            return

        get_logger().log_info("Controller cannot reach WAD server directly, trying via kubectl exec in Dex pod")

        # Fallback: run ldapsearch from Dex pod to verify mail attribute presence
        dex_pod_cmd = f"kubectl exec -n kube-system $(kubectl get pods -n kube-system " f"-l app.kubernetes.io/name=dex -o jsonpath='{{.items[0].metadata.name}}') " f"-- sh -c \"ldapsearch -x -H ldaps://{wad_server} -D '{bind_dn}' -w '{bind_pw}' " f"-b '{user_dn}' -s base '(objectClass=*)' mail 2>/dev/null | grep -i '^mail:'\""
        self.ssh_connection.send(export_k8s_config(dex_pod_cmd))
        output = self.ssh_connection.get_output() if hasattr(self.ssh_connection, "get_output") else ""
        raw = "\n".join(output) if isinstance(output, list) else str(output)

        if "mail:" in raw.lower():
            get_logger().log_info(f"WAD user '{username}' already has mail attribute set in AD")
            return

        # Try ldapmodify from Dex pod
        dex_modify_cmd = f"kubectl exec -n kube-system $(kubectl get pods -n kube-system " f"-l app.kubernetes.io/name=dex -o jsonpath='{{.items[0].metadata.name}}') " f"-- sh -c \"echo -e 'dn: {user_dn}\\nchangetype: modify\\nadd: mail\\nmail: {email}' " f"| ldapmodify -x -H ldaps://{wad_server} -D '{bind_dn}' -w '{bind_pw}'\""
        self.ssh_connection.send(export_k8s_config(dex_modify_cmd))
        rc = self.ssh_connection.get_return_code()
        if rc == 0:
            get_logger().log_info(f"WAD user '{username}' mail attribute set to '{email}' via Dex pod")
            return

        # Last resort: log warning and let the test decide
        get_logger().log_info(f"WARNING: Could not set mail attribute for WAD user '{username}'. " f"The WAD server may not allow modification from test automation. " f"Ensure the mail attribute is pre-configured in Active Directory.")
