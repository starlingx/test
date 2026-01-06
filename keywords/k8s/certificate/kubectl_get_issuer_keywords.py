from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.k8s.certificate.object.kubectl_get_issuer_output import KubectlGetIssuerOutput
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlGetCertIssuerKeywords(BaseKeyword):
    """
    Class for 'kubectl get issuer' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection object used to interact with the Kubernetes cluster.
        """
        self.ssh_connection = ssh_connection

    def get_issuers(self, namespace: str = None) -> KubectlGetIssuerOutput:
        """
        Gets the k8s issuer that are available using 'kubectl get issuer'.

        Args:
            namespace (str, optional): the namespace

        Returns:
            KubectlGetIssuerOutput: Parsed output of the 'kubectl get issuer' command.
        """
        arg_namespace = ""
        if namespace:
            arg_namespace = f"-n {namespace}"

        kubectl_get_issuer_output = self.ssh_connection.send(export_k8s_config(f"kubectl {arg_namespace} get issuer"))
        self.validate_success_return_code(self.ssh_connection)

        issuer_list_output = KubectlGetIssuerOutput(kubectl_get_issuer_output)

        return issuer_list_output

    def wait_for_issuer_status(self, issuer_name: str, is_ready: bool, namespace: str = None, timeout: int = 600) -> None:
        """
        Waits timeout amount of time for the given issuer to be in the given status

        Args:
            issuer_name (str): the certs issuer name
            is_ready (bool): the is_ready status
            namespace (str , optional): the namespace
            timeout (int): the timeout in secs

        """

        def get_issuer_status():
            issuer_status = self.get_issuers(namespace).get_issuer(issuer_name).get_ready()
            return bool(issuer_status)

        message = f"issuer {issuer_name}'s status is {is_ready}"
        validate_equals_with_retry(get_issuer_status, is_ready, message, timeout=600)
