"""Keywords for OpenBao application operations."""

import base64
import json
import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords


class OpenBaoKeywords(BaseKeyword):
    """Keywords for OpenBao application operations.

    Provides methods to configure OpenBao and store/read secrets via both the
    REST API and the in-pod ``bao`` CLI, and to verify agent-injector delivery.
    """

    NAMESPACE = "openbao"
    OB_API = "https://stx-openbao-active.openbao.svc.cluster.local:8200"
    SERVER_POD_PREFIX = "stx-openbao-"
    MANAGER_LABEL = "component=openbao-manager"
    UNSEAL_CURRENT_SECRET = "openbao-unseal-current"
    CA_SECRET = "openbao-ca"
    POD_BAO_ADDR = "https://127.0.0.1:8200"
    POD_CA_CERT = "/openbao/userconfig/openbao-server-tls/ca.crt"

    def __init__(self, ssh_connection: SSHConnection, ssh_user_home: str = "/home/sysadmin"):
        """Initialize OpenBao keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
            ssh_user_home (str): Home directory of the SSH user on the lab.
        """
        self.ssh_connection = ssh_connection
        self.ssh_user_home = ssh_user_home
        self.ca_cert_path = f"{ssh_user_home}/openbao_ca.pem"
        self.k8s = K8sBaseKeyword(ssh_connection)
        self.file_keywords = FileKeywords(ssh_connection)
        self.kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
        self.kubectl_secrets = KubectlGetSecretsKeywords(ssh_connection)
        self.kubectl_exec = KubectlExecInPodsKeywords(ssh_connection)
        self.kubectl_delete = KubectlDeleteResourceKeywords(ssh_connection)
        self.kubectl_create_namespace = KubectlCreateNamespacesKeywords(ssh_connection)
        self.kubectl_create_secret = KubectlCreateSecretsKeywords(ssh_connection)

    def get_current_gen_secret_name(self) -> str:
        """Resolve the current unseal-key generation secret name.

        Reads the mutable ``openbao-unseal-current`` pointer secret, whose
        ``.data.data`` payload is ``{"current": "openbao-unseal-gen-NNN"}``.

        Returns:
            str: The current generation secret name (e.g. "openbao-unseal-gen-001").

        Raises:
            KeywordException: If the pointer secret cannot be read or parsed.
        """
        raw = self.kubectl_secrets.get_secret_with_custom_output(self.UNSEAL_CURRENT_SECRET, self.NAMESPACE, "jsonpath", "'{.data.data}'", base64=True)
        raw = raw.strip().strip("'")
        if not raw or raw.startswith("Error"):
            raise KeywordException(f"Could not read {self.UNSEAL_CURRENT_SECRET}: {raw}")
        gen_name = json.loads(raw).get("current", "")
        if not gen_name:
            raise KeywordException(f"No 'current' generation in {self.UNSEAL_CURRENT_SECRET}: {raw}")
        return gen_name

    def get_root_token(self) -> str:
        """Retrieve the OpenBao root token from the current generation secret.

        Follows the ``openbao-unseal-current`` pointer to the active immutable
        generation secret and extracts ``root_token`` from its JSON payload.

        Returns:
            str: The OpenBao root token.

        Raises:
            KeywordException: If the token cannot be read or parsed.
        """
        gen_name = self.get_current_gen_secret_name()
        raw = self.kubectl_secrets.get_secret_with_custom_output(gen_name, self.NAMESPACE, "jsonpath", "'{.data.data}'", base64=True)
        raw = raw.strip().strip("'")
        if not raw or raw.startswith("Error"):
            raise KeywordException(f"Could not read generation secret {gen_name}: {raw}")
        token = json.loads(raw).get("root_token", "")
        if not token:
            raise KeywordException(f"No root_token in generation secret {gen_name}")
        return token

    def is_server_pod(self, pod_name: str) -> bool:
        """Check if a pod name is an OpenBao server pod (not agent or manager).

        Args:
            pod_name (str): The pod name to check.

        Returns:
            bool: True if it is an OpenBao server pod.
        """
        return pod_name.startswith(self.SERVER_POD_PREFIX) and "agent" not in pod_name and "manager" not in pod_name

    def get_server_pod_name(self) -> str:
        """Get the name of the first OpenBao server pod.

        Returns:
            str: The server pod name, or an empty string if none found.
        """
        pods_output = self.kubectl_pods.get_pods(self.NAMESPACE)
        server_pods = [p.get_name() for p in pods_output.get_pods_with_status("Running") if self.is_server_pod(p.get_name())]
        return server_pods[0] if server_pods else ""

    def wait_for_unseal(self, timeout: int = 300) -> bool:
        """Wait for all OpenBao server pods to be unsealed (Running and Ready).

        Args:
            timeout (int): Maximum seconds to wait for unseal.

        Returns:
            bool: True if OpenBao is unsealed, False if timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            pods_output = self.kubectl_pods.get_pods(self.NAMESPACE)
            server_pods = [p for p in pods_output.get_pods_with_status("Running") if self.is_server_pod(p.get_name())]
            if server_pods and all(p.is_ready() for p in server_pods):
                get_logger().log_info("All OpenBao server pods are unsealed and ready")
                return True
            get_logger().log_info("OpenBao pods not all ready yet, waiting 15s...")
            time.sleep(15)
        get_logger().log_info("OpenBao unseal wait timed out")
        return False

    def _pod_bao_env(self, token: str) -> str:
        """Build the in-pod ``bao`` CLI environment with strict TLS verification.

        The server pod connects to itself over loopback; the serving cert's SAN
        includes 127.0.0.1, so TLS is verified against the mounted CA
        (``BAO_CACERT``) rather than skipped.

        Args:
            token (str): OpenBao token to authenticate with.

        Returns:
            str: The ``env`` prefix for a ``bao`` command.
        """
        return f"env HOME=/tmp BAO_ADDR={self.POD_BAO_ADDR} BAO_CACERT={self.POD_CA_CERT} BAO_TOKEN={token}"

    def run_bao(self, bao_args: str, token: str) -> str:
        """Run a ``bao`` CLI command inside the OpenBao server pod.

        The server pod has no curl, so configuration and CLI reads use the
        in-pod ``bao`` binary.

        Args:
            bao_args (str): Arguments passed to ``bao`` (e.g. "kv get secret/foo").
            token (str): OpenBao token to authenticate with.

        Returns:
            str: The command output.
        """
        pod = self.get_server_pod_name()
        env = self._pod_bao_env(token)
        output = self.kubectl_exec.run_pod_exec_cmd(pod, f"{env} bao {bao_args}", options=f"-n {self.NAMESPACE}")
        return "\n".join(output) if isinstance(output, list) else str(output)

    def run_bao_idempotent(self, bao_args: str, token: str, already_done_markers: tuple = ("already in use", "already enabled")) -> str:
        """Run a ``bao`` command tolerating 'already configured' results.

        Enabling a secrets engine or auth method is idempotent on an already
        configured OpenBao: the CLI exits non-zero with 'path is already in use'
        / 'already enabled'. Those are treated as success; any other non-zero
        output is raised.

        Args:
            bao_args (str): Arguments passed to ``bao`` (e.g. "secrets enable -path=secret kv-v2").
            token (str): OpenBao token to authenticate with.
            already_done_markers (tuple): Output substrings that mean the operation was already applied.

        Returns:
            str: The command output.

        Raises:
            KeywordException: If the command fails for a reason other than being already applied.
        """
        pod = self.get_server_pod_name()
        env = self._pod_bao_env(token)
        output = self.kubectl_exec.run_pod_exec_cmd(pod, f"{env} bao {bao_args}", options=f"-n {self.NAMESPACE}", ignore_error=True)
        text = "\n".join(output) if isinstance(output, list) else str(output)
        rc = self.ssh_connection.get_return_code()
        if rc != 0 and not any(marker in text for marker in already_done_markers):
            raise KeywordException(f"bao {bao_args} failed (rc={rc}): {text}")
        return text

    def enable_kv_v2(self, token: str) -> None:
        """Enable the KV v2 secrets engine at ``secret/`` (idempotent).

        Args:
            token (str): OpenBao root token.
        """
        self.run_bao_idempotent("secrets enable -path=secret kv-v2", token)

    def enable_kubernetes_auth(self, token: str) -> None:
        """Enable the kubernetes auth method (idempotent).

        Args:
            token (str): OpenBao root token.
        """
        self.run_bao_idempotent("auth enable kubernetes", token)

    def configure_kubernetes_auth(self, token: str) -> None:
        """Configure the kubernetes auth method with the in-cluster API host.

        Writes ``auth/kubernetes/config`` so the method can validate
        ServiceAccount JWTs via TokenReview. Without this, kubernetes/login
        returns "could not load backend configuration".

        Args:
            token (str): OpenBao root token.
        """
        self.run_bao("write auth/kubernetes/config kubernetes_host=https://kubernetes.default.svc.cluster.local", token)

    def write_policy(self, policy_name: str, policy_hcl: str, token: str) -> None:
        """Write an OpenBao policy from an HCL string.

        The HCL is base64-encoded on the controller and decoded to a file inside
        the pod before ``bao policy write`` reads it, so quotes and special
        characters in the policy survive without nested-shell quoting issues.

        Args:
            policy_name (str): Name of the policy.
            policy_hcl (str): HCL policy body.
            token (str): OpenBao root token.
        """
        pod = self.get_server_pod_name()
        env = self._pod_bao_env(token)
        encoded = base64.b64encode(policy_hcl.encode()).decode()
        remote_file = f"/tmp/{policy_name}.hcl"
        cmd = f"sh -c 'echo {encoded} | base64 -d > {remote_file} && {env} bao policy write {policy_name} {remote_file}'"
        self.kubectl_exec.run_pod_exec_cmd(pod, cmd, options=f"-n {self.NAMESPACE}")

    def write_kubernetes_role(self, role_name: str, service_account: str, namespace: str, policy_name: str, token: str, ttl: str = "24h") -> None:
        """Bind a kubernetes service account to an OpenBao policy via a role.

        Args:
            role_name (str): Name of the kubernetes auth role.
            service_account (str): Bound service account name.
            namespace (str): Bound service account namespace.
            policy_name (str): Policy to attach to the role.
            token (str): OpenBao root token.
            ttl (str): Token TTL for the role. Defaults to "24h".
        """
        bao_args = f"write auth/kubernetes/role/{role_name} bound_service_account_names={service_account} bound_service_account_namespaces={namespace} policies={policy_name} ttl={ttl}"
        self.run_bao(bao_args, token)

    def create_secret_rest(self, path: str, data: dict, token: str) -> None:
        """Create a secret via the OpenBao REST API (KV v2).

        Uses the OpenBao CA for TLS verification (no insecure flag).

        Args:
            path (str): Secret path (e.g., "basic-secret/helloworld").
            data (dict): Secret data dictionary.
            token (str): OpenBao token.
        """
        json_data = json.dumps({"data": data})
        cmd = f"curl -s --cacert {self.ca_cert_path} --header 'X-Vault-Token: {token}' -H 'Content-Type: application/json' --request POST -d '{json_data}' {self.OB_API}/v1/secret/data/{path}"
        self.ssh_connection.send(self.k8s.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def read_secret_rest(self, path: str, token: str, retries: int = 12, retry_delay: int = 15) -> dict:
        """Read a secret via the OpenBao REST API (KV v2).

        Args:
            path (str): Secret path (e.g., "basic-secret/helloworld").
            token (str): OpenBao token.
            retries (int): Number of retry attempts if OpenBao is not responding.
            retry_delay (int): Seconds to wait between retries.

        Returns:
            dict: The parsed JSON response from OpenBao.
        """
        cmd = f"curl -s --cacert {self.ca_cert_path} --header 'X-Vault-Token: {token}' {self.OB_API}/v1/secret/data/{path}"
        response_text = ""
        for attempt in range(retries):
            output = self.ssh_connection.send(self.k8s.k8s_config.export(cmd))
            response_text = "\n".join(output) if isinstance(output, list) else str(output)
            if response_text.strip():
                return json.loads(response_text)
            get_logger().log_info(f"OpenBao returned empty response, retrying in {retry_delay}s (attempt {attempt + 1}/{retries})")
            time.sleep(retry_delay)
        return json.loads(response_text)

    def create_secret_cli(self, path: str, data: dict, token: str) -> None:
        """Create a secret via the in-pod ``bao`` CLI (KV v2).

        Args:
            path (str): Secret path under the KV mount (e.g., "basic-secret/helloworld").
            data (dict): Secret key/value pairs.
            token (str): OpenBao token.
        """
        kv_pairs = " ".join(f"{key}={value}" for key, value in data.items())
        self.run_bao(f"kv put secret/{path} {kv_pairs}", token)

    def read_secret_cli(self, path: str, token: str) -> str:
        """Read a secret via the in-pod ``bao`` CLI (KV v2).

        Args:
            path (str): Secret path under the KV mount.
            token (str): OpenBao token.

        Returns:
            str: The ``bao kv get`` command output.
        """
        return self.run_bao(f"kv get secret/{path}", token)

    def login_token_and_read(self, path: str, token: str) -> str:
        """Authenticate with ``bao login`` (token method) then read a KV v2 secret.

        Exercises the ``bao login`` codepath non-interactively (``-no-store``),
        distinct from the BAO_TOKEN-in-env path used by read_secret_cli.

        Args:
            path (str): Secret path under the KV mount.
            token (str): OpenBao root token to log in with.

        Returns:
            str: The ``bao kv get`` output after an explicit login.
        """
        self.run_bao(f"login -no-store -method=token token={token}", token)
        return self.run_bao(f"kv get secret/{path}", token)

    def extract_ca_cert(self) -> None:
        """Extract the OpenBao CA certificate to the controller filesystem.

        Reads the CA via the secret keyword and writes it to ``openbao_ca.pem``
        so REST clients can verify TLS.
        """
        ca_pem = self.kubectl_secrets.get_secret_with_custom_output(self.CA_SECRET, self.NAMESPACE, "jsonpath", "'{.data.tls\\.crt}'", base64=True)
        self.file_keywords.create_file_with_echo(self.ca_cert_path, ca_pem.strip().strip("'"))

    def setup_test_namespace_secrets(self, test_namespace: str = "pvtest") -> None:
        """Copy OpenBao CA and registry secrets into the test namespace.

        Args:
            test_namespace (str): Namespace used by the injector test app. Defaults to "pvtest".
        """
        self.kubectl_create_namespace.create_namespace_if_absent(test_namespace)
        self.kubectl_create_secret.copy_secret_between_namespaces(self.CA_SECRET, self.NAMESPACE, test_namespace)
        self.kubectl_create_secret.copy_secret_between_namespaces("default-registry-key", self.NAMESPACE, test_namespace)

    def get_injected_secret(self, pod_name: str, namespace: str = "pvtest") -> dict:
        """Read the injected secret from a test pod's filesystem.

        The agent injector writes the rendered secret to ``/vault/secrets/helloworld``.

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
        """Get the name of the first Running pod in a namespace.

        Args:
            namespace (str): Namespace to query.

        Returns:
            str: The pod name, or an empty string if none found.
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
