import time

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class EjbcaCertManagerKeywords(BaseKeyword):
    """Keywords for cert-manager integration with EJBCA ClusterIssuer."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize cert-manager keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)

    def is_cluster_issuer_ready(self, issuer_name: str) -> bool:
        """Check if a ClusterIssuer is in Ready state.

        Args:
            issuer_name (str): Name of the ClusterIssuer resource.

        Returns:
            bool: True if the issuer condition is Ready.
        """
        cmd = f"kubectl get clusterissuer {issuer_name} -o jsonpath='{{.status.conditions[0].type}}'"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        return self.ssh_connection.get_return_code() == 0 and "Ready" in output

    def create_certificate_cr(self, name: str, namespace: str, secret_name: str, common_name: str, issuer_name: str, issuer_group: str, duration: str = "2160h", renew_before: str = "360h", dns_names: list = None) -> None:
        """Create a Certificate CR for cert-manager to process.

        Args:
            name (str): Certificate resource name.
            namespace (str): Namespace for the Certificate.
            secret_name (str): Name of the TLS secret to create.
            common_name (str): Certificate common name.
            issuer_name (str): ClusterIssuer name.
            issuer_group (str): ClusterIssuer API group.
            duration (str): Certificate duration.
            renew_before (str): Renewal trigger time before expiry.
            dns_names (list): Optional list of DNS SANs.
        """
        dns_section = ""
        if dns_names:
            entries = "\n".join([f"    - {d}" for d in dns_names])
            dns_section = f"  dnsNames:\n{entries}\n"
        cert_yaml = (
            "apiVersion: cert-manager.io/v1\nkind: Certificate\nmetadata:\n"
            f"  name: {name}\n  namespace: {namespace}\nspec:\n"
            f"  secretName: {secret_name}\n  duration: {duration}\n"
            f"  renewBefore: {renew_before}\n  commonName: {common_name}\n"
            f"{dns_section}  issuerRef:\n    name: {issuer_name}\n"
            f"    group: {issuer_group}\n    kind: ClusterIssuer\n"
        )
        yaml_path = f"/tmp/cert-{name}.yaml"
        self.file_keywords.write_to_file(yaml_path, cert_yaml)
        self.ssh_connection.send(export_k8s_config(f"kubectl apply -f {yaml_path}"))
        self.validate_success_return_code(self.ssh_connection)

    def wait_for_certificate_ready(self, name: str, namespace: str, timeout: int = 120) -> bool:
        """Wait for a Certificate CR to become Ready.

        Args:
            name (str): Certificate resource name.
            namespace (str): Namespace of the Certificate.
            timeout (int): Maximum wait time in seconds.

        Returns:
            bool: True if Certificate became Ready.
        """
        cmd = f"kubectl wait certificate {name} -n {namespace} --for=condition=Ready --timeout={timeout}s"
        self.ssh_connection.send(export_k8s_config(cmd))
        return self.ssh_connection.get_return_code() == 0

    def get_tls_secret_cert_data(self, secret_name: str, namespace: str) -> str:
        """Get the base64-encoded certificate from a TLS secret.

        Args:
            secret_name (str): Name of the TLS secret.
            namespace (str): Namespace of the secret.

        Returns:
            str: Base64-encoded certificate data, or empty string.
        """
        cmd = f"kubectl get secret {secret_name} -n {namespace} -o jsonpath='{{.data.tls\\.crt}}'"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        return output.strip() if self.ssh_connection.get_return_code() == 0 else ""

    def delete_certificate_cr(self, name: str, namespace: str) -> None:
        """Delete a Certificate CR.

        Args:
            name (str): Certificate resource name.
            namespace (str): Namespace of the Certificate.
        """
        self.ssh_connection.send(export_k8s_config(f"kubectl delete certificate {name} -n {namespace} --ignore-not-found"))

    def delete_tls_secret(self, secret_name: str, namespace: str) -> None:
        """Delete a TLS secret.

        Args:
            secret_name (str): Name of the TLS secret.
            namespace (str): Namespace of the secret.
        """
        self.ssh_connection.send(export_k8s_config(f"kubectl delete secret {secret_name} -n {namespace} --ignore-not-found"))

    def get_pod_cpu_usage(self, namespace: str) -> str:
        """Get CPU usage of pods in a namespace.

        Args:
            namespace (str): Namespace to query.

        Returns:
            str: Raw output of kubectl top pods.
        """
        return self.ssh_connection.send(export_k8s_config(f"kubectl top pods -n {namespace} --no-headers"))

    def wait_for_secret_exists(self, secret_name: str, namespace: str, timeout: int = 120) -> bool:
        """Wait for a secret to exist.

        Args:
            secret_name (str): Name of the secret.
            namespace (str): Namespace of the secret.
            timeout (int): Maximum wait time in seconds.

        Returns:
            bool: True if secret exists within timeout.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            data = self.get_tls_secret_cert_data(secret_name, namespace)
            if data:
                return True
            time.sleep(5)
        return False
