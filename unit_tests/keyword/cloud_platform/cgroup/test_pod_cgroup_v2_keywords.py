"""Unit tests for the pod cgroup v2 keywords."""

import unittest
from unittest.mock import NonCallableMagicMock, patch

from keywords.cloud_platform.cgroup import pod_cgroup_v2_keywords as pod_cgroup
from keywords.cloud_platform.cgroup.pod_cgroup_v2_keywords import PodCgroupV2Keywords


class PodCgroupV2KeywordsTest(unittest.TestCase):
    """Exercise the kubectl exec call without a live cluster."""

    def _read_limits(self, namespace: str = None) -> tuple:
        """Run get_pod_cgroup_v2_limits against a mocked kubectl exec.

        Args:
            namespace (str): The namespace to pass, or None to omit it.

        Returns:
            tuple: The parsed limits object and the mocked run_pod_exec_cmd.
        """
        ssh = NonCallableMagicMock()
        with patch("keywords.base_keyword.get_logger"), patch.object(pod_cgroup, "KubectlExecInPodsKeywords") as executor:
            exec_cmd = executor.return_value.run_pod_exec_cmd
            exec_cmd.return_value = ["4", "10000 50000", "134217728"]
            keywords = PodCgroupV2Keywords(ssh)
            limits = (keywords.get_pod_cgroup_v2_limits("my-pod", namespace) if namespace else keywords.get_pod_cgroup_v2_limits("my-pod")).get_limits()
        return limits, exec_cmd

    def test_read_uses_requested_namespace_and_single_exec(self) -> None:
        """One kubectl exec reads all three files and passes the pod namespace."""
        limits, exec_cmd = self._read_limits("other-ns")
        self.assertEqual(exec_cmd.call_count, 1)
        args, kwargs = exec_cmd.call_args
        self.assertEqual(args[0], "my-pod")
        self.assertEqual(args[1], "cat /sys/fs/cgroup/cpu.weight /sys/fs/cgroup/cpu.max /sys/fs/cgroup/memory.max")
        self.assertEqual(kwargs["options"], "-n other-ns")
        self.assertEqual(limits.get_cpu_quota(), 10000)
        self.assertEqual(limits.get_cpu_period(), 50000)

    def test_read_without_namespace_omits_namespace_option(self) -> None:
        """No -n option is added when no namespace is given."""
        _, exec_cmd = self._read_limits()
        self.assertEqual(exec_cmd.call_args.kwargs["options"], "")


if __name__ == "__main__":
    unittest.main()
