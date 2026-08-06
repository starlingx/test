"""KubectlApplyPatchKeywords keywords."""

from framework.logging.automation_logger import get_logger
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

    def apply_patch_service(self, svc_name: str, namespace: str, args_port: str) -> None:
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

    def apply_patch_saccount(self, name: str, namespace: str, args_sa: str) -> None:
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
            args += f"-p '{args_sa}' "
        self.ssh_connection.send(self.k8s_config.export(f"kubectl patch serviceaccount {name} {args}"))
        self.validate_success_return_code(self.ssh_connection)

    def patch_host(self, host_name: str, namespace: str, patch_data: str, patch_type: str = "merge", subresource: str = None) -> None:
        """
        Apply patch to a Kubernetes Host resource.

        Args:
            host_name (str): Name of the host to patch.
            namespace (str): Namespace where the host resource exists.
            patch_data (str): Patch data as JSON string.
            patch_type (str): Type of patch operation.
            subresource (str): Subresource to patch.

        """
        cmd = f"kubectl -n {namespace} patch host {host_name} -p '{patch_data}' --type={patch_type}"

        if subresource:
            cmd += f" --subresource={subresource}"

        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def patch_resource(self, resource_type: str, resource_name: str, namespace: str, patch_json: str) -> str:
        """Patch a Kubernetes resource with JSON patch.

        Args:
            resource_type (str): Resource type (e.g., "secret").
            resource_name (str): Resource name.
            namespace (str): Namespace.
            patch_json (str): JSON patch string.

        Returns:
            str: Patch command output.
        """
        cmd = self.k8s_config.export(f"kubectl patch {resource_type} {resource_name} -n {namespace} --type='json' -p='{patch_json}'")
        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        raw = "\n".join(output) if isinstance(output, list) else output
        get_logger().log_info(f"Patch {resource_type}/{resource_name}: {raw}")
        return raw
