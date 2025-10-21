from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlExecInPodsKeywords(BaseKeyword):
    """
    Keywords for Exec in pods
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): the ssh connection
        """
        self.ssh_connection = ssh_connection

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
        output = self.ssh_connection.send(export_k8s_config(f"kubectl exec {options} {pod_name} -- {cmd}"))
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
        self.ssh_connection.send(export_k8s_config(f"kubectl exec {pod_name} -n {namespace} -i -- calicoctl apply -f {config_file}"))
