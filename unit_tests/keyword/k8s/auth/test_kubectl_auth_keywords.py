"""Unit tests for the kubectl auth keywords.

These cover the two reads that decide whether an OIDC token is real and what it may do, so the
cases that matter are the ones where a broken cluster could look like a successful answer.
"""

import unittest
from unittest.mock import patch

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.auth.kubectl_auth_keywords import KubectlAuthKeywords

USER_KUBECONFIG = "$HOME/.kube/config"
# The prefixed form the apiserver produces when oidc-username-claim is not email. It contains
# colons and slashes, which is what makes naive parsing fail.
PREFIXED_USER = "https://192.0.2.10:30556/dex#oidcuser"


class FakeConnection:
    """A stand-in for SSHConnection that returns canned output and a chosen return code."""

    def __init__(self, output: str = "", return_code: int = 0):
        """Build a connection that answers with the given output and status.

        Args:
            output (str): what the command prints, on stdout, as kubectl does for its errors.
            return_code (int): the exit status to report.

        """
        self.output = output
        self.return_code = return_code
        self.commands = []

    def send(self, command: str, **kwargs) -> list:
        """Record the command and return the canned output.

        Args:
            command (str): the command to run.
            **kwargs: ignored; present because the real signature accepts timeouts.

        Returns:
            list: output lines.

        """
        self.commands.append(command)
        return self.output.splitlines()

    def get_return_code(self) -> int:
        """Return the chosen exit status.

        Returns:
            int: the exit status.

        """
        return self.return_code


class KubectlAuthKeywordsTest(unittest.TestCase):
    """Cover whoami and can-i, including the failure shapes that must not read as answers."""

    def setUp(self):
        """Silence the loggers the keywords write to."""
        for target in ("keywords.base_keyword.get_logger", "keywords.k8s.auth.kubectl_auth_keywords.get_logger"):
            patcher = patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_whoami_returns_the_username_the_apiserver_resolved(self):
        """The username must come from the apiserver, not be derived from the login name."""
        connection = FakeConnection(output=PREFIXED_USER, return_code=0)

        result = KubectlAuthKeywords(connection, kubeconfig_path=USER_KUBECONFIG).whoami()

        self.assertEqual(result.get_username(), PREFIXED_USER)

    def test_whoami_uses_the_kubeconfig_it_was_given(self):
        """The read must name the caller's kubeconfig.

        The framework default is the administrator kubeconfig, which the OIDC test user can read,
        so a read that does not name its own kubeconfig authenticates over X.509 and proves
        nothing about the token.
        """
        connection = FakeConnection(output=PREFIXED_USER, return_code=0)

        KubectlAuthKeywords(connection, kubeconfig_path=USER_KUBECONFIG).whoami()

        self.assertTrue(
            any(USER_KUBECONFIG in command for command in connection.commands),
            f"the kubeconfig was not named in {connection.commands}",
        )

    def test_whoami_refuses_an_unreachable_apiserver(self):
        """A kubectl that cannot reach a server prints to stdout and exits non-zero.

        That text is non-empty and is not a username, so a reader that only checked the text would
        carry "connection to the server was refused" forward as an identity.
        """
        connection = FakeConnection(
            output="error: connection to the server localhost:8080 was refused - did you specify the right host or port?",
            return_code=1,
        )

        with self.assertRaises(KeywordException):
            KubectlAuthKeywords(connection, kubeconfig_path=USER_KUBECONFIG).whoami()

    def test_whoami_refuses_empty_output(self):
        """An empty answer must fail rather than yield an empty username.

        An empty username would compare equal to another empty username in a later phase, so a
        claim mapping that broke across an upgrade would read as unchanged.
        """
        connection = FakeConnection(output="", return_code=0)

        with self.assertRaises(KeywordException):
            KubectlAuthKeywords(connection, kubeconfig_path=USER_KUBECONFIG).whoami()

    def test_can_i_reports_an_allowed_operation(self):
        """A permitted operation answers yes."""
        connection = FakeConnection(output="yes", return_code=0)

        result = KubectlAuthKeywords(connection, kubeconfig_path=USER_KUBECONFIG).can_i("list", "pods", namespace="kube-system")

        self.assertTrue(result.is_allowed())
        self.assertFalse(result.is_denied())

    def test_can_i_reports_a_denied_operation_despite_a_non_zero_exit(self):
        """can-i exits non-zero when the answer is no, so the return code must not be asserted.

        A keyword that validated the return code would read a correct denial as a command failure.
        """
        connection = FakeConnection(output="no", return_code=1)

        result = KubectlAuthKeywords(connection, kubeconfig_path=USER_KUBECONFIG).can_i("list", "secrets", namespace="kube-system")

        self.assertTrue(result.is_denied())
        self.assertFalse(result.is_allowed())

    def test_can_i_reports_a_denial_that_carries_a_reason(self):
        """kubectl answers "no - <reason>", which an exact-equality check would miss."""
        connection = FakeConnection(output="no - no RBAC policy matched", return_code=1)

        result = KubectlAuthKeywords(connection, kubeconfig_path=USER_KUBECONFIG).can_i("list", "secrets", namespace="kube-system")

        self.assertTrue(result.is_denied())

    def test_can_i_refuses_an_answer_that_is_neither_yes_nor_no(self):
        """An unreachable cluster must fail, not be reported as a denial.

        This is the fail-open this keyword exists to prevent. If a dead cluster were reported as
        denied, the precondition that proves a denial is meaningful would pass on a cluster where
        nothing can be evaluated at all.
        """
        connection = FakeConnection(
            output="error: You must be logged in to the server (Unauthorized)",
            return_code=1,
        )

        with self.assertRaises(KeywordException):
            KubectlAuthKeywords(connection, kubeconfig_path=USER_KUBECONFIG).can_i("list", "secrets", namespace="kube-system")


if __name__ == "__main__":
    unittest.main()
