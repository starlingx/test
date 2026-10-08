from typing import List

from keywords.k8s.jobs.object.kubectl_get_jobs_table_parser import KubectlGetJobsTableParser
from keywords.k8s.jobs.object.kubectl_jobs_object import KubectlJobObject


class KubectlGetJobsOutput:
    """
    Class for output of the get job command
    """

    def __init__(self, kubectl_get_jobs_output: str):
        """
        Constructor

        Args:
            kubectl_get_jobs_output (str): Raw string output from running a "kubectl get job" command.
        """
        self.kubectl_jobs: List[KubectlJobObject] = []
        parser = KubectlGetJobsTableParser(kubectl_get_jobs_output)
        output_values_list = parser.get_output_values_list()

        for job_dict in output_values_list:
            if "NAME" not in job_dict:
                continue
            job = KubectlJobObject(job_dict["NAME"])
            if "STATUS" in job_dict:
                job.set_status(job_dict["STATUS"])
            if "COMPLETIONS" in job_dict:
                job.set_completions(job_dict["COMPLETIONS"])
            if "DURATION" in job_dict:
                job.set_duration(job_dict["DURATION"])
            if "AGE" in job_dict:
                job.set_age(job_dict["AGE"])
            self.kubectl_jobs.append(job)

    def get_jobs(self) -> List[KubectlJobObject]:
        """Get the list of all jobs available.

        Returns:
            List[KubectlJobObject]: All parsed job objects.
        """
        return self.kubectl_jobs

    def get_job(self, job_name: str) -> KubectlJobObject:
        """
        Get the job with the specified name from this output.

        Args:
            job_name (str): The name of the job of interest.

        Returns:
            KubectlJobObject: The matching job object, or None if not present.
        """
        for job in self.kubectl_jobs:
            if job.get_name() == job_name:
                return job
        return None

    def is_job(self, job_name: str) -> bool:
        """
        Whether a job with the specified name is present in this output.

        Args:
            job_name (str): The name of the job of interest.

        Returns:
            bool: True if the job is present.
        """
        return any(job.get_name() == job_name for job in self.kubectl_jobs)
