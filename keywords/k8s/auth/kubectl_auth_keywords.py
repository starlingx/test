"""Keywords for the two kubectl reads that establish who a token is and what it may do."""

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.auth.object.kubectl_can_i_output import KubectlCanIOutput
from keywords.k8s.auth.object.kubectl_whoami_output import KubectlWhoamiOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlAuthKeywords(K8sBaseKeyword):
    """Read the authenticated identity and whether an operation is permitted.

    Both reads deliberately ignore the command's return code and inspect its text instead, and both
    refuse an answer they cannot interpret rather than defaulting.

    The return code cannot be asserted. ``kubectl auth can-i`` exits non-zero when the answer is
    "no", so a keyword that validated the status would report a correct denial as a command
    failure. But ignoring the status is not enough on its own: kubectl prints its errors to stdout,
    so an unreachable apiserver produces non-empty text that is neither "yes" nor "no". Returning
    "not allowed" for that text would make a denial assertion pass on a cluster where authorization
    was never evaluated, which is the failure this pair exists to prevent. So anything that is not
    a recognisable answer raises.

    ``kubeconfig_path`` matters here more than usual. The framework default is the administrator
    kubeconfig, which is group-readable by ``sys_protected``; a read that does not name the caller's
    own kubeconfig authenticates over X.509 as ``kubernetes-admin`` and says nothing about the token
    under test.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Instance of the class.

        Args:
            ssh_connection (SSHConnection): the session to run kubectl on. For an identity read
                this must be the session belonging to the user being identified.
            kubeconfig_path (str, optional): KUBECONFIG to name explicitly. When None the
                framework default is used, which is the administrator kubeconfig.

        """
        super().__init__(ssh_connection, kubeconfig_path)
        self.ssh_connection = ssh_connection

    def whoami(self) -> KubectlWhoamiOutput:
        """Read the username the apiserver resolved for this session.

        This is the only reliable source for the username. It is the claim named by
        ``oidc-username-claim``, resolved through the identity provider's attribute mapping, and
        the apiserver prefixes it with the issuer URL unless that claim is ``email`` - so the same
        user appears in two different forms depending on configuration.

        ``SelfSubjectReview`` is granted to ``system:authenticated`` by the ``system:basic-user``
        ClusterRole, so this works for a user holding no permissions at all.

        Returns:
            KubectlWhoamiOutput: the resolved identity.

        Raises:
            KeywordException: when the answer is empty or is not a username.

        """
        command = "kubectl auth whoami -o jsonpath='{.status.userInfo.username}'"
        output = self.ssh_connection.send(self.k8s_config.export(command))
        return_code = self.ssh_connection.get_return_code()
        text = "\n".join(output) if isinstance(output, list) else str(output)

        result = KubectlWhoamiOutput(text, return_code)
        if not result.is_valid():
            raise KeywordException(f"could not read the authenticated username. Return code {return_code}, output: {text[:200]}")
        get_logger().log_info(f"the apiserver resolved the username as '{result.get_username()}'")
        return result

    def can_i(self, verb: str, resource: str, namespace: str = None) -> KubectlCanIOutput:
        """Ask the apiserver whether this session may perform an operation.

        Args:
            verb (str): the verb, for example "list".
            resource (str): the resource, for example "secrets".
            namespace (str, optional): the namespace to scope the question to. When None the
                question is asked without a namespace.

        Returns:
            KubectlCanIOutput: the answer.

        Raises:
            KeywordException: when the answer is neither yes nor no, which means the question was
                never evaluated.

        """
        namespace_argument = f" -n {namespace}" if namespace else ""
        # The trailing 'true' keeps the non-zero exit that a "no" answer carries from aborting the
        # command, so the answer itself can be read. The return code is captured separately and
        # used only in the failure message.
        command = f"kubectl auth can-i {verb} {resource}{namespace_argument} 2>&1; true"
        output = self.ssh_connection.send(self.k8s_config.export(command))
        text = "\n".join(output) if isinstance(output, list) else str(output)

        result = KubectlCanIOutput(text)
        if not result.is_answered():
            raise KeywordException(f"'kubectl auth can-i {verb} {resource}{namespace_argument}' did not return an answer, so authorization was " f"never evaluated. Output: {text[:200]}")
        get_logger().log_info(f"can-i {verb} {resource}{namespace_argument}: {'yes' if result.is_allowed() else 'no'}")
        return result
