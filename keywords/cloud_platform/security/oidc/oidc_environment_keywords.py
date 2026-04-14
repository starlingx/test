from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.secret.kubectl_delete_secret_keywords import KubectlDeleteSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords


class OidcEnvironmentKeywords(BaseKeyword):
    """Lifecycle keywords for setting up and tearing down the OIDC Keycloak environment."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Active controller SSH connection.
        """
        self.ssh_connection = ssh_connection
        self.yaml_keywords = YamlKeywords(ssh_connection)
        self.kubectl_file_apply = KubectlFileApplyKeywords(ssh_connection)
        self.kubectl_get_secrets = KubectlGetSecretsKeywords(ssh_connection)
        self.helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
        self.system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        self.file_keywords = FileKeywords(ssh_connection)
        self.kubectl_delete_secrets = KubectlDeleteSecretsKeywords(ssh_connection)
        self.kubectl_crb = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    def setup(self, oam_ip: str, namespace: str, secret_name: str, oidc_app_name: str, working_dir: str, ca_cert_pem: str, client_id: str, client_secret: str, external_idp_issuer_url: str, ca_cert_filename: str, kubeconfig_filename: str, oidc_client_id: str, oidc_client_secret: str, crb_binding_name: str = None, crb_cluster_role: str = None, crb_group: str = None) -> str:
        """Set up the full OIDC Keycloak environment.

        Imports the upstream IdP CA secret, applies dex Helm overrides,
        applies oidc-auth-apps, optionally creates the ClusterRoleBinding,
        extracts the system-local-ca certificate, and generates the local kubeconfig.

        Args:
            oam_ip (str): OAM floating IP, bracket-wrapped if IPv6.
            namespace (str): Kubernetes namespace for OIDC secrets.
            secret_name (str): Name of the upstream IdP CA secret.
            oidc_app_name (str): Name of the OIDC application to apply.
            working_dir (str): Remote working directory for generated files.
            ca_cert_pem (str): PEM-encoded Keycloak CA certificate content.
            client_id (str): Keycloak OIDC client ID.
            client_secret (str): Keycloak OIDC client secret.
            external_idp_issuer_url (str): Keycloak realm issuer URL.
            ca_cert_filename (str): Filename for the system-local-ca certificate.
            kubeconfig_filename (str): Filename for the local OIDC kubeconfig.
            oidc_client_id (str): Static OIDC client ID for kubeconfig.
            oidc_client_secret (str): Static OIDC client secret for kubeconfig.
            crb_binding_name (str): ClusterRoleBinding name. Skipped if None.
            crb_cluster_role (str): Cluster role to bind. Skipped if None.
            crb_group (str): Group to bind the cluster role to. Skipped if None.

        Returns:
            str: Full path to the generated kubeconfig file on the remote host.
        """
        get_logger().log_info("Step 1: Import the upstream IdP CA certificate")
        self.file_keywords.create_directory(working_dir)
        template_file = get_stx_resource_path("resources/cloud_platform/security/oidc/upstream-idp-ca-secret.yaml")
        replacement_dict = {"keycloak_ca_cert": ca_cert_pem.replace("\n", "\\n")}
        secret_yaml = self.yaml_keywords.generate_yaml_file_from_template(template_file, replacement_dict, "upstream-idp-ca-secret.yaml", working_dir)
        self.kubectl_file_apply.apply_resource_from_yaml(secret_yaml)
        secret_present = secret_name in self.kubectl_get_secrets.get_secret_names(namespace=namespace)
        validate_equals(secret_present, True, f"Secret '{secret_name}' should be present in '{namespace}' after creation")

        get_logger().log_info("Step 2: Create Helm overrides configuration for dex Keycloak connector")
        template_file = get_stx_resource_path("resources/cloud_platform/security/oidc/dex-keycloak-overrides.yaml")
        replacement_dict = {
            "oam_ip": oam_ip,
            "client_id": client_id,
            "client_secret": client_secret,
            "external_idp_issuer_url": external_idp_issuer_url,
            "oidc_client_secret": oidc_client_secret,
        }
        dex_overrides_yaml = self.yaml_keywords.generate_yaml_file_from_template(template_file, replacement_dict, "dex-keycloak-overrides.yaml", working_dir)
        self.helm_override_keywords.update_helm_override(dex_overrides_yaml, oidc_app_name, "dex", namespace, reuse_values=True)

        get_logger().log_info("Step 3: Apply the oidc-auth-apps configuration")
        system_app_apply_output = self.system_app_apply.system_application_apply(oidc_app_name)
        validate_equals(system_app_apply_output.get_system_application_object().get_status(), "applied", f"{oidc_app_name} should be in applied state")

        get_logger().log_info("Step 4: Create ClusterRoleBinding for wrcp-admin group")
        if crb_binding_name and crb_cluster_role and crb_group:
            self.kubectl_crb.create_clusterrolebinding_for_group(binding_name=crb_binding_name, clusterrole=crb_cluster_role, group=crb_group)

        get_logger().log_info("Step 5: Extract and save the system-local-ca certificate")
        ca_cert_path = f"{working_dir}{ca_cert_filename}"
        ca_cert_content = self.kubectl_get_secrets.get_secret_with_custom_output(
            secret_name="system-local-ca",
            namespace="cert-manager",
            output_format="jsonpath",
            extra_parameters="'{.data.ca\\.crt}'",
            base64=True,
        )
        self.file_keywords.create_file_with_heredoc(ca_cert_path, ca_cert_content)
        validate_equals(self.file_keywords.file_exists(ca_cert_path), True, f"system-local-ca certificate should be saved at '{ca_cert_path}'")

        get_logger().log_info("Step 6: Create local OIDC login kubeconfig")
        kubeconfig_path = f"{working_dir}{kubeconfig_filename}"
        template_file = get_stx_resource_path("resources/cloud_platform/security/oidc/local-oidc-login-kubeconfig.yml")
        replacement_dict = {
            "ca_cert_filename": ca_cert_path,
            "oam_ip": oam_ip,
            "oidc_client_id": oidc_client_id,
            "oidc_client_secret": oidc_client_secret,
        }
        self.yaml_keywords.generate_yaml_file_from_template(template_file, replacement_dict, kubeconfig_filename, working_dir)
        validate_equals(self.file_keywords.file_exists(kubeconfig_path), True, f"Kubeconfig should be saved at '{kubeconfig_path}'")

        return kubeconfig_path

    def cleanup(self, secret_name: str, namespace: str, crb_binding_name: str) -> None:
        """Clean up the OIDC Keycloak environment.

        Deletes the upstream IdP CA secret and the ClusterRoleBinding.

        Args:
            secret_name (str): Name of the upstream IdP CA secret to delete.
            namespace (str): Kubernetes namespace containing the secret.
            crb_binding_name (str): Name of the ClusterRoleBinding to delete.
        """
        get_logger().log_info(f"Cleanup: deleting secret '{secret_name}' from namespace '{namespace}'")
        self.kubectl_delete_secrets.cleanup_secret(secret_name=secret_name, namespace=namespace)
        get_logger().log_info(f"Cleanup: deleting ClusterRoleBinding '{crb_binding_name}'")
        self.kubectl_crb.delete_clusterrolebinding(crb_binding_name)
