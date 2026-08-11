"""KubectlGetCertStatusKeywords keywords."""

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.certificate.object.kubectl_get_certificate_output import KubectlGetCertsOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword

CERT_EXTRA_COLUMNS = {
    "algorithm": ".spec.privateKey.algorithm",
    "size": ".spec.privateKey.size",
    "issuer": ".spec.issuerRef.name",
    "revision": ".status.revision",
}


class KubectlGetCertStatusKeywords(K8sBaseKeyword):
    """
    Class for 'kubectl get certificate' keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection object used to interact with the Kubernetes cluster.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_certificates(self, namespace: str = None) -> KubectlGetCertsOutput:
        """
        Gets the k8s certificate that are available using 'kubectl get certificate'.

        Args:
            namespace (str, optional): The namespace to retrieve certificates from. Defaults to None.

        Returns:
            KubectlGetCertsOutput: Parsed output of the 'kubectl get certificate' command.

        """
        arg_namespace = ""
        if namespace:
            arg_namespace = f"-n {namespace}"

        kubectl_get_issuer_output = self.ssh_connection.send(self.k8s_config.export(f"kubectl {arg_namespace} get certificate"))
        self.validate_success_return_code(self.ssh_connection)

        cert_list_output = KubectlGetCertsOutput(kubectl_get_issuer_output)

        return cert_list_output

    def wait_for_certs_status(self, certs_name: str, is_ready: bool, namespace: str = None, timeout: int = 600) -> None:
        """
        Waits timeout amount of time for the given certs to be in the given status

        Args:
            certs_name (str): the name of the certificate
            is_ready (bool): the is_ready status
            namespace (str): the namespace
            timeout (int, optional): the timeout in secs

        """

        def get_cert_status():
            cert_status = self.get_certificates(namespace).get_cert(certs_name).get_ready()
            return cert_status == "True"

        validate_equals_with_retry(get_cert_status, is_ready, "Verify the certs status issued", timeout=600)

    def get_certificates_with_extra_columns(self, namespace: str, columns_to_add: list) -> KubectlGetCertsOutput:
        """Get certificates with extra spec/status columns appended.

        Args:
            namespace (str): Namespace to query.
            columns_to_add (list): Friendly column names to add (e.g., ["algorithm", "size", "issuer", "revision"]).

        Returns:
            KubectlGetCertsOutput: Parsed certificates including the requested extra columns.
        """
        base_columns = "NAME:.metadata.name,READY:.status.conditions[0].status,SECRET:.spec.secretName,AGE:.metadata.creationTimestamp"
        extra = ",".join(f"{name.upper()}:{CERT_EXTRA_COLUMNS[name]}" for name in columns_to_add if name in CERT_EXTRA_COLUMNS)
        columns = f"{base_columns},{extra}" if extra else base_columns
        cmd = self.k8s_config.export(f"kubectl get certificate -n {namespace} -o custom-columns={columns}")
        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetCertsOutput(output)
