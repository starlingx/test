from config.docker.objects.registry import Registry
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlCreateSecretsKeywords(BaseKeyword):
    """
    Kubectl keywords for create secret
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def create_secret_for_registry(self, registry: Registry, secret_name: str, namespace: str = "default"):
        """
        Create a secret for the registry
        Args:
            registry (): the registry
            secret_name (): the secret name
            namespace (): the namespace

        Returns:

        """
        user_name = registry.get_user_name()
        password = registry.get_password()
        docker_server = registry.get_registry_url()
        self.ssh_connection.send(
            export_k8s_config(f"kubectl create secret -n {namespace} docker-registry {secret_name} --docker-server={docker_server} " f"--docker-username={user_name} --docker-password={password}")
        )

    def create_secret_generic(self, secret_name: str, tls_crt: str, tls_key: str, namespace: str):
        """
        Create a generic secret

        Args:
            secret_name (str): the secret name
            tls_crt (str): tls_crt file name
            tls_key (str): tls_key file name
            namespace (str): namespace
        """
        self.ssh_connection.send(export_k8s_config(f"kubectl create -n {namespace} secret generic {secret_name} --from-file=tls.crt={tls_crt} --from-file=tls.key={tls_key}"))
