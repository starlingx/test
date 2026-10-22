"""Regression checks for shared Prometheus acquisition behavior."""

import unittest
from unittest.mock import NonCallableMagicMock, patch

from keywords.k8s.telemetry import prometheus_api_keywords as api
from keywords.k8s.telemetry import prometheus_metrics_keywords as metrics


class PrometheusCollectionTest(unittest.TestCase):
    """Exercise controller-side HTTP transport without a live cluster."""

    def test_replica_query_uses_exact_pod_and_encoded_expression(self) -> None:
        """Independent replica queries must not traverse the service load balancer."""
        ssh = NonCallableMagicMock()
        with patch("keywords.base_keyword.get_logger"), patch.object(api, "KubectlExecInPodsKeywords") as executor:
            executor.return_value.run_pod_exec_cmd.return_value = '{"status":"success","data":{"result":[]}}'
            output = api.PrometheusApiKeywords(ssh, "monitoring").query_instant_from_pod('up{job="sample"}', "server-1")
        args, kwargs = executor.return_value.run_pod_exec_cmd.call_args
        self.assertEqual(args[0], "server-1")
        self.assertIn("localhost:9090/api/v1/query?query=up%7Bjob%3D%22sample%22%7D", args[1])
        self.assertEqual(kwargs["options"], "-n monitoring -c prometheus")
        self.assertEqual(output.get_series(), [])

    def test_failed_scrape_rejects_http_error_body(self) -> None:
        """An HTTP error page must not be accepted as collected samples."""
        ssh = NonCallableMagicMock()
        ssh.send.return_value = "unavailable"
        ssh.get_return_code.return_value = 22
        with patch("keywords.base_keyword.get_logger"), patch("keywords.k8s.k8s_base_keyword.K8sConfigExporter"):
            with self.assertRaisesRegex(RuntimeError, "Metrics scrape failed"):
                metrics.PrometheusMetricsKeywords(ssh).scrape_metrics_from_url("http://sample:9100/metrics", timeout=10, fail_on_error=True)
        self.assertIn("curl -fsS --max-time 10", ssh.send.call_args.args[0])

    def test_existing_scrape_defaults_remain_compatible(self) -> None:
        """Default scrapes preserve the permissive existing command contract."""
        ssh = NonCallableMagicMock()
        ssh.send.return_value = ["sample 4"]
        with patch("keywords.base_keyword.get_logger"), patch("keywords.k8s.k8s_base_keyword.K8sConfigExporter"):
            result = metrics.PrometheusMetricsKeywords(ssh).scrape_metrics_from_url("http://sample:9100/metrics")
        self.assertEqual(ssh.send.call_args.args[0], "curl -s http://sample:9100/metrics")
        self.assertEqual(result.get_metric_sum("sample"), 4)

    def test_invalid_download_bounds_fail_before_transport(self) -> None:
        """Malformed numeric command arguments cannot reach SSH."""
        ssh = NonCallableMagicMock()
        with patch("keywords.base_keyword.get_logger"):
            keyword = api.PrometheusApiKeywords(ssh, "monitoring")
            for start, end in ((3, 2), (True, 2), ("1", 2)):
                with self.subTest(start=start), self.assertRaises(ValueError):
                    keyword.query_range_download("sample", start, end)
        ssh.send.assert_not_called()
        ssh.get_sftp_client.assert_not_called()
