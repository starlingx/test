from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlExecInPodsKeywords(K8sBaseKeyword):
    """
    Keywords for Exec in pods
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): the ssh connection
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def run_pod_exec_cmd(
        self,
        pod_name: str,
        cmd: str,
        options: str = "",
    ) -> str:
        """
        Executes the given command in the pod

        Args:
            pod_name (str): the name of the pod
            cmd (str): the cmd to execute
            options (str): options

        Returns:
            str: the output

        """
        kubectl_cmd = f"kubectl exec {options} {pod_name} -- {cmd}"

        output = self.ssh_connection.send(self.k8s_config.export(kubectl_cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output

    def exec_calicoctl_apply(self, pod_name: str, namespace: str, config_file: str):
        """
        exec_calicoctl_apply

        Args:
            pod_name (str): the name of the pod
            namespace (str): namespace
            config_file (str): config file

        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl exec {pod_name} -n {namespace} -i -- calicoctl apply -f {config_file}"))
