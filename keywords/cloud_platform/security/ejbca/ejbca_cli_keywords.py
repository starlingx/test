import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class EjbcaCliKeywords(BaseKeyword):
    """Keywords for EJBCA CLI operations via kubectl exec."""

    EJBCA_CLI_PATH = "/opt/keyfactor/bin/ejbca.sh"

    def __init__(self, ssh_connection: SSHConnection, namespace: str = "ejbca"):
        """Initialize EJBCA CLI keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
            namespace (str): Kubernetes namespace where EJBCA is deployed.
        """
        self.ssh_connection = ssh_connection
        self.namespace = namespace
        self.kubectl_exec = KubectlExecInPodsKeywords(ssh_connection)
        self.kubectl_pods = KubectlGetPodsKeywords(ssh_connection)

    def get_ejbca_pod_name(self, label: str = "app.kubernetes.io/name=ejbca") -> str:
        """Get the name of the first running EJBCA pod.

        Args:
            label (str): Label selector for EJBCA pods.

        Returns:
            str: Name of the EJBCA pod.
        """
        pods_output = self.kubectl_pods.get_pods(namespace=self.namespace, label=label)
        pod_list = pods_output.get_pods_list()
        for pod in pod_list:
            if pod.get_status() == "Running":
                return pod.get_name()
        return pod_list[0].get_name() if pod_list else ""

    def _exec_ejbca_cmd(self, subcommand: str) -> str:
        """Execute an EJBCA CLI command inside the EJBCA pod.

        Args:
            subcommand (str): EJBCA CLI subcommand.

        Returns:
            str: Command output.
        """
        pod_name = self.get_ejbca_pod_name()
        cmd = f"{self.EJBCA_CLI_PATH} {subcommand}"
        output = self.kubectl_exec.run_pod_exec_cmd(pod_name=pod_name, cmd=cmd, options=f"-n {self.namespace}")
        return output

    def list_cas(self) -> list:
        """List all Certificate Authorities in EJBCA.

        Returns:
            list: List of CA names.
        """
        output = self._exec_ejbca_cmd("ca listcas")
        ca_names = []
        for line in output.splitlines():
            stripped = line.strip()
            if stripped and "CA Name:" in stripped:
                ca_names.append(stripped.split("CA Name:")[-1].strip())
            elif stripped and not stripped.startswith("CAs:"):
                ca_names.append(stripped)
        return ca_names

    def is_ca_present(self, ca_name: str) -> bool:
        """Check if a specific CA exists.

        Args:
            ca_name (str): Name of the CA to check.

        Returns:
            bool: True if CA is present.
        """
        return ca_name in self.list_cas()

    def list_crypto_tokens(self) -> str:
        """List all crypto tokens.

        Returns:
            str: Raw output of crypto token listing.
        """
        return self._exec_ejbca_cmd("cryptotoken list")

    def is_crypto_token_active(self, token_name: str) -> bool:
        """Check if a crypto token is active.

        Args:
            token_name (str): Name of the crypto token.

        Returns:
            bool: True if token is active.
        """
        output = self.list_crypto_tokens()
        for line in output.splitlines():
            if token_name in line and "Active" in line:
                return True
        return False

    def list_crypto_token_keys(self, token_name: str) -> str:
        """List keys in a crypto token.

        Args:
            token_name (str): Name of the crypto token.

        Returns:
            str: Raw output of key listing.
        """
        return self._exec_ejbca_cmd(f"cryptotoken listkeys --token {token_name}")

    def list_roles(self) -> str:
        """List all EJBCA roles.

        Returns:
            str: Raw output of roles listing.
        """
        return self._exec_ejbca_cmd("roles listroles")

    def list_role_admins(self, role_name: str) -> str:
        """List administrators in a specific role.

        Args:
            role_name (str): Name of the role.

        Returns:
            str: Raw output of role admin listing.
        """
        return self._exec_ejbca_cmd(f'roles listadmins --role "{role_name}"')

    def find_end_entity(self, username: str) -> str:
        """Find an end entity by username.

        Args:
            username (str): Username to search for.

        Returns:
            str: Raw output of end entity search.
        """
        return self._exec_ejbca_cmd(f"ra findendentity --username {username}")

    def get_protocol_status(self) -> dict:
        """Get status of all EJBCA protocols.

        Returns:
            dict: Protocol name to status mapping.
        """
        output = self._exec_ejbca_cmd("config protocols status")
        protocols = {}
        for line in output.splitlines():
            if "=" in line:
                parts = line.split("=", 1)
                protocols[parts[0].strip()] = parts[1].strip()
        return protocols

    def is_protocol_enabled(self, protocol_name: str) -> bool:
        """Check if a specific protocol is enabled.

        Args:
            protocol_name (str): Name of the protocol.

        Returns:
            bool: True if protocol is enabled.
        """
        protocols = self.get_protocol_status()
        for name, status in protocols.items():
            if protocol_name.lower() in name.lower():
                return "enabled" in status.lower()
        return False

    def wait_for_ca_available(self, ca_name: str, timeout: int = 300) -> bool:
        """Wait for a CA to become available.

        Args:
            ca_name (str): Name of the CA to wait for.
            timeout (int): Maximum wait time in seconds.

        Returns:
            bool: True if CA became available, False on timeout.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            if self.is_ca_present(ca_name):
                get_logger().log_info(f"CA '{ca_name}' is available")
                return True
            time.sleep(10)
        get_logger().log_error(f"CA '{ca_name}' not available after {timeout}s")
        return False
