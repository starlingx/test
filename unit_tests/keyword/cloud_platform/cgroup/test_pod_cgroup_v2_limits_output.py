"""Unit tests for parsing the pod cgroup v2 limits output."""

import unittest

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.cgroup.object.pod_cgroup_v2_limits_output import PodCgroupV2LimitsOutput


class PodCgroupV2LimitsOutputTest(unittest.TestCase):
    """Exercise the limits output parsing without a live cluster."""

    def test_limits_output_parses_list_and_string(self) -> None:
        """The three files parse into typed values from either a list of lines or one string."""
        for raw in (["4\n", "20000 100000\n", "134217728\n"], ["4", "20000 100000", "134217728"], "4\n20000 100000\n134217728\n"):
            limits = PodCgroupV2LimitsOutput(raw).get_limits()
            self.assertEqual(limits.get_cpu_weight(), 4)
            self.assertEqual(limits.get_cpu_quota(), 20000)
            self.assertEqual(limits.get_cpu_period(), 100000)
            self.assertEqual(limits.get_memory_max(), 134217728)
        self.assertIn("cpu.weight=4", str(limits))
        self.assertIn("cpu.max='20000 100000'", str(limits))

    def test_limits_output_parses_non_default_period(self) -> None:
        """A cpu.max with a non-default period is split into quota and period."""
        limits = PodCgroupV2LimitsOutput(["4", "10000 50000", "134217728"]).get_limits()
        self.assertEqual(limits.get_cpu_quota(), 10000)
        self.assertEqual(limits.get_cpu_period(), 50000)

    def test_limits_output_rejects_bad_output(self) -> None:
        """A wrong line count, a malformed cpu.max or a non-integer value such as 'max' raises a clear error."""
        with self.assertRaises(KeywordException):
            PodCgroupV2LimitsOutput(["4", "20000 100000"])
        with self.assertRaises(KeywordException):
            PodCgroupV2LimitsOutput(["4", "20000", "134217728"])
        with self.assertRaises(KeywordException):
            PodCgroupV2LimitsOutput(["4", "max 100000", "134217728"])
        with self.assertRaises(KeywordException):
            PodCgroupV2LimitsOutput(["4", "20000 100000", "max"])


if __name__ == "__main__":
    unittest.main()
