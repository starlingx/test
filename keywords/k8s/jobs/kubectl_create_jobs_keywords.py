from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCreateJobsKeywords(K8sBaseKeyword):
    """
    Keywords for creating Kubernetes jobs.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def create_job_from_cronjob(self, job_name: str, cronjob_name: str, namespace: str = None) -> str:
        """
        Create a one-off job from an existing cronjob.

        Running a job from a cronjob executes the same workload immediately
        rather than waiting for the cronjob's schedule to fire.

        Args:
            job_name (str): Name for the one-off job to create.
            cronjob_name (str): The cronjob to create the job from.
            namespace (str): The namespace. Optional.

        Returns:
            str: The output of the create command.
        """
        cmd = f"kubectl create job {job_name} --from=cronjob/{cronjob_name}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        get_logger().log_info(f"Creating job '{job_name}' from cronjob '{cronjob_name}'")
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return output
