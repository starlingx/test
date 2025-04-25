from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.k8s.certificate.object.kubectl_get_certificate_output import KubectlGetCertsOutput
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlGetCertStatusKeywords(BaseKeyword):
    """
    Class for 'kubectl get certificate' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection object used to interact with the Kubernetes cluster.
        """
        self.ssh_connection = ssh_connection

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

        kubectl_get_issuer_output = self.ssh_connection.send(export_k8s_config(f"kubectl {arg_namespace} get certificate"))
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
            return bool(cert_status)

        validate_equals_with_retry(get_cert_status, is_ready, "Verify the certs status issued", timeout=600)
