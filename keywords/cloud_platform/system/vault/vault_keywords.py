"""Keywords for HashiCorp Vault application operations."""

import json
import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords


class VaultKeywords(BaseKeyword):
    """Keywords for HashiCorp Vault application operations."""

    NAMESPACE = "vault"
    VAULT_API = "https://sva-vault.vault.svc.cluster.local:8200"

    def __init__(self, ssh_connection: SSHConnection, ssh_user_home: str = "/home/sysadmin"):
        """Initialize vault keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
            ssh_user_home (str): Home directory of the SSH user on the lab.
        """
        self.ssh_connection = ssh_connection
        self.ssh_user_home = ssh_user_home
        self.ca_cert_path = f"{ssh_user_home}/vault_ca.pem"
        self.k8s = K8sBaseKeyword(ssh_connection)
        self.file_keywords = FileKeywords(ssh_connection)
        self.kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
        self.kubectl_secrets = KubectlGetSecretsKeywords(ssh_connection)
        self.kubectl_exec = KubectlExecInPodsKeywords(ssh_connection)
        self.kubectl_delete = KubectlDeleteResourceKeywords(ssh_connection)

    def get_root_token(self) -> str:
        """Retrieve the vault root token from kubernetes secret.

        Returns:
            str: The vault root token.
        """
        token = self.kubectl_secrets.get_secret_with_custom_output("cluster-key-root", self.NAMESPACE, "jsonpath", "'{.data.strdata}'", base64=True)
        return token.strip().strip("'")

    def _is_vault_server_pod(self, pod_name: str) -> bool:
        """Check if a pod name is a vault server pod (not agent or manager).

        Args:
            pod_name (str): The pod name to check.

        Returns:
            bool: True if it is a vault server pod.
        """
        return pod_name.startswith("sva-vault-") and not pod_name.startswith("sva-vault-agent") and not pod_name.startswith("sva-vault-manager")

    def wait_for_unseal(self, timeout: int = 300) -> bool:
        """Wait for all vault server pods to be unsealed (ready).

        Args:
            timeout (int): Maximum seconds to wait for unseal.

        Returns:
            bool: True if vault is unsealed, False if timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            pods_output = self.kubectl_pods.get_pods(self.NAMESPACE)
            vault_pods = [p for p in pods_output.get_pods_with_status("Running") if self._is_vault_server_pod(p.get_name())]
            if vault_pods and all(p.is_ready() for p in vault_pods):
                get_logger().log_info("All vault server pods are unsealed and ready")
                return True
            get_logger().log_info("Vault pods not all ready yet, waiting 15s...")
            time.sleep(15)
        get_logger().log_info("Vault unseal wait timed out")
        return False

    def run_setup_script(self, script_path: str) -> None:
        """Upload and execute the vault setup script on the controller.

        Args:
            script_path (str): Local path to the setup script.
        """
        remote_script = f"{self.ssh_user_home}/setup_vault.sh"
        self.file_keywords.upload_file(script_path, remote_script, overwrite=True)
        self.ssh_connection.send(self.k8s.k8s_config.export(f"chmod +x {remote_script} && {remote_script}"))

    def create_secret(self, path: str, data: dict, token: str) -> None:
        """Create a secret in vault using the REST API (KV v2).

        Args:
            path (str): Secret path (e.g., "basic-secret/helloworld").
            data (dict): Secret data dictionary.
            token (str): Vault root token.
        """
        json_data = json.dumps({"data": data})
        cmd = f"curl -s --cacert {self.ca_cert_path}" f' --header "Authorization: Bearer {token}"' f" -H 'Content-Type: application/json'" f" --request POST" f" -d '{json_data}'" f" {self.VAULT_API}/v1/secret/data/{path}"
        self.ssh_connection.send(self.k8s.k8s_config.export(cmd))

    def read_secret(self, path: str, token: str, retries: int = 12, retry_delay: int = 15) -> dict:
        """Read a secret from vault using the REST API (KV v2).

        Args:
            path (str): Secret path (e.g., "basic-secret/helloworld").
            token (str): Vault root token.
            retries (int): Number of retry attempts if vault is not responding.
            retry_delay (int): Seconds to wait between retries.

        Returns:
            dict: The parsed JSON response from vault.
        """
        cmd = f"curl -s --cacert {self.ca_cert_path}" f' --header "Authorization: Bearer {token}"' f" {self.VAULT_API}/v1/secret/data/{path}"
        for attempt in range(retries):
            output = self.ssh_connection.send(self.k8s.k8s_config.export(cmd))
            response_text = "\n".join(output) if isinstance(output, list) else str(output)
            if response_text.strip():
                return json.loads(response_text)
            get_logger().log_info(f"Vault returned empty response, retrying in {retry_delay}s (attempt {attempt + 1}/{retries})")
            time.sleep(retry_delay)
        return json.loads(response_text)

    def setup_test_namespace_secrets(self) -> None:
        """Copy vault-ca and registry secrets to the pvtest namespace."""
        self.ssh_connection.send(self.k8s.k8s_config.export("kubectl create ns pvtest 2>/dev/null || true"))

        cmd = "kubectl get secrets -n vault vault-ca -o jsonpath='{.data.tls\\.crt}'" " | base64 -d > /tmp/vault_ca_tls.crt" " && kubectl create secret generic -n pvtest vault-ca-tls-crt" " --from-file=tls.crt=/tmp/vault_ca_tls.crt 2>/dev/null || true"
        self.ssh_connection.send(self.k8s.k8s_config.export(cmd))

        cmd = "kubectl get secrets -n vault default-registry-key" " -o jsonpath='{.data.\\.dockerconfigjson}'" " | base64 -d > /tmp/docker_config.json" " && kubectl create secret docker-registry -n pvtest default-registry-key" " --from-file=.dockerconfigjson=/tmp/docker_config.json 2>/dev/null || true"
        self.ssh_connection.send(self.k8s.k8s_config.export(cmd))

    def get_injected_secret(self, pod_name: str, namespace: str = "pvtest") -> dict:
        """Read the injected secret from a pod's filesystem.

        Args:
            pod_name (str): Name of the pod.
            namespace (str): Namespace of the pod.

        Returns:
            dict: The parsed JSON secret content.
        """
        output = self.kubectl_exec.run_pod_exec_cmd(pod_name, "cat /vault/secrets/helloworld", options=f"-n {namespace} -c app")
        content = "\n".join(output) if isinstance(output, list) else str(output)
        return json.loads(content)

    def get_first_pod_name(self, namespace: str = "pvtest") -> str:
        """Get the name of the first pod in a namespace.

        Args:
            namespace (str): Namespace to query.

        Returns:
            str: The pod name.
        """
        pods_output = self.kubectl_pods.get_pods(namespace)
        pods = pods_output.get_pods_with_status("Running")
        return pods[0].get_name() if pods else ""

    def delete_clusterrolebinding(self, name: str) -> None:
        """Delete a cluster role binding by name.

        Args:
            name (str): Name of the cluster role binding to delete.
        """
        self.kubectl_delete.delete_resource("clusterrolebinding", name)

    def recreate_ca_cert_file(self) -> None:
        """Re-extract the vault CA cert to the controller filesystem.

        Used after swact/reboot when the cert file may not exist on the new active.
        """
        cmd = f"kubectl get secret vault-ca -n {self.NAMESPACE}" f" -o jsonpath='{{.data.tls\\.crt}}'" f" | base64 --decode > {self.ca_cert_path}"
        self.ssh_connection.send(self.k8s.k8s_config.export(cmd))
