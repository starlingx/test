"""Keywords for querying Prometheus metrics from a Kubernetes service endpoint."""

import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.service.kubectl_get_service_keywords import KubectlGetServiceKeywords
from keywords.k8s.telemetry.object.prometheus_metrics_output import PrometheusMetricsOutput


class PrometheusMetricsKeywords(K8sBaseKeyword):
    """Keywords for querying Prometheus-format metrics from a Kubernetes service.

    Queries a metrics endpoint exposed by a Kubernetes service via its
    ClusterIP. The service name, namespace, and port are configurable
    so this class works with any Prometheus-compatible exporter.
    """

    def __init__(
        self,
        ssh_connection: SSHConnection,
        service_name: str = "openstack-metrics",
        namespace: str = "openstack",
        port: int = 9180,
    ) -> None:
        """Initialize PrometheusMetricsKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
            service_name (str): Kubernetes service name exposing the metrics endpoint.
            namespace (str): Namespace of the metrics service.
            port (int): Port number of the metrics endpoint.
        """
        super().__init__(ssh_connection)
        self._service_name = service_name
        self._namespace = namespace
        self._port = port

    def scrape_metrics(self, grep_pattern: str = "") -> PrometheusMetricsOutput:
        """Scrape metrics from the service endpoint and return the output object.

        This is the primary keyword for retrieving metrics. Callers should use
        the returned PrometheusMetricsOutput object to perform data queries
        (get_metric_sum, get_metrics_by_prefix, count_metrics_with_prefix, etc.)
        without invoking the CLI multiple times.

        Args:
            grep_pattern (str): Optional grep filter to reduce output size.

        Returns:
            PrometheusMetricsOutput: Parsed metrics output object.
        """
        cluster_ip = self._get_service_cluster_ip()
        if not cluster_ip:
            return PrometheusMetricsOutput([])

        curl_cmd = f"curl -s http://{cluster_ip}:{self._port}/metrics"
        if grep_pattern:
            curl_cmd += f" | grep '{grep_pattern}'"

        output = self.ssh_connection.send(curl_cmd)
        lines = output if isinstance(output, list) else str(output).strip().splitlines()
        clean_lines = [line.strip() for line in lines if line.strip() and "curl" not in line]
        return PrometheusMetricsOutput(clean_lines)

    def measure_scrape_latency(self, samples: int = 5) -> float:
        """Measure the p95 scrape latency of the metrics endpoint.

        Performs multiple scrapes and returns the 95th percentile latency.

        Args:
            samples (int): Number of scrape samples to collect.

        Returns:
            float: p95 scrape latency in seconds.
        """
        latencies = []
        for i in range(samples):
            start = time.time()
            self.scrape_metrics(grep_pattern="openstack_")
            elapsed = time.time() - start
            latencies.append(elapsed)
            get_logger().log_info(f"Scrape {i + 1}/{samples}: {elapsed:.2f}s")

        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95 = latencies[min(p95_index, len(latencies) - 1)]
        get_logger().log_info(f"Scrape latency p95: {p95:.2f}s (from {samples} samples)")
        return p95

    def _get_service_cluster_ip(self) -> str:
        """Retrieve the ClusterIP of the metrics service.

        Returns:
            str: ClusterIP address (with brackets for IPv6), or empty string.
        """
        svc_kw = KubectlGetServiceKeywords(self.ssh_connection)
        service = svc_kw.get_service(self._service_name, self._namespace)
        cluster_ip = service.get_cluster_ip()
        if not cluster_ip:
            get_logger().log_warning(
                f"Service '{self._service_name}' in namespace "
                f"'{self._namespace}' has no ClusterIP"
            )
            return ""
        if ":" in cluster_ip:
            cluster_ip = f"[{cluster_ip}]"
        return cluster_ip
