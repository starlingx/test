from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.top.objects.kubectl_top_output import KubectlTopOutput


class KubectlTopKeywords(K8sBaseKeyword):
    """
    Keywords for the `kubectl top` command (resource usage from the Metrics API).
    """

    # `kubectl top` does not serve the instant the metrics-server pod reports Ready: the
    # aggregation layer and serving certificate settle after that, and right after
    # 'software deploy activate' the command can exit non-zero ("metrics not available yet").
    # These bound the wait the serve-aware reads poll over.
    SERVED_TIMEOUT = 900
    SERVED_POLL_INTERVAL = 15

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: Optional[str] = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
            kubeconfig_path (Optional[str]): Custom KUBECONFIG path. If None, uses default.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_top_nodes(self) -> KubectlTopOutput:
        """
        Run `kubectl top nodes` and return the parsed node resource usage.

        Returns:
            KubectlTopOutput: parsed per-node CPU and memory usage.

        Raises:
            AssertionError: if the kubectl command fails. A failed top (for example while the
                Metrics API is still starting) raises; callers that need to tolerate that
                transient use wait_for_top_nodes_served instead.
        """
        output = self.ssh_connection.send(self.k8s_config.export("kubectl top nodes"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlTopOutput(output, resource="nodes")

    def get_top_pods(self, namespace: Optional[str] = None) -> KubectlTopOutput:
        """
        Run `kubectl top pods` and return the parsed pod resource usage.

        Args:
            namespace (Optional[str]): namespace to scope the read to; when None, the current
                namespace is used.

        Returns:
            KubectlTopOutput: parsed per-pod CPU and memory usage.

        Raises:
            AssertionError: if the kubectl command fails. Callers that need to tolerate the
                post-activate transient use wait_for_top_pods_served instead.
        """
        output = self.ssh_connection.send(self._build_top_pods_command(namespace))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlTopOutput(output, resource="pods")

    def is_top_nodes_served(self) -> bool:
        """
        Report whether `kubectl top nodes` currently serves a positive node reading, without raising.

        One non-asserting snapshot: the return code is read with get_return_code rather than
        asserted, so a transient non-zero exit ("metrics not available yet") becomes a False a
        caller can poll on rather than an exception. A caller that wants to wait uses
        wait_for_top_nodes_served; a caller running its own poll window uses this.

        Returns:
            bool: True when the command exited zero and at least one node served a positive CPU
                and memory reading.
        """
        return self._read_top_served("kubectl top nodes", resource="nodes")

    def is_top_pods_served(self, namespace: Optional[str] = None) -> bool:
        """
        Report whether `kubectl top pods` currently serves a positive pod reading, without raising.

        Same non-asserting snapshot contract as is_top_nodes_served.

        Args:
            namespace (Optional[str]): namespace to scope the read to; when None, the current
                namespace is used.

        Returns:
            bool: True when the command exited zero and at least one pod served a positive CPU
                and memory reading.
        """
        return self._read_top_served(self._build_top_pods_command(namespace), resource="pods")

    def wait_for_top_nodes_served(self, timeout: Optional[int] = None, polling_sleep_time: Optional[int] = None) -> KubectlTopOutput:
        """
        Poll `kubectl top nodes` until it serves a parseable, non-zero node reading.

        The stability lives here rather than in the caller: right after 'software deploy
        activate' the command can exit non-zero or return an empty/`<unknown>` table while the
        Metrics API settles. Both are treated as "not served yet" and keep the window polling,
        so a caller never has to wrap the read in a retry loop or a try/except.

        Args:
            timeout (Optional[int]): seconds to keep polling before giving up; defaults to
                SERVED_TIMEOUT.
            polling_sleep_time (Optional[int]): seconds to wait between polls; defaults to
                SERVED_POLL_INTERVAL.

        Returns:
            KubectlTopOutput: the parsed node table once at least one node serves a positive
                CPU and memory reading.

        Raises:
            TimeoutError: when no node serves a positive reading within the timeout.
        """
        validate_equals_with_retry(
            self.is_top_nodes_served,
            True,
            "`kubectl top nodes` serves a positive node reading",
            timeout=self.SERVED_TIMEOUT if timeout is None else timeout,
            polling_sleep_time=self.SERVED_POLL_INTERVAL if polling_sleep_time is None else polling_sleep_time,
        )
        return self.get_top_nodes()

    def wait_for_top_pods_served(self, namespace: Optional[str] = None, timeout: Optional[int] = None, polling_sleep_time: Optional[int] = None) -> KubectlTopOutput:
        """
        Poll `kubectl top pods` until it serves a parseable, non-zero pod reading.

        Same stability contract as wait_for_top_nodes_served: a transient non-zero exit or an
        empty/`<unknown>` table keeps the window polling instead of raising.

        Args:
            namespace (Optional[str]): namespace to scope the read to; when None, the current
                namespace is used.
            timeout (Optional[int]): seconds to keep polling before giving up; defaults to
                SERVED_TIMEOUT.
            polling_sleep_time (Optional[int]): seconds to wait between polls; defaults to
                SERVED_POLL_INTERVAL.

        Returns:
            KubectlTopOutput: the parsed pod table once at least one pod serves a positive CPU
                and memory reading.

        Raises:
            TimeoutError: when no pod serves a positive reading within the timeout.
        """
        validate_equals_with_retry(
            lambda: self.is_top_pods_served(namespace=namespace),
            True,
            f"`{self._build_top_pods_command(namespace)}` serves a positive pod reading",
            timeout=self.SERVED_TIMEOUT if timeout is None else timeout,
            polling_sleep_time=self.SERVED_POLL_INTERVAL if polling_sleep_time is None else polling_sleep_time,
        )
        return self.get_top_pods(namespace=namespace)

    def _build_top_pods_command(self, namespace: Optional[str]) -> str:
        """
        Build the `kubectl top pods` command, scoped to a namespace when given.

        Args:
            namespace (Optional[str]): namespace to scope the read to; when None, omitted.

        Returns:
            str: the kubectl top pods command.
        """
        command = "kubectl top pods"
        if namespace:
            command += f" -n {namespace}"
        return command

    def _read_top_served(self, command: str, resource: str) -> bool:
        """
        Report whether one `kubectl top` read served a positive reading, without raising.

        The return code is read with get_return_code rather than asserted, so a transient
        non-zero exit ("metrics not available yet") becomes a False the polling helper retries
        on, rather than an exception it cannot catch.

        Args:
            command (str): the kubectl top command to run.
            resource (str): the resource the table describes, "nodes" or "pods".

        Returns:
            bool: True when the command exited zero and at least one row served a positive CPU
                and memory reading.
        """
        output = self.ssh_connection.send(self.k8s_config.export(command))
        if self.ssh_connection.get_return_code() != 0:
            get_logger().log_info(f"`{command}` exited non-zero; the Metrics API is not serving yet")
            return False
        entries = KubectlTopOutput(output, resource=resource).get_entries()
        return any(entry.has_positive_cpu() and entry.has_positive_memory() for entry in entries)
