from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.cgroup.cgroup_keywords import CGROUP_V2
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.linux.sysfs.object.numa_online_nodes_output import NumaOnlineNodesOutput

K8SINFRA_CPUSET_MEMS_PATH_V1 = "/sys/fs/cgroup/cpuset/k8sinfra/cpuset.mems"
KUBEPODS_CPUSET_MEMS_PATH_V1 = "/sys/fs/cgroup/cpuset/k8sinfra/kubepods/cpuset.mems"
K8SINFRA_CPUSET_MEMS_PATH_V2 = "/sys/fs/cgroup/k8sinfra.slice/cpuset.mems.effective"
KUBEPODS_CPUSET_MEMS_PATH_V2 = "/sys/fs/cgroup/k8sinfra.slice/k8sinfra-kubepods.slice/cpuset.mems.effective"

# In-pod cpuset.mems path. On cgroup v1 the cpuset controller is mounted separately; on v2 the
# unified hierarchy is mounted at the cgroup root and the inherited value is cpuset.mems.effective.
POD_CPUSET_MEMS_PATH_V1 = "/sys/fs/cgroup/cpuset/cpuset.mems"
POD_CPUSET_MEMS_PATH_V2 = "/sys/fs/cgroup/cpuset.mems.effective"

POD_PROC_STATUS_PATH = "/proc/self/status"


class NumaCpusetKeywords(BaseKeyword):
    """Keywords for reading the cpuset.mems NUMA field from cgroups and pods.

    Supports the multi-NUMA cpuset.mems checks: reading cpuset.mems on the bare-metal
    k8sinfra/kubepods cgroups and reading cpuset.mems / Mems_allowed_list from inside a pod.
    Paths are selected for the given cgroup version (cpuset.mems on v1, the inherited
    cpuset.mems.effective on v2). Values are returned as parsed NUMA-node sets.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize NumaCpusetKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for command execution.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    @staticmethod
    def _to_text(output: object) -> str:
        """Normalize an SSH/exec response (str or list of str) to a single string.

        Args:
            output (object): The raw response from an SSH send or kubectl exec.

        Returns:
            str: The response joined into one string.
        """
        if isinstance(output, list):
            return "".join(output)
        return str(output)

    def get_k8sinfra_cpuset_mems_nodes(self, cgroup_version: str) -> set:
        """Read cpuset.mems on the bare-metal k8sinfra cgroup for the given cgroup version.

        Args:
            cgroup_version (str): CGROUP_V1 or CGROUP_V2.

        Returns:
            set: The set of NUMA node indices the k8sinfra cgroup exposes.
        """
        path = K8SINFRA_CPUSET_MEMS_PATH_V2 if cgroup_version == CGROUP_V2 else K8SINFRA_CPUSET_MEMS_PATH_V1
        return self._read_host_cpuset_mems(path)

    def get_kubepods_cpuset_mems_nodes(self, cgroup_version: str) -> set:
        """Read cpuset.mems on the bare-metal kubepods cgroup for the given cgroup version.

        Args:
            cgroup_version (str): CGROUP_V1 or CGROUP_V2.

        Returns:
            set: The set of NUMA node indices the kubepods cgroup exposes.
        """
        path = KUBEPODS_CPUSET_MEMS_PATH_V2 if cgroup_version == CGROUP_V2 else KUBEPODS_CPUSET_MEMS_PATH_V1
        return self._read_host_cpuset_mems(path)

    def _read_host_cpuset_mems(self, path: str) -> set:
        """Read and parse a bare-metal cpuset.mems file on the host (via sudo).

        Args:
            path (str): Absolute path to the cpuset.mems file to read.

        Returns:
            set: The set of NUMA node indices listed in the file (empty if the file is empty).
        """
        output = self.ssh_connection.send_as_sudo_non_interactive(f"cat {path}")
        self.validate_success_return_code(self.ssh_connection)
        value = self._to_text(output).strip()
        return NumaOnlineNodesOutput(value).get_online_node_ids_as_frozenset()

    def get_pod_cpuset_mems_nodes(self, pod_name: str, cgroup_version: str) -> set:
        """Read cpuset.mems from inside a pod for the given cgroup version.

        Runs 'cat <cpuset.mems path>' inside the pod via kubectl exec, so this keyword's SSH
        connection must be an active controller.

        Args:
            pod_name (str): Name of the pod to exec into.
            cgroup_version (str): CGROUP_V1 or CGROUP_V2.

        Returns:
            set: The set of NUMA node indices the pod's cpuset.mems exposes.
        """
        path = POD_CPUSET_MEMS_PATH_V2 if cgroup_version == CGROUP_V2 else POD_CPUSET_MEMS_PATH_V1
        exec_keywords = KubectlExecInPodsKeywords(self.ssh_connection)
        output = exec_keywords.run_pod_exec_cmd(pod_name, f"cat {path}")
        value = self._to_text(output).strip()
        return NumaOnlineNodesOutput(value).get_online_node_ids_as_frozenset()

    def get_pod_mems_allowed_nodes(self, pod_name: str) -> set:
        """Read Mems_allowed_list from /proc/self/status inside a pod.

        This is the set of NUMA memory nodes the pod's processes are allowed to use, and is
        independent of cgroup version. The exec runs via kubectl, so this keyword's SSH
        connection must be an active controller.

        Args:
            pod_name (str): Name of the pod to exec into.

        Returns:
            set: The set of NUMA node indices in the pod's Mems_allowed_list.
        """
        exec_keywords = KubectlExecInPodsKeywords(self.ssh_connection)
        output = exec_keywords.run_pod_exec_cmd(pod_name, f"grep Mems_allowed_list {POD_PROC_STATUS_PATH}")
        text = self._to_text(output)
        value = text.split(":", 1)[-1].strip() if ":" in text else text.strip()
        return NumaOnlineNodesOutput(value).get_online_node_ids_as_frozenset()
