from keywords.base_keyword import BaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords


class CatCpuSetKeywords(BaseKeyword):
    """
    Class for 'kubectl get ns' keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_cpuset_from_pod(self, pod_name: str) -> str:
        """
        This function will get the cpuset associated with the specified pod.
        Args:
            pod_name: Name of the pod for which we want the CPUSet.

        Returns: (str) String id for the associated CPUSet associated with the pod.

        """

        exec_in_pod = KubectlExecInPodsKeywords(self.ssh_connection)
        command_output = exec_in_pod.run_pod_exec_cmd(pod_name, "cat /proc/self/cpuset")

        # Output will be of the form:
        # /k8s-infra/kubepods/burstable/podf29015d0-4696-4a3a-9b45-03f3b9329251/fb27aa9fd05033f7bab0eeb65618b3f56d8da3bfa209c401cabd206a3d42a1fa
        # We want to parse out the ID right next to the /pod
        # f29015d0-4696-4a3a-9b45-03f3b9329251
        cpuset_string = command_output[0]
        sections_list = cpuset_string.split("/")
        for section in sections_list:
            if section.startswith("pod"):
                return section[len("pod") :].strip()
        raise ValueError("There was no '/podXYZ/' section in the pod's cpuset")
