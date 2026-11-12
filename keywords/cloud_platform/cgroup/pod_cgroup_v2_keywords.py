"""Keywords for reading cgroup v2 CPU and memory limits from inside a pod."""

import shlex

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.cgroup.object.pod_cgroup_v2_limits_output import PodCgroupV2LimitsOutput
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords

# cgroup v2 defaults / bounds. cpu.weight is NOT a fixed function of the CPU request: kubelet
# derives v1 shares from the request, then the OCI runtime converts shares -> weight, and that
# conversion changed (runc >= 1.3.2 / crun >= 1.23 use a new quadratic mapping). So tests assert
# the runtime-independent invariant 1 < cpu.weight < the default (for a sub-CPU request), rather
# than an exact value. See https://kubernetes.io/blog/2026/01/30/new-cgroup-v1-to-v2-cpu-conversion-formula/.
CGROUP_V2_DEFAULT_CPU_WEIGHT = 100
CGROUP_V2_MIN_CPU_WEIGHT = 1

# In-pod cgroup v2 leaf files. With cgroupns=private (the StarlingX v2 setup) each container sees
# its own leaf cgroup mounted at /sys/fs/cgroup, so these root files hold the effective limits.
POD_CPU_WEIGHT_PATH = "/sys/fs/cgroup/cpu.weight"
POD_CPU_MAX_PATH = "/sys/fs/cgroup/cpu.max"
POD_MEMORY_MAX_PATH = "/sys/fs/cgroup/memory.max"


class PodCgroupV2Keywords(BaseKeyword):
    """Keywords for reading cpu.weight, cpu.max and memory.max from inside a pod on cgroup v2.

    The limits are read with a single 'cat' of the three files inside the pod via kubectl exec, so
    this keyword's SSH connection must be an active controller. Values are read from the
    container's own leaf cgroup files, which reflect the effective CPU/memory limits kubelet
    applied for the pod's resource requests/limits.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize PodCgroupV2Keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to an active controller for exec.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def get_pod_cgroup_v2_limits(self, pod_name: str, namespace: str = None) -> PodCgroupV2LimitsOutput:
        """Read cpu.weight, cpu.max and memory.max from inside the pod's cgroup v2 leaf.

        Args:
            pod_name (str): Name of the pod to exec into.
            namespace (str): Namespace of the pod. If None, kubectl uses its default namespace. Defaults to None.

        Returns:
            PodCgroupV2LimitsOutput: The parsed cpu.weight, cpu.max (quota and period) and memory.max values.
        """
        options = f"-n {shlex.quote(namespace)}" if namespace else ""
        exec_keywords = KubectlExecInPodsKeywords(self.ssh_connection)
        output = exec_keywords.run_pod_exec_cmd(pod_name, f"cat {POD_CPU_WEIGHT_PATH} {POD_CPU_MAX_PATH} {POD_MEMORY_MAX_PATH}", options=options)
        return PodCgroupV2LimitsOutput(output)
