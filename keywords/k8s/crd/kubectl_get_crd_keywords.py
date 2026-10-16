"""Keywords for listing Kubernetes Custom Resource Definitions (CRDs)."""

import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.crd.object.kubectl_get_crd_output import KubectlGetCrdOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetCrdKeywords(K8sBaseKeyword):
    """Keywords for listing Kubernetes Custom Resource Definitions (CRDs)."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize KubectlGetCrdKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_crds(self) -> KubectlGetCrdOutput:
        """Get the list of registered CRDs.

        Returns:
            KubectlGetCrdOutput: Parsed output containing all CRD objects.
        """
        cmd = "kubectl get crd"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetCrdOutput(output)

    def get_crds_with_retry(self, attempts: int = 8, interval: int = 15) -> KubectlGetCrdOutput:
        """Get the registered CRDs, retrying through a transient apiserver outage.

        An upgrade activate, controller swact or host reboot briefly restarts the kube-apiserver,
        so a read that lands in that window returns "connection refused" / "couldn't get current
        server API group list" (or raises when the rc check fails). This retries the read for a
        bounded window and only returns once a usable (non-apiserver-down) response is parsed, so a
        one-shot CRD-presence check is not flaked by that blip. Generic: usable by any caller that
        reads CRDs shortly after a disruptive platform operation.

        Args:
            attempts (int): how many times to try before giving up.
            interval (int): seconds between attempts.

        Returns:
            KubectlGetCrdOutput: the parsed CRD list. Empty (no CRDs parsed) if the apiserver never
                became readable within the window - the caller distinguishes that from "CRDs
                missing" as it sees fit.
        """
        apiserver_down_markers = ("connection refused", "server API group list",
                                  "was refused", "Unable to connect to the server")
        last_output = []
        for attempt in range(attempts):
            try:
                output = self.ssh_connection.send(self.k8s_config.export("kubectl get crd"))
            except Exception as e:  # noqa: BLE001 - transient apiserver blip, retried below
                get_logger().log_info(f"kubectl get crd raised, retrying ({attempt + 1}/{attempts}): {e}")
                time.sleep(interval)
                continue
            lines = [line.strip() for line in (output or []) if line.strip()]
            joined = " ".join(lines)
            if lines and not any(marker in joined for marker in apiserver_down_markers):
                return KubectlGetCrdOutput(output)
            last_output = output
            get_logger().log_info(f"kubectl get crd empty/apiserver-unavailable, retrying ({attempt + 1}/{attempts})")
            time.sleep(interval)
        return KubectlGetCrdOutput(last_output or [])

    def get_crd(self, crd_name: str) -> KubectlGetCrdOutput:
        """Get a single CRD with full details including status conditions.

        Args:
            crd_name (str): Full CRD name (e.g. 'prometheuses.monitoring.coreos.com').

        Returns:
            KubectlGetCrdOutput: Parsed output containing the CRD object with status.
        """
        cmd = f"kubectl get crd {crd_name} -o json"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetCrdOutput(output, source="json")

