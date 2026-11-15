"""Keywords for OpenBao application operations."""

import base64
import json
import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.linux.systemctl.systemctl_is_active_keywords import SystemCTLIsActiveKeywords
from keywords.linux.systemctl.systemctl_status_keywords import SystemCTLStatusKeywords


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
    HOST_SERVICE_NAME = "openbao"
    HOST_HCL_PATH = "/etc/openbao/stx_openbao_configs.hcl"
    HOST_CERT_PATH = "/etc/openbao/certs/openbao-cert.crt"
    HOST_CA_ANCHORS_DIR = "/etc/pki/ca-trust/source/anchors"
    APP_NAME = "openbao"
    CHART_PATH = "/usr/local/share/applications/helm/openbao-[0-9]*"
    TEST_NAMESPACE = "pvtest"
    POLICY_NAME = "basic-secret-policy"
    ROLE_NAME = "basic-secret-role"
    SERVICE_ACCOUNT = "basic-secret"
    POLICY_HCL = 'path "secret/data/basic-secret/*" { capabilities = ["read"] }'
    HOST_BAO_ADDR = "https://[::1]:8200"
    HOST_ADMIN_PW_FILE = "/var/luks/stx/luks_fs/controller/.openbao/users/admin/pw"
    HOST_LUKS_KEY_PATH = "/var/luks/stx/luks_fs/controller/.openbao/auto-unseal/stx-initial.key"

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
        self.kubectl_pvc = KubectlGetPvcKeywords(ssh_connection)
        self.kubectl_resource = KubectlGetResourceKeywords(ssh_connection)

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

    def get_server_pod_names(self) -> list[str]:
        """Get the names of all running OpenBao server pods.

        Returns:
            list[str]: Names of all Running stx-openbao server pods (excludes the
                agent-injector and manager pods).
        """
        pods_output = self.kubectl_pods.get_pods(self.NAMESPACE)
        return [p.get_name() for p in pods_output.get_pods_with_status("Running") if self.is_server_pod(p.get_name())]

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
        if not response_text.strip():
            get_logger().log_info(f"OpenBao returned an empty response for {path} after {retries} attempts")
            return {}
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

    def get_seal_status(self, token: str) -> dict:
        """Get the OpenBao seal-status as a parsed dict.

        Reads ``bao status -format=json`` which reports the Shamir
        configuration (``total_shares`` / ``threshold``) and seal state.

        Args:
            token (str): OpenBao token to authenticate with.

        Returns:
            dict: The decoded status JSON (keys include ``total_shares``,
                ``threshold``, ``sealed``, ``initialized``).
        """
        raw = self.run_bao("status -format=json", token)
        return json.loads(raw)

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

    def get_openbao_pvc_names(self) -> list[str]:
        """Get the names of all PVCs in the OpenBao namespace.

        Returns:
            list[str]: PVC names bound in the OpenBao namespace (empty if none).
        """
        pvcs = self.kubectl_pvc.get_pvc(namespace=self.NAMESPACE).get_pvcs()
        return [pvc.get_name() for pvc in pvcs]

    def is_gen_secret_immutable(self, gen_secret_name: str) -> bool:
        """Check whether an unseal-key generation secret is immutable.

        Args:
            gen_secret_name (str): Name of the generation secret (e.g. "openbao-unseal-gen-001").

        Returns:
            bool: True if the secret's ``immutable`` field is true.
        """
        raw = self.kubectl_secrets.get_secret_with_custom_output(gen_secret_name, self.NAMESPACE, "jsonpath", "'{.immutable}'")
        return raw.strip().strip("'") == "true"

    def get_gen_secret_keys(self, gen_secret_name: str) -> list[str]:
        """Get the inner data keys stored in an unseal-key generation secret.

        Args:
            gen_secret_name (str): Name of the generation secret (e.g. "openbao-unseal-gen-001").

        Returns:
            list[str]: The keys present in the secret's decoded ``.data.data`` payload
                (e.g. "keys", "keys_base64", "root_token").
        """
        raw = self.kubectl_secrets.get_secret_with_custom_output(gen_secret_name, self.NAMESPACE, "jsonpath", "'{.data.data}'", base64=True)
        return list(json.loads(raw.strip().strip("'")).keys())

    def get_statefulset_template_label(self, label_key: str) -> str:
        """Get a pod-template label value from the stx-openbao StatefulSet.

        Args:
            label_key (str): The pod-template label key (e.g. "pv").

        Returns:
            str: The label value from ``.spec.template.metadata.labels``, or empty if unset.
        """
        return self.kubectl_resource.get_resource_field("statefulset", "stx-openbao", f"{{.spec.template.metadata.labels.{label_key}}}", self.NAMESPACE)

    def get_namespace_psa_enforce(self, namespace: str) -> str:
        """Get the PodSecurity 'enforce' level label of a namespace.

        Args:
            namespace (str): Namespace to query.

        Returns:
            str: The pod-security.kubernetes.io/enforce label value (e.g. "privileged"), or empty if unset.
        """
        return self.kubectl_resource.get_resource_field("namespace", namespace, "{.metadata.labels.pod-security\\.kubernetes\\.io/enforce}")

    def get_namespace_psa_level(self, namespace: str, level: str) -> str:
        """Get a PodSecurity level label (enforce/warn/audit) of a namespace.

        Args:
            namespace (str): Namespace to query.
            level (str): PodSecurity mode - one of "enforce", "warn", "audit".

        Returns:
            str: The pod-security.kubernetes.io/<level> label value, or empty if unset.
        """
        return self.kubectl_resource.get_resource_field("namespace", namespace, f"{{.metadata.labels.pod-security\\.kubernetes\\.io/{level}}}")

    def dry_run_privileged_pod(self, namespace: str) -> str:
        """Server-side dry-run a privileged pod in a namespace to probe PodSecurity admission.

        No real pod is created. An 'enforce=privileged' namespace admits the request; an
        'enforce=restricted' namespace rejects it with a 'violates PodSecurity' message. The
        call does not assert on the return code so the caller can validate either outcome.

        Args:
            namespace (str): Namespace to probe.

        Returns:
            str: The API server response (admission confirmation or violation message).
        """
        overrides = '{"spec":{"containers":[{"name":"psa-probe","image":"registry.k8s.io/pause:3.9","securityContext":{"privileged":true}}]}}'
        cmd = f"kubectl run psa-probe --image=registry.k8s.io/pause:3.9 -n {namespace} --restart=Never --dry-run=server --overrides='{overrides}'"
        output = self.ssh_connection.send(self.k8s.k8s_config.export(cmd))
        return "\n".join(output) if isinstance(output, list) else str(output)

    def is_manager_pod_present(self) -> bool:
        """Check whether an OpenBao manager pod exists in the namespace.

        Returns:
            bool: True if a pod matching the manager label is present.
        """
        pods = self.kubectl_pods.get_pods(self.NAMESPACE).get_pods()
        return any("manager" in pod.get_name() for pod in pods)

    def wait_for_server_sealed(self, timeout: int = 300) -> bool:
        """Wait for an OpenBao server pod to be present but sealed (Running, not Ready).

        A sealed server pod runs but fails its readiness probe, so it stays 0/1 Ready.

        Args:
            timeout (int): Maximum seconds to wait for the sealed state.

        Returns:
            bool: True if a server pod is present and not Ready (sealed), False if timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            server_pods = [p for p in self.kubectl_pods.get_pods(self.NAMESPACE).get_pods() if self.is_server_pod(p.get_name())]
            if server_pods and not any(p.is_ready() for p in server_pods):
                get_logger().log_info("OpenBao server pod is present but sealed (not Ready)")
                return True
            get_logger().log_info("OpenBao server not yet in the sealed state, waiting 15s...")
            time.sleep(15)
        get_logger().log_info("OpenBao sealed-state wait timed out")
        return False

    def is_host_service_active(self, ssh_connection: SSHConnection = None) -> bool:
        """Check whether the host OpenBao systemd service is active.

        Args:
            ssh_connection (SSHConnection): Target host SSH; defaults to the
                connection this keyword was constructed with (active controller).

        Returns:
            bool: True if ``systemctl is-active openbao`` reports active.
        """
        target = ssh_connection if ssh_connection is not None else self.ssh_connection
        return SystemCTLIsActiveKeywords(target).is_active(self.HOST_SERVICE_NAME) == "active"

    def is_host_service_enabled(self, ssh_connection: SSHConnection = None) -> bool:
        """Check whether the host OpenBao systemd service is enabled at boot.

        The enabled state is read from the ``Loaded:`` line of ``systemctl
        status`` so no additional command is required.

        Args:
            ssh_connection (SSHConnection): Target host SSH; defaults to the
                connection this keyword was constructed with (active controller).

        Returns:
            bool: True if the unit is reported as enabled.
        """
        target = ssh_connection if ssh_connection is not None else self.ssh_connection
        status_lines = SystemCTLStatusKeywords(target).get_status(self.HOST_SERVICE_NAME)
        for line in status_lines:
            if "Loaded:" in line and "enabled" in line:
                return True
        return False

    def is_host_service_enabled_on_all_controllers(self) -> bool:
        """Check the host OpenBao service is enabled on every controller.

        Works on SX (one controller), DX and Standard (two controllers): the
        service is preset-enabled on all controllers so it persists reboot.

        Returns:
            bool: True if the service is enabled on all controllers.
        """
        lab_connection = LabConnectionKeywords()
        controllers = SystemHostListKeywords(self.ssh_connection).get_controllers()
        for controller in controllers:
            host_ssh = lab_connection.get_ssh_for_hostname(controller.get_host_name())
            if not self.is_host_service_enabled(host_ssh):
                get_logger().log_info(f"Host OpenBao service not enabled on {controller.get_host_name()}")
                return False
        return True

    def is_host_service_disabled_on_non_controllers(self) -> bool:
        """Check the host OpenBao service is NOT enabled on workers/storage.

        The host service runs on controllers only. Hosts are enumerated from
        the full host list and filtered by personality, so a system with no
        worker or storage nodes (such as SX) has nothing to check and returns
        True without error.

        Returns:
            bool: True if no non-controller node has the service enabled.
        """
        lab_connection = LabConnectionKeywords()
        all_hosts = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_hosts()
        non_controllers = [host for host in all_hosts if "controller" not in host.get_personality()]
        for host in non_controllers:
            host_ssh = lab_connection.get_ssh_for_hostname(host.get_host_name())
            if self.is_host_service_enabled(host_ssh):
                get_logger().log_info(f"Host OpenBao service unexpectedly enabled on {host.get_host_name()}")
                return False
        return True

    def validate_host_hcl_config(self) -> bool:
        """Validate the host OpenBao HCL config with ``bao operator validate-config``.

        Returns:
            bool: True if the validator reports a successful config.
        """
        output = self.ssh_connection.send_as_sudo(f"/usr/bin/bao operator validate-config -config {self.HOST_HCL_PATH}")
        joined = " ".join(output)
        return "success" in joined.lower()

    def get_host_hcl_content(self) -> str:
        """Read the host OpenBao HCL config file contents.

        Returns:
            str: The HCL file content as a single string.
        """
        return "".join(FileKeywords(self.ssh_connection).read_file_with_sudo(self.HOST_HCL_PATH))

    def _host_bao(self, bao_args: str, token: str = None) -> str:
        """Run a host ``bao`` command over sudo with strict TLS.

        Args:
            bao_args (str): Arguments passed to the ``bao`` CLI.
            token (str): Optional BAO_TOKEN to authenticate the call.

        Returns:
            str: The joined command output.
        """
        env = f"BAO_ADDR={self.HOST_BAO_ADDR} BAO_CACERT={self.HOST_CERT_PATH}"
        if token:
            env += f" BAO_TOKEN={token}"
        output = self.ssh_connection.send_as_sudo_non_interactive(f"env {env} /usr/bin/bao {bao_args}")
        return "".join(output)

    def host_bao_admin_login(self) -> str:
        """Log in to the host OpenBao as admin using the encrypted-filesystem password.

        Returns:
            str: The client token returned by the userpass login (empty on failure).
        """
        output = self._host_bao(f"login -field=token -no-store -method=userpass username=admin password=@{self.HOST_ADMIN_PW_FILE}")
        return output.strip()

    def host_bao_auth_methods(self, token: str) -> str:
        """List the host OpenBao auth methods.

        Args:
            token (str): BAO_TOKEN to authenticate the call.

        Returns:
            str: The ``bao auth list`` output.
        """
        return self._host_bao("auth list", token)

    def host_bao_secret_mounts(self, token: str) -> str:
        """List the host OpenBao secret engine mounts.

        Args:
            token (str): BAO_TOKEN to authenticate the call.

        Returns:
            str: The ``bao secrets list`` output.
        """
        return self._host_bao("secrets list", token)

    def host_bao_policies(self, token: str) -> str:
        """List the host OpenBao policies.

        Args:
            token (str): BAO_TOKEN to authenticate the call.

        Returns:
            str: The ``bao policy list`` output.
        """
        return self._host_bao("policy list", token)

    def host_bao_kv_put(self, path: str, kv_pairs: dict, token: str) -> str:
        """Write a KV v2 secret to the host OpenBao (mount ``secret``).

        Args:
            path (str): Secret path under the ``secret`` mount.
            kv_pairs (dict): Key/value pairs to store.
            token (str): BAO_TOKEN to authenticate the call.

        Returns:
            str: The ``bao kv put`` command output.
        """
        pairs = " ".join(f"{key}={value}" for key, value in kv_pairs.items())
        return self._host_bao(f"kv put -mount=secret {path} {pairs}", token)

    def host_bao_kv_get(self, path: str, token: str) -> str:
        """Read a KV v2 secret from the host OpenBao (mount ``secret``).

        Args:
            path (str): Secret path under the ``secret`` mount.
            token (str): BAO_TOKEN to authenticate the call.

        Returns:
            str: The ``bao kv get`` command output.
        """
        return self._host_bao(f"kv get -mount=secret {path}", token)

    def host_raft_list_peers(self, token: str) -> str:
        """List the host OpenBao raft peers.

        Args:
            token (str): BAO_TOKEN to authenticate the call.

        Returns:
            str: The ``bao operator raft list-peers`` output.
        """
        return self._host_bao("operator raft list-peers", token)

    def host_puppet_runtime_reapply(self) -> str:
        """Trigger a puppet runtime re-apply of the host OpenBao class.

        Re-runs the ``platform::openbao::runtime`` class so the service re-reads
        its configuration without a restart or re-seal (no sysinv path exists).

        Returns:
            str: The ``puppet apply`` command output.
        """
        manifest = "include ::platform::openbao::runtime"
        modulepath = "/usr/share/puppet/modules:/usr/share/openstack-puppet/modules"
        cmd = f"bash -c \"echo '{manifest}' | puppet apply --modulepath={modulepath} 2>&1\""
        return "".join(self.ssh_connection.send_as_sudo_non_interactive(cmd))

    def get_host_file_owner_mode(self, path: str) -> str:
        """Get ``owner:group mode`` for a host file via sudo stat.

        Args:
            path (str): Absolute path to the file.

        Returns:
            str: A string of the form ``"openbao:openbao 640"`` (empty on error).
        """
        output = self.ssh_connection.send_as_sudo_non_interactive(f"stat -c '%U:%G %a' {path}")
        return "".join(output).strip()

    def sysadmin_can_read(self, path: str) -> bool:
        """Check whether the non-privileged SSH user can read a file.

        Reads the file without sudo and treats a permission error as "cannot
        read". Used to confirm that service-owned secrets are not world or
        sysadmin readable.

        Args:
            path (str): Absolute path to the file.

        Returns:
            bool: True if the file content is readable without sudo.
        """
        output = "".join(self.ssh_connection.send(f"cat {path} 2>&1"))
        return "Permission denied" not in output and "No such file" not in output

    def host_bao_status_with_ca(self) -> str:
        """Query host ``bao status`` over TLS trusting the server CA cert.

        Returns:
            str: The ``bao status`` output (includes the seal state when the
            TLS handshake succeeds).
        """
        return self._host_bao("status")

    def host_server_cert_verifies(self) -> bool:
        """Check the host OpenBao server certificate verifies against the system CA.

        Runs ``openssl verify`` of the server leaf certificate against the
        platform trust-anchor directory (``-CApath``) so verification succeeds
        regardless of which anchor CA issued the cert, and checks for the
        authoritative ``: OK`` verdict (not the per-depth ``verify return``
        callback lines).

        Returns:
            bool: True if openssl reports the leaf verifies against a trusted CA.
        """
        cmd = f'bash -c "openssl verify -CApath {self.HOST_CA_ANCHORS_DIR} {self.HOST_CERT_PATH} 2>&1"'
        output = "".join(self.ssh_connection.send_as_sudo_non_interactive(cmd))
        return f"{self.HOST_CERT_PATH}: OK" in output

    def is_host_server_cert_ca_issued(self) -> bool:
        """Check the host OpenBao server certificate is CA-issued (not self-signed).

        A CA-issued certificate has an issuer distinct from its subject; a
        self-signed certificate has issuer == subject. The specific issuing CA
        CN is lab-dependent (system-local-ca on standard labs, a custom
        intermediate CA on others), so CA-issuance is asserted by issuer !=
        subject rather than a fixed CN. Trust against the platform anchors is
        covered separately by host_server_cert_verifies.

        Returns:
            bool: True if the cert has a non-empty issuer that differs from its subject.
        """
        cmd = f"openssl x509 -in {self.HOST_CERT_PATH} -noout -issuer -subject"
        output = "".join(self.ssh_connection.send_as_sudo_non_interactive(cmd))
        lines = output.splitlines()
        issuer = next((line[len("issuer=") :].strip() for line in lines if line.startswith("issuer=")), "")
        subject = next((line[len("subject=") :].strip() for line in lines if line.startswith("subject=")), "")
        return bool(issuer) and issuer != subject

    def rest_status_code(self, path: str, token: str = None, use_ca: bool = True) -> str:
        """Return the HTTP status code of a REST GET against a secret path.

        Args:
            path (str): Secret path under ``v1/secret/data/``.
            token (str): Optional X-Vault-Token header value.
            use_ca (bool): Trust the OpenBao CA (True) or omit it (False).

        Returns:
            str: The numeric HTTP status code as a string (e.g., "200").
        """
        cacert = f"--cacert {self.ca_cert_path}" if use_ca else ""
        header = f"--header 'X-Vault-Token: {token}'" if token is not None else ""
        cmd = f"curl -s -o /dev/null -w '%{{http_code}}' {cacert} {header} {self.OB_API}/v1/secret/data/{path}"
        output = self.ssh_connection.send(self.k8s.k8s_config.export(cmd))
        return "".join(output).strip()

    def rest_health_trusts_ca(self) -> bool:
        """Check the server health endpoint is reachable over TLS trusting the CA.

        Returns:
            bool: True if the health endpoint returns an initialized/unsealed body.
        """
        cmd = f"curl -s --cacert {self.ca_cert_path} {self.OB_API}/v1/sys/health"
        output = "".join(self.ssh_connection.send(self.k8s.k8s_config.export(cmd)))
        return '"initialized":true' in output and '"sealed":false' in output

    def rest_health_no_ca_rejected(self) -> bool:
        """Check the server health endpoint is rejected without a trusted CA.

        The app server certificate is issued by the OpenBao CA, which the
        system trust store does not contain, so a request without ``--cacert``
        must fail the TLS handshake.

        Returns:
            bool: True if curl reports a TLS/certificate verification failure.
        """
        cmd = f"curl -s --show-error {self.OB_API}/v1/sys/health 2>&1"
        output = "".join(self.ssh_connection.send(self.k8s.k8s_config.export(cmd)))
        return "certificate" in output.lower() or "SSL" in output or "unable to get local issuer" in output

    def app_server_cert_verifies(self) -> bool:
        """Verify the app server certificate against the OpenBao CA via openssl.

        Returns:
            bool: True if openssl reports the server cert verifies against the CA.
        """
        server_pem = f"{self.ssh_user_home}/openbao_server.pem"
        extract = f"kubectl get secret -n {self.NAMESPACE} openbao-server-tls -o jsonpath='{{.data.tls\\.crt}}' | base64 -d > {server_pem}"
        self.ssh_connection.send(self.k8s.k8s_config.export(extract))
        verify = f"openssl verify -CAfile {self.ca_cert_path} {server_pem} 2>&1"
        output = "".join(self.ssh_connection.send(verify))
        return f"{server_pem}: OK" in output

    def k8s_role_login_token(self, role_name: str, service_account: str, namespace: str) -> str:
        """Log in via the kubernetes auth method and return the scoped client token.

        Mints a service-account JWT and exchanges it at the kubernetes auth
        login endpoint for a policy-scoped client token.

        Args:
            role_name (str): Kubernetes auth role to authenticate as.
            service_account (str): Service account whose JWT is minted.
            namespace (str): Namespace of the service account.

        Returns:
            str: The scoped client token (empty string on failure).
        """
        jwt_cmd = f"kubectl create token {service_account} -n {namespace}"
        jwt = "".join(self.ssh_connection.send(self.k8s.k8s_config.export(jwt_cmd))).strip()
        login = f"curl -s --cacert {self.ca_cert_path} --request POST " f'--data \'{{"role":"{role_name}","jwt":"{jwt}"}}\' ' f"{self.OB_API}/v1/auth/kubernetes/login"
        output = "".join(self.ssh_connection.send(self.k8s.k8s_config.export(login)))
        try:
            return json.loads(output).get("auth", {}).get("client_token", "")
        except (ValueError, AttributeError):
            return ""

    def rest_write_status_code(self, path: str, token: str) -> str:
        """Return the HTTP status code of a REST write to a secret path.

        Args:
            path (str): Secret path under ``v1/secret/data/``.
            token (str): X-Vault-Token header value.

        Returns:
            str: The numeric HTTP status code as a string.
        """
        cmd = f"curl -s -o /dev/null -w '%{{http_code}}' --cacert {self.ca_cert_path} " f"--header 'X-Vault-Token: {token}' --request POST " f'-d \'{{"data":{{"k":"x"}}}}\' {self.OB_API}/v1/secret/data/{path}'
        output = self.ssh_connection.send(self.k8s.k8s_config.export(cmd))
        return "".join(output).strip()

    def enable_audit_device(self, name: str, file_path: str, token: str) -> None:
        """Enable a file audit device (idempotent: tolerates already-enabled).

        Args:
            name (str): Audit device name (mount path).
            file_path (str): File path the device writes to (or "stdout").
            token (str): OpenBao root token.
        """
        data = f'{{"type":"file","options":{{"file_path":"{file_path}"}}}}'
        cmd = f"curl -s --cacert {self.ca_cert_path} --header 'X-Vault-Token: {token}' " f"--request POST --data '{data}' {self.OB_API}/v1/sys/audit/{name}"
        self.ssh_connection.send(self.k8s.k8s_config.export(cmd))

    def disable_audit_device(self, name: str, token: str) -> None:
        """Disable an audit device (idempotent: tolerates absent).

        Args:
            name (str): Audit device name (mount path).
            token (str): OpenBao root token.
        """
        cmd = f"curl -s --cacert {self.ca_cert_path} --header 'X-Vault-Token: {token}' " f"--request DELETE {self.OB_API}/v1/sys/audit/{name}"
        self.ssh_connection.send(self.k8s.k8s_config.export(cmd))

    def list_audit_devices(self, token: str) -> str:
        """List the enabled audit devices.

        Args:
            token (str): OpenBao root token.

        Returns:
            str: The raw JSON listing of audit devices.
        """
        cmd = f"curl -s --cacert {self.ca_cert_path} --header 'X-Vault-Token: {token}' {self.OB_API}/v1/sys/audit"
        return "".join(self.ssh_connection.send(self.k8s.k8s_config.export(cmd)))

    def read_pod_audit_log(self, audit_file: str, grep_token: str) -> str:
        """Read the in-pod audit log and return the last line matching a token.

        Args:
            audit_file (str): Audit log path inside the server pod.
            grep_token (str): Substring to match (e.g., a secret path).

        Returns:
            str: The matching audit log line (empty if none).
        """
        pod = self.get_server_pod_name()
        cmd = f"sh -c 'grep \"{grep_token}\" {audit_file} | tail -1'"
        output = self.kubectl_exec.run_pod_exec_cmd(pod, cmd, options=f"-n {self.NAMESPACE}")
        return "".join(output) if isinstance(output, list) else str(output)

    def patch_gen_secret_rejected(self, gen_secret_name: str) -> bool:
        """Attempt to patch the immutable generation secret and confirm rejection.

        Args:
            gen_secret_name (str): Name of the unseal generation secret.

        Returns:
            bool: True if the patch is rejected because the secret is immutable.
        """
        cmd = f'kubectl patch secret -n {self.NAMESPACE} {gen_secret_name} -p \'{{"data":{{"x":"eA=="}}}}\' 2>&1'
        output = "".join(self.ssh_connection.send(self.k8s.k8s_config.export(cmd)))
        return "immutable" in output.lower()

    def ensure_rbac_test_subject(self, namespace: str, service_account: str) -> None:
        """Idempotently ensure the RBAC test namespace and service account exist.

        Creates the namespace and the bound service account, tolerating the
        already-exists state so the method is safe to call repeatedly.

        Args:
            namespace (str): Namespace to hold the service account.
            service_account (str): Service account bound to the OpenBao role.
        """
        self.kubectl_create_namespace.create_namespace_if_absent(namespace)
        cmd = f"kubectl create serviceaccount {service_account} -n {namespace} --dry-run=client -o yaml | kubectl apply -f -"
        self.ssh_connection.send(self.k8s.k8s_config.export(cmd))
