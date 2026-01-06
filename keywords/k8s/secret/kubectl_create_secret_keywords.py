from config.docker.objects.registry import Registry
from keywords.base_keyword import BaseKeyword
from framework.logging.automation_logger import get_logger
from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords

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

    def create_secret_generic(self, namespace: str, secret_name: str, tls_crt: str, tls_key: str = None):
        """
        Create a generic secret, with explicit filename, or tls.crt / tls.key

        Args:
            namespace (str): namespace
            secret_name (str): the secret name
            tls_crt (str): tls_crt file name
            tls_key (str): tls_key file name (optional)
        """

        base_cmd = f"kubectl create -n {namespace} secret generic {secret_name}"

        if tls_key:
            base_cmd += f" --from-file=tls.crt={tls_crt} --from-file=tls.key={tls_key}"
        else:
            base_cmd += f" --from-file={tls_crt}"

        self.ssh_connection.send(export_k8s_config(base_cmd))
        self.validate_success_return_code(self.ssh_connection)
        list_of_secrets = KubectlGetSecretsKeywords(self.ssh_connection).get_secret_names(namespace=namespace)
        if secret_name in list_of_secrets:
            get_logger().log_info(f"Kubernetes secret {secret_name} created successfully.")
        else:
            raise KeywordException(f"Failed to create Kubernetes secret {secret_name}.")

