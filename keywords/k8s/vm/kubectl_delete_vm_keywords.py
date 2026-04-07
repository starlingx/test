from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteVmKeywords(K8sBaseKeyword):
    """Keywords for kubectl delete vm operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize delete vm keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_vm(self, vm_name: str, namespace: str = "default", ignore_not_found: bool = False) -> None:
        """Delete a VirtualMachine resource.

        Args:
            vm_name (str): Name of the VM to delete.
            namespace (str): Namespace of the VM. Defaults to 'default'.
            ignore_not_found (bool): If True, adds --ignore-not-found=true flag. Defaults to False.
        """
        ignore_flag = " --ignore-not-found=true" if ignore_not_found else ""
        cmd = f"kubectl delete vm {vm_name} -n {namespace}{ignore_flag}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
