"""Keywords for running an iperf3 client inside a pod."""

import shlex
from typing import Optional

from framework.logging.automation_logger import get_logger
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.object.iperf3_client_output import Iperf3ClientOutput

IPERF3_DEFAULT_PORT = 5201


class KubectlIperf3Keywords(K8sBaseKeyword):
    """Keywords for running an iperf3 client from a pod whose image provides iperf3."""

    def run_iperf3_client_from_pod(self, pod_name: str, server_ip: str, namespace: Optional[str] = None, port: int = IPERF3_DEFAULT_PORT, duration_seconds: int = 10) -> Iperf3ClientOutput:
        """Run an iperf3 client from a pod against an iperf3 server and fail if the run fails.

        Args:
            pod_name (str): The pod to run the client in.
            server_ip (str): The IPv4 or IPv6 address of the iperf3 server.
            namespace (Optional[str]): The pod namespace.
            port (int): The iperf3 server port.
            duration_seconds (int): The test length in seconds.

        Returns:
            Iperf3ClientOutput: The parsed iperf3 report.
        """
        get_logger().log_info(f"Running iperf3 from pod {pod_name} to {server_ip}:{port} for {duration_seconds}s")
        command = shlex.join(["iperf3", "-c", server_ip, "-p", str(port), "-t", str(duration_seconds), "-J"])
        options = f"-n {namespace}" if namespace else ""
        output = KubectlExecInPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).run_pod_exec_cmd(pod_name, command, options=options)
        return Iperf3ClientOutput(output)
