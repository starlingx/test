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

    def create_secret_for_registry(self, registry: Registry, secret_name: str):
        """
        Create a secret for the registry
        Args:
            registry (): the registry
            secret_name (): the secret name

        Returns:

        """
        user_name = registry.get_user_name()
        password = registry.get_password()
        docker_server = registry.get_registry_url()
        self.ssh_connection.send(
            export_k8s_config(f"kubectl create secret docker-registry {secret_name} --docker-server={docker_server} " f"--docker-username={user_name} --docker-password={password}")
        )