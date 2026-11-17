"""Bounded Deployment rollout synchronization."""

from shlex import quote

from keywords.k8s.k8s_base_keyword import K8sBaseKeyword

ROLLOUT_COMMAND_GRACE = 20


class KubectlRolloutStatusKeywords(K8sBaseKeyword):
    """Wait for controller-reported Deployment rollout completion."""

    def wait_for_deployment_rollout(self, namespace: str, deployment: str, timeout: int = 300) -> None:
        """Wait for kubectl rollout status with an explicit command bound.

        Args:
            namespace (str): Deployment namespace.
            deployment (str): Exact Deployment name.
            timeout (int): Positive maximum rollout wait in seconds.
        """
        if type(timeout) is not int or timeout <= 0:
            raise ValueError("Rollout timeout must be a positive integer")
        command = f"kubectl rollout status deployment/{quote(deployment)} -n {quote(namespace)} --timeout={timeout}s"
        self.ssh_connection.send(self.k8s_config.export(command), command_timeout=timeout + ROLLOUT_COMMAND_GRACE)
        self.validate_success_return_code(self.ssh_connection)
