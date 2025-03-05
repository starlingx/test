from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlApplyPatchKeywords(BaseKeyword):
    """
    Class for Kubectl Apply Patch keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection(SSHConnection):ssh connection object
        """
        self.ssh_connection = ssh_connection

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
        self.ssh_connection.send(export_k8s_config(f"kubectl patch service {svc_name} {args}"))
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
        self.ssh_connection.send(export_k8s_config(f"kubectl patch serviceaccount {name} {args}"))
        self.validate_success_return_code(self.ssh_connection)
