from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords


class EjbcaSecurityKeywords(BaseKeyword):
    """Keywords for EJBCA security validation operations."""

    def __init__(self, ssh_connection: SSHConnection, namespace: str = "ejbca"):
        """Initialize EJBCA security keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
            namespace (str): Kubernetes namespace where EJBCA is deployed.
        """
        self.ssh_connection = ssh_connection
        self.namespace = namespace
        self.kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
        self.openssl_keywords = OpenSSLKeywords(ssh_connection)

    def secrets_contain_private_key(self) -> bool:
        """Check if any K8s Secret contains private key material.

        Returns:
            bool: True if private key markers found.
        """
        cmd = f"kubectl get secrets -n {self.namespace} -o yaml"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        return "BEGIN" in raw and "PRIVATE" in raw

    def configmaps_contain_private_key(self) -> bool:
        """Check if any K8s ConfigMap contains private key material.

        Returns:
            bool: True if private key markers found.
        """
        cmd = f"kubectl get configmaps -n {self.namespace} -o yaml"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        return "BEGIN" in raw and "PRIVATE" in raw

    def can_default_sa_exec_into_ejbca(self) -> bool:
        """Check if the default ServiceAccount can exec into EJBCA pod.

        Returns:
            bool: True if exec allowed (security violation).
        """
        pods_output = self.kubectl_pods.get_pods(namespace=self.namespace)
        ejbca_pods = pods_output.get_pods_start_with("ejbca")
        pod_name = ""
        for pod in ejbca_pods:
            if "pg" not in pod.get_name():
                pod_name = pod.get_name()
                break
        if not pod_name:
            return False
        cmd = (
            f"kubectl --as=system:serviceaccount:{self.namespace}:default "
            f"exec {pod_name} -n {self.namespace} -- cat /etc/hostname"
        )
        self.ssh_connection.send(export_k8s_config(cmd))
        return self.ssh_connection.get_return_code() == 0

    def is_system_local_ca_ready(self) -> bool:
        """Check if system-local-ca ClusterIssuer is Ready.

        Returns:
            bool: True if Ready.
        """
        cmd = "kubectl get clusterissuer system-local-ca -o jsonpath='{.status.conditions[0].type}'"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        raw = "\n".join(output) if isinstance(output, list) else output
        return self.ssh_connection.get_return_code() == 0 and "Ready" in raw

    def get_service_tls_cert_issuer(self, oam_ip: str, port: int) -> str:
        """Get TLS certificate issuer for EJBCA OAM endpoint.

        Args:
            oam_ip (str): OAM floating IP address.
            port (int): EJBCA external port.

        Returns:
            str: Certificate issuer string.
        """
        cmd = f"openssl s_client -connect {oam_ip}:{port} -showcerts </dev/null 2>/dev/null | openssl x509 -noout -issuer"
        output = self.ssh_connection.send(cmd)
        raw = "\n".join(output) if isinstance(output, list) else output
        return raw.strip()

    def is_fake_client_cert_accepted(self, oam_ip: str, port: int) -> bool:
        """Check if a self-signed client cert is accepted.

        Args:
            oam_ip (str): OAM floating IP.
            port (int): EJBCA external port.

        Returns:
            bool: True if fake cert accepted (security violation).
        """
        cmd = (
            f"openssl req -x509 -newkey rsa:2048 -keyout /tmp/fake.key "
            f"-out /tmp/fake.crt -days 1 -nodes -subj '/CN=fake' 2>/dev/null && "
            f"curl -sk --cert /tmp/fake.crt --key /tmp/fake.key "
            f"https://{oam_ip}:{port}/ejbca/ejbca-rest-api/v1/ca"
        )
        self.ssh_connection.send(cmd)
        return self.ssh_connection.get_return_code() == 0

    def all_pods_use_local_registry(self) -> bool:
        """Verify all pods pull images from registry.local:9001.

        Returns:
            bool: True if all images are from local registry.
        """
        cmd = f"kubectl get pods -n {self.namespace} -o jsonpath='{{.items[*].spec.containers[*].image}}'"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        images = raw.strip().split()
        for image in images:
            if image and "registry.local:9001" not in image:
                return False
        return len(images) > 0

    def verify_hostname_override_set(self, app_name: str) -> bool:
        """Verify EJBCA has hostname helm override configured.

        Args:
            app_name (str): Application name.

        Returns:
            bool: True if hostname override is set.
        """
        helm_keywords = SystemHelmOverrideKeywords(self.ssh_connection)
        override_output = helm_keywords.get_system_helm_override_show(app_name, "ejbca", "ejbca")
        raw = str(override_output)
        return "hostname" in raw.lower()

    def is_http_accessible(self, oam_ip: str, port: int) -> bool:
        """Check if plain HTTP works on the endpoint.

        Args:
            oam_ip (str): OAM floating IP.
            port (int): Port to test.

        Returns:
            bool: True if HTTP response received (security violation).
        """
        cmd = f"curl -s --max-time 5 http://{oam_ip}:{port}/ -o /dev/null -w '%{{http_code}}'"
        output = self.ssh_connection.send(cmd)
        raw = "\n".join(output) if isinstance(output, list) else output
        return self.ssh_connection.get_return_code() == 0 and "000" not in raw

    def generate_expired_cert(self, key_path: str, cert_path: str) -> None:
        """Generate a self-signed certificate with 0 days validity.

        Args:
            key_path (str): Path to write the private key.
            cert_path (str): Path to write the expired certificate.
        """
        self.openssl_keywords.generate_self_signed_cert(
            key_path, cert_path, "/CN=expired-test", days=0, algorithm="RSA", rsa_size=2048
        )
