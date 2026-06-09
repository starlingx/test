"""Keywords for DEX connector attribute mapping and oidc-username-claim operations."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords


class DexConnectorKeywords(BaseKeyword):
    """Keywords for DEX connector attribute mapping and oidc-username-claim operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize DEX connector keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection
        self.helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
        self.system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        self.service_param_keywords = SystemServiceParameterKeywords(ssh_connection)

    def apply_dex_override_and_reapply(self, yaml_file: str, app_name: str, namespace: str) -> None:
        """Apply DEX helm override and re-apply oidc-auth-apps.

        Args:
            yaml_file (str): Path to override YAML on controller.
            app_name (str): Application name (e.g., 'oidc-auth-apps').
            namespace (str): Chart namespace.
        """
        get_logger().log_info(f"Applying DEX helm override: {yaml_file}")
        self.helm_override_keywords.update_helm_override(yaml_file, app_name, "dex", namespace, reuse_values=True)
        self.system_app_apply.system_application_apply(app_name)

    def set_oidc_username_claim(self, claim_value: str) -> None:
        """Set oidc-username-claim and apply kubernetes service parameters.

        Args:
            claim_value (str): Claim value (e.g., 'preferred_username' or 'email').
        """
        get_logger().log_info(f"Setting oidc-username-claim='{claim_value}'")
        self.service_param_keywords.modify_service_parameter("kubernetes", "kube_apiserver", "oidc-username-claim", claim_value)
        self.service_param_keywords.apply_service_parameters("kubernetes")

    def get_oidc_username_claim(self) -> str:
        """Get current oidc-username-claim value.

        Returns:
            str: Current value, or empty string if not set.
        """
        output = self.service_param_keywords.list_service_parameters(service="kubernetes", section="kube_apiserver")
        for param in output.get_service_parameter_objects():
            if param.get_name() == "oidc-username-claim":
                return param.get_value()
        return ""
