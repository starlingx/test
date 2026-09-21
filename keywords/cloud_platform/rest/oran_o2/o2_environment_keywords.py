import os

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.applications.o_ran_o2_keywords import APP_NAMESPACE, O2_POD_PREFIX
from keywords.cloud_platform.rest.oran_o2.o2_rest_client import O2RestClient
from keywords.cloud_platform.rest.oran_o2.o2_token_keywords import O2TokenKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class O2EnvironmentKeywords(BaseKeyword):
    """Keywords for checking, and optionally standing up, the O2 IMS environment.

    A usable environment has three parts standing: the client certificate
    material on the test runner, the O2 API pod running on the target, and a
    token issuer that can mint a Bearer token. Verifying them up front reports
    the missing part directly, rather than letting the gap surface later as an
    obscure connection error.

    Two entry points, differing in what they do about a missing part:
    `is_environment_ready` reports it as a boolean, while
    `verify_environment_ready` raises naming the part that is missing.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
        """
        self.ssh_connection = ssh_connection

    def is_environment_ready(self, cert_dir: str) -> bool:
        """Whether the certificate material, O2 API pod and token are all available.

        Args:
            cert_dir (str): Directory holding the client certificate material.

        Returns:
            bool: True when every part of the environment is standing.
        """
        get_logger().log_info("Checking whether the O2 IMS environment is ready")
        not_ready_reason = self._get_not_ready_reason(cert_dir)
        if not_ready_reason:
            get_logger().log_info(f"The O2 IMS environment is not ready: {not_ready_reason}")
            return False
        get_logger().log_info("The O2 IMS environment is ready")
        return True

    def verify_environment_ready(self, cert_dir: str) -> None:
        """Verify the certificate material, O2 API pod and token are all available.

        Args:
            cert_dir (str): Directory holding the client certificate material.

        Raises:
            KeywordException: If any part of the O2 IMS environment is unavailable.
        """
        get_logger().log_info("Verifying the O2 IMS environment is ready")
        not_ready_reason = self._get_not_ready_reason(cert_dir)
        if not_ready_reason:
            raise KeywordException(not_ready_reason)
        get_logger().log_info("The O2 IMS environment is ready")

    def _get_not_ready_reason(self, cert_dir: str) -> str | None:
        """Describe the first part of the environment found missing, if any.

        The single place the three checks are performed, so the predicate and the
        raising form report identically and cannot drift apart.

        Args:
            cert_dir (str): Directory holding the client certificate material.

        Returns:
            str | None: Description of the first problem found, or None when the
                environment is fully standing.
        """
        missing_certificate = self._get_missing_certificate(cert_dir)
        if missing_certificate:
            return f"O2 certificate '{missing_certificate}' not found in '{os.path.expanduser(cert_dir)}'. The O2 IMS environment is not deployed on this runner."

        unhealthy_pod_reason = self._get_unhealthy_pod_reason()
        if unhealthy_pod_reason:
            return unhealthy_pod_reason

        if not self._is_token_obtainable():
            return "Could not obtain an O2 IMS Bearer token. The OAuth2 token issuer is not usable."

        return None

    def _get_missing_certificate(self, cert_dir: str) -> str | None:
        """Return the name of the first absent certificate file, if any.

        Args:
            cert_dir (str): Directory holding the client certificate material.

        Returns:
            str | None: File name of the first certificate found absent, or None
                when all three are present.
        """
        resolved_dir = os.path.expanduser(cert_dir)
        for file_name in (O2RestClient.CLIENT_CERT_FILE, O2RestClient.CLIENT_KEY_FILE, O2RestClient.CA_CERT_FILE):
            if not os.path.isfile(os.path.join(resolved_dir, file_name)):
                return file_name
        return None

    def _get_unhealthy_pod_reason(self) -> str | None:
        """Describe why the O2 API pods are not serving, if they are not.

        Returns:
            str | None: Description of the missing or unhealthy pod, or None when
                every O2 API pod is Running.
        """
        pods_output = KubectlGetPodsKeywords(self.ssh_connection).get_pods(namespace=APP_NAMESPACE)
        o2_pods = pods_output.get_pods_start_with(O2_POD_PREFIX)
        if not o2_pods:
            return f"No '{O2_POD_PREFIX}' pod found in namespace '{APP_NAMESPACE}'. The O2 IMS application is not deployed."
        for pod in o2_pods:
            if pod.get_status() != "Running":
                return f"O2 pod '{pod.get_name()}' is '{pod.get_status()}', not Running. The O2 IMS application is deployed but not healthy."
        return None

    def _is_token_obtainable(self) -> bool:
        """Whether a Bearer token can currently be minted by the token issuer.

        Minting is the only way to establish this, so the attempt's failure is
        caught and reported as False. The specific exception is caught, and only
        to answer the question the method exists to answer.

        Returns:
            bool: True when the issuer returned a token.
        """
        try:
            return bool(O2TokenKeywords(self.ssh_connection).get_token())
        except KeywordException as token_unavailable:
            get_logger().log_info(f"Could not obtain an O2 IMS Bearer token: {token_unavailable}")
            return False
