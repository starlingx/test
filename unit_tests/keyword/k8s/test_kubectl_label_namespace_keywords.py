"""Unit tests for the namespace label keyword.

Cover the command the keyword builds and the fact that it asserts the write's own return code. The
assertion is the point of the keyword: a label that silently failed to apply produces a failure much
further away from its cause, in whatever depended on the label being set.
"""

import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.k8s.namespace.kubectl_label_namespace_keywords import KubectlLabelNamespaceKeywords


class TestKubectlLabelNamespaceKeywords(unittest.TestCase):
    """Test suite for KubectlLabelNamespaceKeywords."""

    NAMESPACE = "stxtest-istio-pre"

    def setUp(self):
        """Silence the BaseKeyword logging wrapper and the keyword's own logger."""
        self.patchers = [
            patch("keywords.base_keyword.get_logger"),
            patch("keywords.k8s.namespace.kubectl_label_namespace_keywords.get_logger"),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self):
        """Stop the logger patchers."""
        for patcher in self.patchers:
            patcher.stop()

    def _build_keywords(self, return_code: int = 0) -> KubectlLabelNamespaceKeywords:
        """Return a keyword instance whose SSH connection reports the given return code.

        BaseKeyword.__getattribute__ wraps every callable attribute in a logging wrapper, so
        collaborators are installed with object.__setattr__ and built from NonCallableMagicMock to
        keep that wrapper from replacing them.

        Args:
            return_code (int): the return code the fake SSH connection reports. Defaults to 0.

        Returns:
            KubectlLabelNamespaceKeywords: instance with a stubbed SSH connection.
        """
        keywords = KubectlLabelNamespaceKeywords.__new__(KubectlLabelNamespaceKeywords)
        ssh = NonCallableMagicMock()
        ssh.send = MagicMock(return_value=[""])
        ssh.get_return_code = MagicMock(return_value=return_code)
        k8s_config = NonCallableMagicMock()
        k8s_config.export = MagicMock(side_effect=lambda command: command)
        object.__setattr__(keywords, "ssh_connection", ssh)
        object.__setattr__(keywords, "k8s_config", k8s_config)
        return keywords

    def test_label_namespace_sends_the_expected_command(self):
        """The label write targets a namespace and overwrites an existing value."""
        keywords = self._build_keywords()
        keywords.label_namespace(self.NAMESPACE, "istio-injection", "enabled")
        keywords.ssh_connection.send.assert_called_once_with(f"kubectl label namespace {self.NAMESPACE} istio-injection=enabled --overwrite")

    def test_label_namespace_asserts_the_return_code(self):
        """A non-zero return code from the label write fails rather than being ignored."""
        keywords = self._build_keywords(return_code=1)
        with self.assertRaises(Exception):
            keywords.label_namespace(self.NAMESPACE, "istio-injection", "enabled")

    def test_remove_label_sends_the_expected_command(self):
        """Removing a label uses the trailing-dash form and names no value."""
        keywords = self._build_keywords()
        keywords.remove_label(self.NAMESPACE, "istio-injection")
        keywords.ssh_connection.send.assert_called_once_with(f"kubectl label namespace {self.NAMESPACE} istio-injection-")

    def test_remove_label_asserts_the_return_code(self):
        """A non-zero return code from the label removal fails rather than being ignored."""
        keywords = self._build_keywords(return_code=1)
        with self.assertRaises(Exception):
            keywords.remove_label(self.NAMESPACE, "istio-injection")

    def test_it_labels_a_namespace_and_not_a_node(self):
        """Guard against the keyword being copied from the node equivalent without editing the verb.

        The node keyword it is modelled on is otherwise identical, and 'kubectl label node' against a
        namespace name fails on the lab rather than at review time.
        """
        keywords = self._build_keywords()
        keywords.label_namespace(self.NAMESPACE, "istio-injection", "enabled")
        sent = keywords.ssh_connection.send.call_args[0][0]
        self.assertIn("label namespace", sent)
        self.assertNotIn("label node", sent)


if __name__ == "__main__":
    unittest.main()
