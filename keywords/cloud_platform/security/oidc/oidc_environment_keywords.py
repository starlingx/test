import os
import shutil
import subprocess
import tempfile
import time
import zipfile

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.remote_cli.object.remote_cli_oidc_setup_output import RemoteCliOidcSetupOutput
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
        get_logger().log_info("Step 0: Ensure kubelogin plugin installed on controller")
        self.ensure_kubelogin_installed_on_controller()

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
        self.helm_override_keywords.update_helm_override(dex_overrides_yaml, oidc_app_name, "dex", namespace, reuse_values=False)

        get_logger().log_info("Step 2b: Update oidc-client override to use oidc-auth-apps-certificate")
        oidc_client_template = get_stx_resource_path("resources/cloud_platform/security/oidc/oidc-client-overrides.yaml")
        remote_oidc_client_override = f"{working_dir}/oidc-client-overrides.yaml"
        self.file_keywords.upload_file(oidc_client_template, remote_oidc_client_override)
        self.helm_override_keywords.update_helm_override(remote_oidc_client_override, oidc_app_name, "oidc-client", namespace, reuse_values=False)

        get_logger().log_info("Step 2c: Ensure secret-observer has user override (platform requires all 3 charts)")
        secret_observer_override = f"{working_dir}/secret-observer-overrides.yaml"
        self.ssh_connection.send(f"echo '{{}}' > {secret_observer_override}")
        self.helm_override_keywords.update_helm_override(secret_observer_override, oidc_app_name, "secret-observer", namespace, reuse_values=True)

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

    def ensure_kubelogin_installed_on_controller(self) -> None:
        """Ensure the kubectl-oidc_login (kubelogin) plugin is installed on the remote controller.

        Checks if the kubelogin plugin is available in the controller's PATH
        via a login shell. If not found, downloads the release zip, extracts
        the binary, and installs it to ~/.local/bin/kubectl-oidc_login on the
        controller. The login shell (bash -lc) includes ~/.local/bin in PATH
        on StarlingX systems.
        """
        output = self.ssh_connection.send("bash -lc 'which kubectl-oidc_login' 2>/dev/null || echo NOT_FOUND")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        if "NOT_FOUND" not in raw:
            get_logger().log_info("kubelogin plugin already installed on controller")
            return

        get_logger().log_info("kubelogin plugin not found on controller; installing")
        security_config = ConfigurationManager.get_security_config()
        download_url = security_config.get_oidc_keycloak_kubelogin_download_url()

        install_cmd = "mkdir -p ~/.local/bin && " f"curl -fsSL '{download_url}' -o /tmp/kubelogin.zip && " "cd /tmp && unzip -o kubelogin.zip kubelogin && " "mv kubelogin ~/.local/bin/kubectl-oidc_login && " "chmod +x ~/.local/bin/kubectl-oidc_login && " "rm -f /tmp/kubelogin.zip"
        self.ssh_connection.send(install_cmd)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("kubelogin plugin installed on controller at ~/.local/bin/kubectl-oidc_login")

    def ensure_kubelogin_installed(self) -> None:
        """Ensure the kubectl-oidc_login (kubelogin) plugin is installed on the local test machine.

        Checks if the kubelogin plugin is available in PATH. If not found,
        downloads the release zip from the configured URL, extracts the
        binary, and installs it to ~/.local/bin/kubectl-oidc_login.
        Adds ~/.local/bin to PATH if not already present.
        """
        if shutil.which("kubectl-oidc_login") is not None:
            get_logger().log_info("kubelogin plugin already installed")
            return

        get_logger().log_info("kubelogin plugin not found; installing from configured URL")
        security_config = ConfigurationManager.get_security_config()
        download_url = security_config.get_oidc_keycloak_kubelogin_download_url()

        local_bin_dir = os.path.join(os.path.expanduser("~"), ".local", "bin")
        os.makedirs(local_bin_dir, exist_ok=True)

        if local_bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{local_bin_dir}:{os.environ.get('PATH', '')}"

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, "kubelogin.zip")
            get_logger().log_info(f"Downloading kubelogin from: {download_url}")
            subprocess.run(["curl", "-fsSL", "-o", zip_path, download_url], check=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_dir)

            extracted_binary = os.path.join(tmp_dir, "kubelogin")
            if not os.path.exists(extracted_binary):
                raise FileNotFoundError(f"kubelogin binary not found in extracted archive at {tmp_dir}")

            install_path = os.path.join(local_bin_dir, "kubectl-oidc_login")
            shutil.copy2(extracted_binary, install_path)
            os.chmod(install_path, 0o755)

        validate_equals(shutil.which("kubectl-oidc_login") is not None, True, "kubelogin plugin should be installed after download")
        get_logger().log_info(f"kubelogin plugin installed successfully at {install_path}")

    def teardown(self, oidc_app_name: str, namespace: str) -> None:
        """Remove OIDC app and delete overrides to leave lab in safe state.

        Cleans up test-specific resources (secrets, ClusterRoleBindings) but
        leaves helm overrides and app in applied state. The next test's setup
        uses reuse_values=False which fully replaces overrides with fresh values.

        Args:
            oidc_app_name (str): Name of the OIDC application (e.g., 'oidc-auth-apps').
            namespace (str): Kubernetes namespace (e.g., 'kube-system').
        """
        get_logger().log_teardown_step("Removing upstream IdP CA secret")
        self.ssh_connection.send(f"export KUBECONFIG=/etc/kubernetes/admin.conf;kubectl delete -n {namespace} secret oidc-upstream-idp-ca --ignore-not-found")

        get_logger().log_teardown_step("Removing ClusterRoleBinding")
        self.ssh_connection.send("export KUBECONFIG=/etc/kubernetes/admin.conf;kubectl delete clusterrolebinding wrcp-admin-binding --ignore-not-found")

        get_logger().log_info("OIDC teardown complete — app remains applied with valid overrides")

    def _wait_for_app_status(self, app_name: str, expected_status: str, timeout: int = 300) -> None:
        """Wait for application to reach expected status.

        Args:
            app_name (str): Application name.
            expected_status (str): Expected status string (e.g., 'uploaded', 'applied').
            timeout (int): Maximum wait time in seconds.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            output = self.ssh_connection.send(f"source /etc/platform/openrc && system application-show {app_name} | grep status")
            raw = "\n".join(output) if isinstance(output, list) else str(output)
            if expected_status in raw:
                return
            time.sleep(10)
        get_logger().log_info(f"Warning: {app_name} did not reach '{expected_status}' within {timeout}s")

    def setup_remote(self, oam_ip: str, ca_cert_filename: str, kubeconfig_filename: str, oidc_client_id: str, oidc_client_secret: str) -> RemoteCliOidcSetupOutput:
        """Set up the local OIDC kubectl environment on the test machine.

        Downloads the system-local-ca certificate from the controller to the
        local log resources directory and generates the remote kubeconfig
        locally. Does not modify dex or oidc-auth-apps.

        Args:
            oam_ip (str): OAM floating IP (bracket-wrapped for IPv6).
            ca_cert_filename (str): Filename for the system-local-ca certificate.
            kubeconfig_filename (str): Filename for the remote OIDC kubeconfig.
            oidc_client_id (str): Static OIDC client ID for kubeconfig.
            oidc_client_secret (str): Static OIDC client secret for kubeconfig.

        Returns:
            RemoteCliOidcSetupOutput: Output object containing local paths to the CA cert and kubeconfig.
        """
        log_folder = ConfigurationManager.get_logger_config().get_test_case_resources_log_location()

        self.ensure_kubelogin_installed()

        get_logger().log_info("Step 1: Download system-local-ca certificate to local machine")
        ca_cert_content = self.kubectl_get_secrets.get_secret_with_custom_output(
            secret_name="system-local-ca",
            namespace="cert-manager",
            output_format="jsonpath",
            extra_parameters="'{.data.ca\\.crt}'",
            base64=True,
        )
        local_ca_cert_path = os.path.join(log_folder, ca_cert_filename)
        with open(local_ca_cert_path, "w") as f:
            f.write(ca_cert_content if isinstance(ca_cert_content, str) else "\n".join(ca_cert_content))
        validate_equals(os.path.exists(local_ca_cert_path), True, f"Local CA cert should exist at '{local_ca_cert_path}'")

        get_logger().log_info("Step 2: Generate remote OIDC kubeconfig locally")
        template_file = get_stx_resource_path("resources/cloud_platform/security/oidc/remote-oidc-login-kubeconfig.yml")
        replacement_dict = {
            "ca_cert_filename": local_ca_cert_path,
            "oam_ip": oam_ip,
            "oidc_client_id": oidc_client_id,
            "oidc_client_secret": oidc_client_secret,
        }
        local_kubeconfig_path = self.yaml_keywords.generate_yaml_file_from_template(template_file, replacement_dict, kubeconfig_filename, "", copy_to_remote=False)
        validate_equals(os.path.exists(local_kubeconfig_path), True, f"Local kubeconfig should exist at '{local_kubeconfig_path}'")

        return RemoteCliOidcSetupOutput(local_ca_cert_path, local_kubeconfig_path)

    def setup_remotecli(self, oam_ip: str, ca_cert_filename: str, kubeconfig_filename: str, oidc_client_id: str, oidc_client_secret: str) -> RemoteCliOidcSetupOutput:
        """Set up the OIDC kubectl environment for use inside the remote CLI container.

        Downloads the system-local-ca certificate from the controller to the
        local log resources directory and generates the remote CLI kubeconfig
        locally. The kubeconfig uses --skip-open-browser so kubelogin prints
        the login URL to stdout instead of opening a browser, which is required
        when kubectl runs inside a headless container.

        Args:
            oam_ip (str): OAM floating IP (bracket-wrapped for IPv6).
            ca_cert_filename (str): Filename for the system-local-ca certificate.
            kubeconfig_filename (str): Filename for the remote CLI OIDC kubeconfig.
            oidc_client_id (str): Static OIDC client ID for kubeconfig.
            oidc_client_secret (str): Static OIDC client secret for kubeconfig.

        Returns:
            RemoteCliOidcSetupOutput: Output object containing local paths to the CA cert and kubeconfig.
        """
        log_folder = ConfigurationManager.get_logger_config().get_test_case_resources_log_location()

        get_logger().log_info("Step 1: Download system-local-ca certificate to local machine")
        ca_cert_content = self.kubectl_get_secrets.get_secret_with_custom_output(
            secret_name="system-local-ca",
            namespace="cert-manager",
            output_format="jsonpath",
            extra_parameters="'{.data.ca\\.crt}'",
            base64=True,
        )
        local_ca_cert_path = os.path.join(log_folder, ca_cert_filename)
        with open(local_ca_cert_path, "w") as f:
            f.write(ca_cert_content if isinstance(ca_cert_content, str) else "\n".join(ca_cert_content))
        validate_equals(os.path.exists(local_ca_cert_path), True, f"Local CA cert should exist at '{local_ca_cert_path}'")

        get_logger().log_info("Step 2: Generate remote CLI OIDC kubeconfig locally")
        template_file = get_stx_resource_path("resources/cloud_platform/security/oidc/remotecli-oidc-login-kubeconfig.yml")
        replacement_dict = {
            "ca_cert_filename": ca_cert_filename,
            "oam_ip": oam_ip,
            "oidc_client_id": oidc_client_id,
            "oidc_client_secret": oidc_client_secret,
        }
        local_kubeconfig_path = self.yaml_keywords.generate_yaml_file_from_template(template_file, replacement_dict, kubeconfig_filename, "", copy_to_remote=False)
        validate_equals(os.path.exists(local_kubeconfig_path), True, f"Local kubeconfig should exist at '{local_kubeconfig_path}'")

        return RemoteCliOidcSetupOutput(local_ca_cert_path, local_kubeconfig_path)

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
