"""Keywords for checking network connectivity from inside a pod."""

import shlex
from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.network.ip_address_keywords import IPAddressKeywords

CONNECTIVITY_POLLING_SECONDS = 5


class KubectlPodConnectivityKeywords(K8sBaseKeyword):
    """Keywords that run ping or an HTTP GET from inside a pod.

    The commands run with 'kubectl exec', so the pod image must provide 'ping' and
    'wget' (busybox does). ping_from_pod validates the return code; the 'wait_for_'
    keywords poll until the request succeeds or, for blocked traffic, fails.
    """

    def _build_ping_command(self, target_ip: str, count: int) -> str:
        """Build the ping command for a target address.

        Args:
            target_ip (str): The IPv4 or IPv6 address to ping.
            count (int): The number of echo requests.

        Returns:
            str: The ping command, with '-6' added for an IPv6 target.
        """
        ping_args = ["ping", "-c", str(count)]
        if IPAddressKeywords(target_ip).check_ip_version(target_ip) == "IPv6":
            ping_args.append("-6")
        ping_args.append(target_ip)
        return shlex.join(ping_args)

    def _build_http_get_command(self, target_ip: str, port: int, path: str, host_header: Optional[str], request_timeout: int) -> str:
        """Build the wget command for an HTTP GET.

        Args:
            target_ip (str): The IPv4 or IPv6 address to request.
            port (int): The port to request.
            path (str): The URL path (e.g. '/').
            host_header (Optional[str]): The HTTP Host header, for host-based routing.
            request_timeout (int): Seconds before wget gives up on the request.

        Returns:
            str: The wget command.
        """
        wget_args = ["wget", "-qO-", f"--timeout={request_timeout}"]
        if host_header:
            wget_args.extend(["--header", f"Host: {host_header}"])
        wget_args.append(f"http://{IPAddressKeywords(target_ip).get_url_host()}:{port}{path}")
        return shlex.join(wget_args)

    def _get_namespace_options(self, namespace: Optional[str]) -> str:
        """Build the kubectl exec namespace option.

        Args:
            namespace (Optional[str]): The pod namespace, or None for the default namespace.

        Returns:
            str: '-n <namespace>' or an empty string.
        """
        return f"-n {namespace}" if namespace else ""

    def ping_from_pod(self, pod_name: str, target_ip: str, namespace: Optional[str] = None, count: int = 3) -> str:
        """Ping an address from a pod and fail if the ping fails.

        Args:
            pod_name (str): The pod to ping from.
            target_ip (str): The IPv4 or IPv6 address to ping.
            namespace (Optional[str]): The pod namespace.
            count (int): The number of echo requests.

        Returns:
            str: The ping output.
        """
        get_logger().log_info(f"Pinging {target_ip} from pod {pod_name}")
        output = KubectlExecInPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).run_pod_exec_cmd(pod_name, self._build_ping_command(target_ip, count), options=self._get_namespace_options(namespace))
        return "".join(output)

    def wait_for_http_get_from_pod(self, pod_name: str, target_ip: str, port: int = 80, path: str = "/", namespace: Optional[str] = None, host_header: Optional[str] = None, timeout: int = 60) -> str:
        """Retry an HTTP GET from a pod until it succeeds.

        Used right after a Service, route or policy changes, while the data path is still
        being programmed. Every failed attempt is logged with the output it returned.

        Args:
            pod_name (str): The pod to send the request from.
            target_ip (str): The IPv4 or IPv6 address to request.
            port (int): The port to request.
            path (str): The URL path.
            namespace (Optional[str]): The pod namespace.
            host_header (Optional[str]): The HTTP Host header, for host-based routing.
            timeout (int): Seconds to keep retrying.

        Returns:
            str: The response body of the successful request.
        """
        command = self._build_http_get_command(target_ip, port, path, host_header, request_timeout=10)
        exec_keywords = KubectlExecInPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())

        def get_request_return_code() -> ValidationResponse:
            output = "".join(exec_keywords.run_pod_exec_cmd(pod_name, command, options=self._get_namespace_options(namespace), ignore_error=True))
            return_code = self.ssh_connection.get_return_code()
            if return_code != 0:
                get_logger().log_info(f"HTTP GET from pod {pod_name} returned {return_code}: {output}")
            return ValidationResponse(return_code, output)

        return validate_equals_with_retry(get_request_return_code, 0, f"HTTP GET to {target_ip}:{port}{path} from pod {pod_name} succeeds", timeout=timeout, polling_sleep_time=CONNECTIVITY_POLLING_SECONDS)

    def wait_for_http_get_from_pod_to_fail(self, pod_name: str, target_ip: str, port: int = 80, path: str = "/", namespace: Optional[str] = None, host_header: Optional[str] = None, timeout: int = 60) -> str:
        """Retry an HTTP GET from a pod until it fails.

        Used right after a policy that blocks traffic is applied, while it is still
        being programmed.

        Args:
            pod_name (str): The pod to send the request from.
            target_ip (str): The IPv4 or IPv6 address to request.
            port (int): The port to request.
            path (str): The URL path.
            namespace (Optional[str]): The pod namespace.
            host_header (Optional[str]): The HTTP Host header, for host-based routing.
            timeout (int): Seconds to keep retrying.

        Returns:
            str: The wget output of the failed request, for the caller to validate the failure.
        """
        command = self._build_http_get_command(target_ip, port, path, host_header, request_timeout=5)
        exec_keywords = KubectlExecInPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())

        def is_request_failing() -> ValidationResponse:
            output = "".join(exec_keywords.run_pod_exec_cmd(pod_name, command, options=self._get_namespace_options(namespace), ignore_error=True))
            return ValidationResponse(self.ssh_connection.get_return_code() != 0, output)

        return validate_equals_with_retry(is_request_failing, True, f"HTTP GET to {target_ip}:{port}{path} from pod {pod_name} fails", timeout=timeout, polling_sleep_time=CONNECTIVITY_POLLING_SECONDS)
