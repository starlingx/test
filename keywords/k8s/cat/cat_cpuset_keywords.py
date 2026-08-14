import re

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class CatCpuSetKeywords(BaseKeyword):
    """Keywords for reading pod cpuset and cgroup information."""

    def __init__(self, ssh_connection):
        """Constructor.

        Args:
            ssh_connection: SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_cpuset_from_pod(self, pod_name: str) -> str:
        """Get the pod UID from the pod's cgroup/cpuset path.

        On cgroups v1, reads /proc/self/cpuset which contains the pod UID directly
        in the path. On cgroups v2 (e.g. containerd 2.x + Debian 13), /proc/self/cpuset
        returns just '/', so we fall back to /proc/self/cgroup to extract the pod UID.
        As a final fallback, queries the Kubernetes API via kubectl.

        Args:
            pod_name: Name of the pod for which we want the pod UID.

        Returns:
            str: The pod UID (e.g. 'f29015d0-4696-4a3a-9b45-03f3b9329251').

        Raises:
            ValueError: If the pod UID cannot be extracted from any source.
        """
        logger = get_logger()
        exec_in_pod = KubectlExecInPodsKeywords(self.ssh_connection)
        command_output = exec_in_pod.run_pod_exec_cmd(pod_name, "cat /proc/self/cpuset")

        # cgroups v1 output format:
        # /k8s-infra/kubepods/burstable/podf29015d0-4696-4a3a-9b45-03f3b9329251/fb27aa9fd...
        # We parse out the UID right after '/pod'
        cpuset_string = command_output[0]
        pod_uid = self._extract_pod_uid_from_cgroupv1_path(cpuset_string)
        if pod_uid:
            return pod_uid

        # On cgroups v2 with cgroupns=private, /proc/self/cpuset returns just '/'.
        # Fall back to reading /proc/self/cgroup which may contain the pod UID.
        logger.log_info(f"Pod {pod_name} cpuset returned '{cpuset_string.strip()}' (cgroups v2). Falling back to /proc/self/cgroup to extract pod UID.")
        cgroup_output = exec_in_pod.run_pod_exec_cmd(pod_name, "cat /proc/self/cgroup")
        cgroup_full_string = "\n".join(cgroup_output) if cgroup_output else ""
        logger.log_info(f"Pod {pod_name} /proc/self/cgroup content: {cgroup_full_string}")

        pod_uid = self._extract_pod_uid_from_cgroupv2_path(cgroup_full_string)
        if pod_uid:
            return pod_uid

        # Also try matching a direct /pod<UID>/ segment in any line (cgroups v1 style in cgroup file)
        for line in cgroup_output:
            pod_uid = self._extract_pod_uid_from_cgroupv1_path(line)
            if pod_uid:
                return pod_uid

        # Final fallback: on cgroupv2 with cgroupns=private, /proc/self/cgroup returns just "0::/"
        # with no pod UID visible from inside the container. Use kubectl API to get the pod UID.
        logger.log_info(f"Could not extract pod UID from cgroup content '{cgroup_full_string.strip()}'. Falling back to kubectl API for pod {pod_name}.")
        pod_uid = KubectlGetPodsKeywords(self.ssh_connection).get_pod_uid_by_label(f"app={pod_name}")
        if pod_uid:
            logger.log_info(f"Got pod UID from kubectl API: {pod_uid}")
            return pod_uid

        raise ValueError(f"Could not extract pod UID from cpuset ('{cpuset_string.strip()}'), /proc/self/cgroup ('{cgroup_full_string.strip()}'), or kubectl API for pod {pod_name}.")

    def _extract_pod_uid_from_cgroupv1_path(self, path: str) -> str:
        """Extract pod UID from a cgroups v1 cpuset/cgroup path string.

        Looks for a path segment starting with 'pod' followed by a UUID-like string.
        Example: /kubepods/burstable/podf29015d0-4696-4a3a-9b45-03f3b9329251/...

        Args:
            path: A cgroup or cpuset path string to parse.

        Returns:
            str: The pod UID if found, or empty string if not found.
        """
        sections_list = path.split("/")
        for section in sections_list:
            if section.startswith("pod"):
                uid = section[len("pod"):].strip()
                if uid:
                    return uid
        return ""

    def _extract_pod_uid_from_cgroupv2_path(self, cgroup_content: str) -> str:
        """Extract pod UID from a cgroups v2 cgroup path string.

        Handles systemd slice format where the pod UID uses underscores instead of dashes.
        Example: 0::/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod<UID_underscored>.slice/...

        Also handles non-slice formats like:
        0::/system.slice/containerd.service/kubepods-pod<UID>/<CID>

        Args:
            cgroup_content: Full content of /proc/self/cgroup (may be multiline).

        Returns:
            str: The pod UID if found, or empty string if not found.
        """
        # Match systemd slice format: pod<UID_underscored>.slice
        pod_uid_match = re.search(r"pod([0-9a-f_-]+)\.slice", cgroup_content)
        if pod_uid_match:
            return pod_uid_match.group(1).replace("_", "-").strip()

        # Match non-slice format with full UUID pattern
        pod_uid_match = re.search(r"pod([0-9a-f]{8}[-_][0-9a-f]{4}[-_][0-9a-f]{4}[-_][0-9a-f]{4}[-_][0-9a-f]{12})", cgroup_content)
        if pod_uid_match:
            return pod_uid_match.group(1).replace("_", "-").strip()

        return ""
