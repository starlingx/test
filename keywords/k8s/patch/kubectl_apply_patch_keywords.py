from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlApplyPatchKeywords(K8sBaseKeyword):
    """
    Class for Kubectl Apply Patch keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor

        Args:
            ssh_connection(SSHConnection): ssh connection object
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def apply_patch_service(self, svc_name: str, namespace: str, args_port: str):
        """
        Apply patch

        Args:
            svc_name(str): patch service name
            namespace (str): namespace for patch
            args_port(str): port patch arguments.
                e.g:'{"spec":{"type":"NodePort","ports":[{"port":443, "nodePort": 30000}]}}''
        """
        args = ""
        if namespace:
            args += f"-n {namespace} "
        if args_port:
            args += f"-p '{args_port}' "
        self.ssh_connection.send(self.k8s_config.export(f"kubectl patch service {svc_name} {args}"))
        self.validate_success_return_code(self.ssh_connection)

    def apply_patch_saccount(self, name: str, namespace: str, args_sa: str):
        """
        Apply patch

        Args:
            name(str): patch service name
            namespace (str): namespace for patch
            args_sa(str): serviceaccount arguments.
                e.g: '{"imagePullSecrets":[{"name":"docker-io"}]}'

        """
        args = ""
        if namespace:
            args += f"-n {namespace} "
        if args_sa:
            args += f"-p {args_sa} "
        self.ssh_connection.send(self.k8s_config.export(f"kubectl patch serviceaccount {name} {args}"))
        self.validate_success_return_code(self.ssh_connection)
