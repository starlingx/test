"""Unit tests for KubectlTopKeywords serve-aware reads and retry waits.

The retry stability for `kubectl top` lives in this keyword (not in its callers): right
after 'software deploy activate' the command can exit non-zero or print `<unknown>` cells
while the Metrics API settles. The two behaviours under test are:

    * is_top_*_served reads the SSH return code rather than asserting it, so a non-zero exit
      becomes a False a caller can poll on - never an exception. This is what lets the serve
      check sit inside validate_equals_with_retry (which retries values, not exceptions).
    * wait_for_top_*_served polls is_top_*_served through the framework retry helper until a
      positive reading is served, then returns the parsed table.

A fake SSH connection models the command output and the return code it would leave behind,
and can be told to exit non-zero for a bounded number of initial reads. The k8s_config
export is stubbed to a pass-through so the command string reaches the fake unchanged.
Collaborators are installed with object.__setattr__ because BaseKeyword.__getattribute__
wraps callable attributes in the keyword-logging hook.
"""

import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.k8s.top.kubectl_top_keywords import KubectlTopKeywords

_NODES_HEADER = "NAME           CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)"
_PODS_HEADER = "NAME                       CPU(cores)   MEMORY(bytes)"
_HEALTHY_NODE_ROW = "controller-0   445m   44%   8996Mi   391%"
_HEALTHY_POD_ROW = "coredns-6499b57679-jsjjn   2m   29Mi"


class FakeTopSsh:
    """A fake SSH connection that answers `kubectl top` and records its return code.

    Holds the node and pod tables and a count of how many initial reads should exit non-zero,
    modelling the post-activate window. get_return_code reports what the last send left.
    """

    def __init__(self, node_rows: list = None, pod_rows: list = None, nonzero_first: int = 0):
        """Build the fake.

        Args:
            node_rows (list): data cells for `kubectl top nodes` (no header). Defaults to one
                healthy row.
            pod_rows (list): data cells for `kubectl top pods` (no header). Defaults to one
                healthy row.
            nonzero_first (int): how many initial reads exit non-zero before succeeding.
        """
        self.node_rows = [_HEALTHY_NODE_ROW] if node_rows is None else node_rows
        self.pod_rows = [_HEALTHY_POD_ROW] if pod_rows is None else pod_rows
        self.nonzero_first = nonzero_first
        self.reads = 0
        self._return_code = 0

    def send(self, command: str, command_timeout: int = None, reconnect_timeout: int = None, get_pty: bool = False) -> list:
        """Answer a `kubectl top` command, setting the return code it would leave.

        Args:
            command (str): the command sent.
            command_timeout (int): unused.
            reconnect_timeout (int): unused.
            get_pty (bool): unused.

        Returns:
            list: the output lines, including the header row.
        """
        self.reads += 1
        if self.reads <= self.nonzero_first:
            self._return_code = 1
            return []
        self._return_code = 0
        if "pods" in command:
            return [_PODS_HEADER + "\n"] + [row + "\n" for row in self.pod_rows]
        return [_NODES_HEADER + "\n"] + [row + "\n" for row in self.node_rows]

    def get_return_code(self) -> int:
        """Return the code the last send left.

        Returns:
            int: the last return code.
        """
        return self._return_code


class KubectlTopKeywordsTestBase(unittest.TestCase):
    """Shared wiring for the KubectlTopKeywords tests."""

    def setUp(self):
        """Silence loggers and shrink the wait so the suite does not sleep."""
        self.patchers = [
            patch("keywords.k8s.top.kubectl_top_keywords.get_logger"),
            patch("keywords.base_keyword.get_logger"),
            patch("framework.validation.validation.get_logger"),
            patch.object(KubectlTopKeywords, "SERVED_TIMEOUT", 2),
            patch.object(KubectlTopKeywords, "SERVED_POLL_INTERVAL", 0),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self):
        """Stop every patcher."""
        for patcher in self.patchers:
            patcher.stop()

    def build(self, ssh: FakeTopSsh) -> KubectlTopKeywords:
        """Return a KubectlTopKeywords wired to a fake SSH connection.

        Args:
            ssh (FakeTopSsh): the fake connection to wire in.

        Returns:
            KubectlTopKeywords: instance backed by that connection.
        """
        keywords = KubectlTopKeywords.__new__(KubectlTopKeywords)
        k8s_config = NonCallableMagicMock()
        k8s_config.export = MagicMock(side_effect=lambda command: command)
        object.__setattr__(keywords, "ssh_connection", ssh)
        object.__setattr__(keywords, "k8s_config", k8s_config)
        return keywords


class TestServeSnapshot(KubectlTopKeywordsTestBase):
    """is_top_*_served reports serving without raising."""

    def test_healthy_nodes_served(self):
        """A healthy node table serves a positive reading."""
        self.assertTrue(self.build(FakeTopSsh()).is_top_nodes_served())

    def test_healthy_pods_served(self):
        """A healthy pod table serves a positive reading."""
        self.assertTrue(self.build(FakeTopSsh()).is_top_pods_served(namespace="kube-system"))

    def test_nonzero_exit_is_not_served_and_does_not_raise(self):
        """A non-zero `top` exit reports not-served rather than raising."""
        ssh = FakeTopSsh(nonzero_first=1)
        self.assertFalse(self.build(ssh).is_top_nodes_served())

    def test_unknown_cells_are_not_served(self):
        """`<unknown>` cells (metrics not served) report not-served."""
        ssh = FakeTopSsh(node_rows=["controller-0   <unknown>   <unknown>   <unknown>   <unknown>"])
        self.assertFalse(self.build(ssh).is_top_nodes_served())

    def test_zero_reading_is_not_served(self):
        """A zero reading is not a positive sample."""
        ssh = FakeTopSsh(node_rows=["controller-0   0m   0%   0Mi   0%"])
        self.assertFalse(self.build(ssh).is_top_nodes_served())

    def test_empty_table_is_not_served(self):
        """A header-only table serves nothing."""
        ssh = FakeTopSsh(node_rows=[])
        self.assertFalse(self.build(ssh).is_top_nodes_served())


class TestWaitRetriesTransient(KubectlTopKeywordsTestBase):
    """wait_for_top_*_served rides out the post-activate transient and returns the table."""

    def test_wait_nodes_retries_after_nonzero_then_returns(self):
        """A non-zero first read is retried; the wait returns the parsed node table."""
        ssh = FakeTopSsh(nonzero_first=1)
        output = self.build(ssh).wait_for_top_nodes_served()
        self.assertGreater(ssh.reads, 1, "the wait must have retried after the non-zero exit")
        self.assertEqual(output.get_entry("controller-0").get_cpu(), "445m")

    def test_wait_pods_returns_parsed_table(self):
        """The pod wait returns the parsed pod table once served."""
        output = self.build(FakeTopSsh()).wait_for_top_pods_served(namespace="kube-system")
        self.assertEqual(output.get_entry("coredns-6499b57679-jsjjn").get_cpu(), "2m")

    def test_wait_nodes_times_out_when_never_served(self):
        """A table that never serves fails the wait rather than returning."""
        ssh = FakeTopSsh(node_rows=["controller-0   <unknown>   <unknown>   <unknown>   <unknown>"])
        with self.assertRaises(Exception):
            self.build(ssh).wait_for_top_nodes_served()


if __name__ == "__main__":
    unittest.main()
