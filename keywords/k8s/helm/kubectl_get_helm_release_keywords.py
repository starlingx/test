from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.k8s.helm.object.kubectl_get_helm_release_output import KubectlGetHelmReleaseOutput
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlGetHelmReleaseKeywords(BaseKeyword):
    """
    Class for 'kubectl get hr' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def get_helm_releases_by_namespace(self, namespace: str) -> KubectlGetHelmReleaseOutput:
        """
        Gets the k8s helm releases available for a given namespace.

        Args:
            namespace (str): the namespace

        Returns:
             KubectlGetHelmReleaseOutput: List of KubectlGetHelmReleaseOutput

        """
        kubectl_get_helm_releases_output = self.ssh_connection.send(export_k8s_config(f"kubectl get hr -n {namespace}"))
        self.validate_success_return_code(self.ssh_connection)
        kubectl_list_helm_releases_output = KubectlGetHelmReleaseOutput(kubectl_get_helm_releases_output)

        return kubectl_list_helm_releases_output

    def validate_helm_release_exists(self, is_expected_to_exist: bool, helm_name: str, namespace: str, validation_description: str) -> None:
        """
        Check if a helm release exist.

        Args:
            is_expected_to_exist (bool): if helm release is expect to exist or not
            helm_name (str): the name of helm release
            namespace (str): the namespace
            validation_description (str): Description of this validation for logging purposes.

        Returns: None

        """
        helm_releases_list = self.get_helm_releases_by_namespace(namespace)
        validate_equals_with_retry(lambda: helm_releases_list.is_helm_release(helm_name), is_expected_to_exist, validation_description)
