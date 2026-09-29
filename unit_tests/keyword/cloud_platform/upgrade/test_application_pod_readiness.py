"""Unit tests for the not-ready pod readiness checks.

Cover the pod-readiness counting without a lab: that a pod whose containers are still starting is
reported even while its phase is Running, that pods which terminated successfully are excluded, and
that the count falls back to its sentinel when the namespace holds fewer pods than expected.
"""

import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.k8s.pods.object.kubectl_get_pods_output import KubectlGetPodsOutput


def build_pods_output(pods: list[tuple[str, str, str]]) -> KubectlGetPodsOutput:
    """Return a KubectlGetPodsOutput built from simple pod tuples.

    The table parser iterates the output line by line and locates each column by the character
    offset of its header, so the output is supplied as newline-terminated lines whose values are
    padded to fixed widths to line up beneath that header.

    Args:
        pods (list[tuple[str, str, str]]): tuples of (name, ready, status), for example ("o2api", "5/5", "Running").

    Returns:
        KubectlGetPodsOutput: output object holding the described pods.
    """
    widths = (30, 10, 24, 12)
    columns = ("NAME", "READY", "STATUS", "RESTARTS")
    lines = ["".join(name.ljust(width) for name, width in zip(columns, widths)) + "AGE\n"]
    for name, ready, status in pods:
        values = (name, ready, status, "0")
        lines.append("".join(value.ljust(width) for value, width in zip(values, widths)) + "10m\n")
    return KubectlGetPodsOutput(lines, source="table")


class TestGetNotReadyPods(unittest.TestCase):
    """Test suite for KubectlGetPodsOutput.get_not_ready_pods."""

    def test_running_and_fully_ready_pod_is_not_reported(self):
        """A pod whose ready count equals its total is ready."""
        output = build_pods_output([("o2api", "5/5", "Running")])
        self.assertEqual(output.get_not_ready_pods(), [])

    def test_running_pod_with_starting_containers_is_reported(self):
        """A Running pod below its ready total is not ready."""
        output = build_pods_output([("o2api", "0/5", "Running")])
        self.assertEqual([pod.get_name() for pod in output.get_not_ready_pods()], ["o2api"])

    def test_completed_pod_is_excluded(self):
        """A job pod that finished reports Completed below its total and is not a failure."""
        output = build_pods_output([("o2api", "5/5", "Running"), ("db-init", "0/1", "Completed")])
        self.assertEqual(output.get_not_ready_pods(), [])

    def test_succeeded_pod_is_excluded(self):
        """Succeeded is the other terminal success state and is also excluded."""
        output = build_pods_output([("hook", "0/1", "Succeeded")])
        self.assertEqual(output.get_not_ready_pods(), [])

    def test_terminal_pods_do_not_mask_a_genuinely_unready_pod(self):
        """Excluding terminal pods must not hide a pod that is still starting."""
        output = build_pods_output(
            [
                ("o2api", "5/5", "Running"),
                ("db-init", "0/1", "Completed"),
                ("o2api-new", "0/5", "Running"),
            ]
        )
        self.assertEqual([pod.get_name() for pod in output.get_not_ready_pods()], ["o2api-new"])

    def test_failed_pod_is_reported(self):
        """A pod in a failure state is not ready."""
        output = build_pods_output([("o2api", "0/5", "CrashLoopBackOff")])
        self.assertEqual([pod.get_name() for pod in output.get_not_ready_pods()], ["o2api"])


class TestGetNotReadyPodCount(unittest.TestCase):
    """Test suite for ApplicationHealthKeywords.get_not_ready_pod_count."""

    NAMESPACE = "test-namespace"

    def setUp(self):
        """Silence the BaseKeyword logging wrapper and the keyword's own logger."""
        self.patchers = [
            patch("keywords.base_keyword.get_logger"),
            patch("keywords.cloud_platform.upgrade.application_health_keywords.get_logger"),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        """Stop the logger patchers."""
        for patcher in self.patchers:
            patcher.stop()

    def _build_keywords(self, pods: list[tuple[str, str, str]]) -> ApplicationHealthKeywords:
        """Return ApplicationHealthKeywords whose pod read yields the given pods.

        BaseKeyword.__getattribute__ wraps every callable attribute in a logging wrapper, so
        collaborators are installed with object.__setattr__ and built from NonCallableMagicMock to
        keep that wrapper from replacing them.

        Args:
            pods (list[tuple[str, str, str]]): tuples of (name, ready, status).

        Returns:
            ApplicationHealthKeywords: instance with a stubbed pod read.
        """
        keywords = ApplicationHealthKeywords.__new__(ApplicationHealthKeywords)
        output = build_pods_output(pods)

        pods_keywords = NonCallableMagicMock()
        pods_keywords.get_pods = MagicMock(return_value=output)
        pods_keywords.get_pods_with_retry = MagicMock(return_value=output)

        object.__setattr__(keywords, "pods", pods_keywords)
        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        return keywords

    def test_counts_only_the_unready_pods(self):
        """Two starting pods alongside a ready one count as two."""
        keywords = self._build_keywords([("o2api", "5/5", "Running"), ("a", "0/1", "Running"), ("b", "0/1", "Running")])
        self.assertEqual(keywords.get_not_ready_pod_count(self.NAMESPACE, expected_min=1), 2)

    def test_completed_pod_does_not_count(self):
        """A namespace whose only extra pod is Completed reports no unready pods."""
        keywords = self._build_keywords([("o2api", "5/5", "Running"), ("db-init", "0/1", "Completed")])
        self.assertEqual(keywords.get_not_ready_pod_count(self.NAMESPACE, expected_min=1), 0)

    def test_sentinel_when_fewer_pods_than_expected(self):
        """Fewer pods than expected_min reports the sentinel rather than zero."""
        keywords = self._build_keywords([("o2api", "5/5", "Running")])
        self.assertEqual(
            keywords.get_not_ready_pod_count(self.NAMESPACE, expected_min=3),
            keywords.POD_COUNT_BELOW_EXPECTED,
        )

    def test_sentinel_is_not_mistaken_for_ready(self):
        """The sentinel must be distinguishable from a healthy zero."""
        self.assertNotEqual(ApplicationHealthKeywords.POD_COUNT_BELOW_EXPECTED, 0)

    def test_read_goes_through_the_retrying_reader(self):
        """The pod read uses the class retry helper rather than a bare read."""
        keywords = self._build_keywords([("o2api", "5/5", "Running")])
        keywords.get_not_ready_pod_count(self.NAMESPACE, expected_min=1)
        keywords.pods.get_pods_with_retry.assert_called_once()


if __name__ == "__main__":
    unittest.main()
