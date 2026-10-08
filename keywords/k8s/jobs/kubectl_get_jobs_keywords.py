from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.jobs.object.kubectl_get_jobs_output import KubectlGetJobsOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetJobsKeywords(K8sBaseKeyword):
    """
    Keywords for getting Kubernetes jobs.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_job(self, job_name: str, namespace: str = None) -> KubectlGetJobsOutput:
        """
        Get the job with the specified name.

        Args:
            job_name (str): the job name.
            namespace (str): the namespace. Optional.

        Returns:
            KubectlGetJobsOutput: The job output object.
        """
        cmd = f"kubectl get job {job_name}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetJobsOutput(output)

    def get_jobs(self, namespace: str = None) -> KubectlGetJobsOutput:
        """
        Get the jobs from the specified namespace, or all namespaces if not specified.

        Args:
            namespace (str): the namespace. Optional.

        Returns:
            KubectlGetJobsOutput: The job output object.
        """
        cmd = "kubectl get job"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetJobsOutput(output)

    def wait_for_job_completed(self, job_name: str, namespace: str = None, timeout: int = 300, polling_sleep_time: int = 10) -> None:
        """
        Wait until a job reports all of its completions succeeded.

        Args:
            job_name (str): The job name to poll.
            namespace (str): The namespace. Optional.
            timeout (int): Maximum seconds to wait. Defaults to 300.
            polling_sleep_time (int): Seconds between polls. Defaults to 10.

        Raises:
            TimeoutError: If the job does not complete within the timeout.
        """

        def _is_completed() -> bool:
            # List rather than get the job by name: create_job_from_cronjob can
            # return before the Job object is listed, and "kubectl get job
            # <name>" on a not-yet-created job fails return-code validation and
            # would raise inside the poller, aborting the retry. Listing
            # tolerates the gap - an absent job is simply "not complete yet".
            job = self.get_jobs(namespace).get_job(job_name)
            return job is not None and job.is_completed()

        validate_equals_with_retry(
            _is_completed,
            True,
            f"Job '{job_name}' completed successfully",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )
