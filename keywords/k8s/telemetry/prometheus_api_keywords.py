"""Keywords for querying the Prometheus HTTP API via Kubernetes Service."""

import time
from typing import List, Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.telemetry.object.prometheus_api_query_output import PrometheusApiQueryOutput
from keywords.k8s.telemetry.object.prometheus_targets_output import PrometheusTargetsOutput

DEFAULT_SERVICE_NAME = "kube-prometheus-stack-prometheus"
DEFAULT_PROMQL = "prometheus_tsdb_head_samples_appended_total"


class PrometheusApiKeywords(BaseKeyword):
    """Keywords for querying the Prometheus HTTP API via Kubernetes Service.

    Queries the Prometheus API through the ClusterIP service DNS name,
    which is how real applications (AODH, Heat, etc.) access Prometheus.
    This avoids needing to know or target specific pod names.
    """

    def __init__(self, ssh_connection: SSHConnection, namespace: str, service_name: str = DEFAULT_SERVICE_NAME, port: int = 9090) -> None:
        """Initialize PrometheusApiKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
            namespace (str): Namespace where Prometheus runs.
            service_name (str): Prometheus ClusterIP service name.
            port (int): Prometheus HTTP API port. Defaults to 9090.
        """
        self.ssh_connection = ssh_connection
        self._namespace = namespace
        self._service_name = service_name
        self._port = port
        self._base_url = f"http://{service_name}.{namespace}.svc.cluster.local:{port}"

    def query_instant(self, promql: str) -> PrometheusApiQueryOutput:
        """Execute an instant PromQL query via the Prometheus service.

        Args:
            promql (str): PromQL expression to query.

        Returns:
            PrometheusApiQueryOutput: Parsed query response object.
                Returns empty result if the service is temporarily unreachable.
        """
        url = f"{self._base_url}/api/v1/query?query={promql}"
        cmd = f"curl -s '{url}'"
        output = self.ssh_connection.send(cmd)
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_info(f"Prometheus service not reachable (curl rc={rc}), returning empty result")
            return PrometheusApiQueryOutput("")
        output_text = "\n".join(output) if isinstance(output, list) else output
        result = PrometheusApiQueryOutput(output_text)
        get_logger().log_info(f"Prometheus instant query '{promql}': has_data={result.has_data()}")
        return result

    def query_range(self, promql: str, start: int, end: int, step: int = 15) -> PrometheusApiQueryOutput:
        """Execute a range PromQL query via the Prometheus service.

        Args:
            promql (str): PromQL expression to query.
            start (int): Start Unix timestamp.
            end (int): End Unix timestamp.
            step (int): Step interval in seconds. Defaults to 15.

        Returns:
            PrometheusApiQueryOutput: Parsed query response object.
                Returns empty result if the service is temporarily unreachable.
        """
        url = f"{self._base_url}/api/v1/query_range?query={promql}&start={start}&end={end}&step={step}"
        cmd = f"curl -s '{url}'"
        output = self.ssh_connection.send(cmd)
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_info(f"Prometheus service not reachable (curl rc={rc}), returning empty result")
            return PrometheusApiQueryOutput("")
        output_text = "\n".join(output) if isinstance(output, list) else output
        result = PrometheusApiQueryOutput(output_text)
        get_logger().log_info(f"Prometheus range query '{promql}' [{start}-{end}]: has_range_data={result.has_range_data()}")
        return result

    def query_targets(self) -> PrometheusTargetsOutput:
        """Query the Prometheus /api/v1/targets endpoint via the service.

        Returns:
            PrometheusTargetsOutput: Parsed targets response object.
                Returns empty/failed result if the service is temporarily unreachable.
        """
        url = f"{self._base_url}/api/v1/targets"
        cmd = f"curl -s '{url}'"
        output = self.ssh_connection.send(cmd)
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_info(f"Prometheus service not reachable (curl rc={rc}), returning empty result")
            return PrometheusTargetsOutput("")
        output_text = "\n".join(output) if isinstance(output, list) else output
        result = PrometheusTargetsOutput(output_text)
        get_logger().log_info(f"Prometheus targets via service: {result}")
        return result

    def wait_for_healthy_targets(self, job_prefixes: List[str], timeout: int = 900, poll_interval: int = 30) -> PrometheusTargetsOutput:
        """Poll until all specified job prefixes have healthy scrape targets.

        Queries /api/v1/targets via the service and checks that every job
        prefix has at least one active target with health=up.

        Args:
            job_prefixes (List[str]): Job name prefixes that must each have
                at least one healthy target.
            timeout (int): Maximum seconds to wait. Defaults to 900.
            poll_interval (int): Seconds between polls. Defaults to 30.

        Returns:
            PrometheusTargetsOutput: The targets response confirming all jobs healthy.

        Raises:
            TimeoutError: If not all job prefixes have healthy targets within timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self.query_targets()
            if result.is_failed():
                get_logger().log_info("Targets query failed via service, retrying")
            elif result.has_all_healthy_jobs(job_prefixes):
                get_logger().log_info(f"All required targets healthy: {job_prefixes}")
                return result
            else:
                healthy = result.get_healthy_jobs()
                get_logger().log_info(f"Healthy jobs: {healthy} - waiting for: {job_prefixes}")
            get_logger().log_info(f"Waiting for healthy targets {job_prefixes}... retrying in {poll_interval}s")
            time.sleep(poll_interval)

        raise TimeoutError(f"Required targets {job_prefixes} did not become healthy within {timeout}s")

    def wait_for_data_in_tsdb(self, promql: str = DEFAULT_PROMQL, timeout: int = 900, poll_interval: int = 20) -> PrometheusApiQueryOutput:
        """Poll until metric data appears in TSDB via the Prometheus service.

        Args:
            promql (str): PromQL expression to poll for. Defaults to
                prometheus_tsdb_head_samples_appended_total.
            timeout (int): Maximum seconds to wait. Defaults to 900.
            poll_interval (int): Seconds between polls. Defaults to 20.

        Returns:
            PrometheusApiQueryOutput: The query response containing data.

        Raises:
            TimeoutError: If no data appears in TSDB within the timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self.query_instant(promql)
            if result.has_data():
                get_logger().log_info(f"Metric '{promql}' confirmed in TSDB via service")
                return result
            get_logger().log_info(f"Waiting for metric '{promql}' in TSDB... retrying in {poll_interval}s")
            time.sleep(poll_interval)

        raise TimeoutError(f"Metric '{promql}' did not appear in TSDB within {timeout}s")

    def wait_for_data_spanning_timestamps(self, start_timestamp: int, after_timestamp: int, promql: str = DEFAULT_PROMQL, timeout: int = 900, poll_interval: int = 20) -> PrometheusApiQueryOutput:
        """Poll until TSDB contains data both before and after a given timestamp.

        Queries a time range via the service to confirm that existing data
        is preserved and that new data points have appeared after the
        specified timestamp.

        Args:
            start_timestamp (int): Unix timestamp to start the range query from.
            after_timestamp (int): Unix timestamp that must appear in the results,
                confirming new data has been ingested after this point.
            promql (str): PromQL expression to query. Defaults to
                prometheus_tsdb_head_samples_appended_total.
            timeout (int): Maximum seconds to wait. Defaults to 900.
            poll_interval (int): Seconds between polls. Defaults to 20.

        Returns:
            PrometheusApiQueryOutput: The last query response (contains spanning data).

        Raises:
            TimeoutError: If data spanning both timestamps is not confirmed within timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self.query_range(
                promql,
                start=start_timestamp,
                end=int(time.time()),
            )
            if result.has_range_data() and result.contains_timestamp(after_timestamp):
                get_logger().log_info(f"Data confirmed spanning timestamps [{start_timestamp}, {after_timestamp}]")
                return result
            if result.has_range_data():
                get_logger().log_info(f"Historical data present but no data after timestamp {after_timestamp} yet")
            else:
                get_logger().log_info("No data in TSDB yet")
            get_logger().log_info(f"Retrying in {poll_interval}s...")
            time.sleep(poll_interval)

        raise TimeoutError(f"Data spanning timestamps [{start_timestamp}, {after_timestamp}] not confirmed within {timeout}s")
