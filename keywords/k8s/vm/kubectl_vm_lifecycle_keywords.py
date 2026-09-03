from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlVmLifecycleKeywords(K8sBaseKeyword):
    """Keywords for starting and stopping KubeVirt VirtualMachines via kubectl.

    Start/stop are driven by patching the VirtualMachine spec.running field so the
    operation is independent of any client tooling (virtctl) and safe to use for
    test setup and teardown regardless of the mechanism under test.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize the KubectlVmLifecycleKeywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def start_vm(self, vm_name: str, namespace: str = "default") -> None:
        """Start a VM by patching its spec.running to true.

        Args:
            vm_name (str): Name of the VM to start.
            namespace (str): Namespace of the VM. Defaults to 'default'.
        """
        cmd = f'kubectl patch vm {vm_name} -n {namespace} --type merge -p \'{{"spec":{{"running":true}}}}\''
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def stop_vm(self, vm_name: str, namespace: str = "default") -> None:
        """Stop a VM by patching its spec.running to false.

        Args:
            vm_name (str): Name of the VM to stop.
            namespace (str): Namespace of the VM. Defaults to 'default'.
        """
        cmd = f'kubectl patch vm {vm_name} -n {namespace} --type merge -p \'{{"spec":{{"running":false}}}}\''
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
