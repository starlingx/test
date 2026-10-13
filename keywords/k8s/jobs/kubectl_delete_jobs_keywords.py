from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteJobsKeywords(K8sBaseKeyword):
    """
    Keywords for deleting Kubernetes jobs.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_job(self, job_name: str, namespace: str = None) -> str:
        """
        Delete the given job.

        Uses --ignore-not-found so a missing job is a no-op rather than an
        error, which is what teardown needs without masking a real failure.

        Args:
            job_name (str): The job name.
            namespace (str): The namespace. Optional.

        Returns:
            str: The output of the delete command.
        """
        cmd = f"kubectl delete job {job_name} --ignore-not-found"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"Deleted job '{job_name}'")
        return output
