"""Keywords for driving the kube-cert-rotation.sh K8s certificate renewal script.

Encapsulates the host-level operations used to test /usr/bin/kube-cert-rotation.sh:
running the script, reading the live apiserver certificate's Subject Alternative
Names, and restarting the kube-apiserver static pod and waiting for it to recover.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

ROTATION_SCRIPT = "/usr/bin/kube-cert-rotation.sh"
APISERVER_CERT = "/etc/kubernetes/pki/apiserver.crt"
K8S_CA_CERT = "/etc/kubernetes/pki/ca.crt"
K8S_CA_KEY = "/etc/kubernetes/pki/ca.key"


class KubeCertRotationKeywords(BaseKeyword):
    """Keywords for the kube-cert-rotation.sh script and apiserver certificate handling."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Active controller SSH connection.
        """
        self.ssh_connection = ssh_connection

    def copy_k8s_ca_readable(self, dest_cert: str, dest_key: str) -> None:
        """Copy the K8s Root CA cert and key to readable destination paths.

        The K8s Root CA under /etc/kubernetes/pki is root-only, so a non-sudo
        openssl signing operation cannot read it. This copies the CA cert and key
        (with sudo) to the given destinations and makes them world-readable so a
        subsequent openssl signing step can use them. The destinations contain the
        CA private key and must be deleted by the caller on teardown.

        Args:
            dest_cert (str): Destination path for the CA certificate copy.
            dest_key (str): Destination path for the CA private key copy.
        """
        file_keywords = FileKeywords(self.ssh_connection)
        file_keywords.copy_file(K8S_CA_CERT, dest_cert, sudo=True)
        file_keywords.copy_file(K8S_CA_KEY, dest_key, sudo=True)
        self.ssh_connection.send_as_sudo(f"chmod 644 {dest_cert} {dest_key}")

    def run_rotation_script(self) -> str:
        """Run kube-cert-rotation.sh and return its combined output.

        Returns:
            str: The script's stdout/stderr output.
        """
        get_logger().log_info(f"Running {ROTATION_SCRIPT}")
        output = self.ssh_connection.send_as_sudo(f"{ROTATION_SCRIPT} --v=5")
        raw = "\n".join(output) if isinstance(output, list) else output
        get_logger().log_info(f"kube-cert-rotation.sh output:\n{raw}")
        return raw

    def get_apiserver_sans(self) -> str:
        """Read the Subject Alternative Names from the live apiserver certificate.

        Returns:
            str: An openssl subjectAltName value (e.g. 'DNS:controller-0,IP:<addr>'),
                normalised to the 'DNS:...,IP:...' request format.
        """
        output = self.ssh_connection.send_as_sudo(f"cat {APISERVER_CERT} | openssl x509 -noout -ext subjectAltName")
        raw = "\n".join(output) if isinstance(output, list) else output
        san_entries = []
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("DNS:") or line.startswith("IP Address:") or line.startswith("IP:"):
                for part in line.split(","):
                    part = part.strip().replace("IP Address:", "IP:")
                    if part.startswith("DNS:") or part.startswith("IP:"):
                        san_entries.append(part)
        get_logger().log_info(f"apiserver certificate SANs: {san_entries}")
        return ",".join(san_entries)

    def restart_apiserver(self) -> None:
        """Restart the kube-apiserver and resync sysinv, then wait for recovery.

        Mirrors the CGTS-72399-validated procedure: stop the kube-apiserver static
        pod container (kubelet recreates it) and restart the sysinv conductor and
        inventory services so the platform re-reads the updated certificate, then
        wait for the Kubernetes API to become available again.
        """
        get_logger().log_info("Restarting kube-apiserver and resyncing sysinv")
        self.ssh_connection.send_as_sudo("crictl ps | awk '/kube-apiserver/{print$1}' | xargs -r crictl stop")
        self.ssh_connection.send_as_sudo("sm-restart service sysinv-conductor")
        self.ssh_connection.send_as_sudo("sm-restart service sysinv-inv")

        # Use the framework's proven API-availability wait rather than parsing the
        # /readyz string (which returns a newline-less 'ok' that is unreliable to
        # match in captured SSH output).
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_kubernetes_api_available(timeout=600)

    def wait_for_api_available(self, timeout: int = 600) -> None:
        """Wait for the Kubernetes API to become available (without restarting anything).

        Used after kube-cert-rotation.sh runs: the script restarts the apiserver
        itself, so the test only needs to wait for the API to come back - it must
        NOT trigger another restart.

        Args:
            timeout (int): Maximum time to wait in seconds. Defaults to 600.
        """
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_kubernetes_api_available(timeout=timeout)
