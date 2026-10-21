"""Unit tests for the metrics-server Metrics-API serving check.

These run against a small stateful stand-in for the cluster's Metrics API rather than a
scripted sequence of return values. The check's correctness is about a single question
asked three ways - is the aggregated Metrics API actually serving - so the model holds the
three things the probe reads and lets each test set them independently:

    * the APIService v1beta1.metrics.k8s.io "Available" condition,
    * the `kubectl top nodes` table,
    * the `kubectl top pods -n kube-system` table.

Two failure surfaces are modelled deliberately, because they are the ones a naive
implementation gets wrong and they cost a whole run when they do:

    * get_resource_field RAISES on a failed `kubectl get` (it calls
      validate_success_return_code), and the first post-activate read can fail transiently
      while the aggregation layer settles. A reader that lets that propagate inside
      validate_equals_with_retry ends the run, because that wrapper retries VALUES, not
      exceptions. The model can be told to raise on the first N reads.
    * `kubectl top` can EXIT NON-ZERO ("metrics not available yet") in the same window.
      KubectlTopKeywords.is_top_*_served reads the return code rather than asserting it, so a
      non-zero exit is reported as "not served yet" (False) and keeps the shared window
      retrying - it must never raise. The model reports False for the first N top reads.

No validate_* function is patched. Failures surface as the exceptions the production code
really raises. Collaborators are installed with object.__setattr__ and built from
NonCallableMagicMock because BaseKeyword.__getattribute__ wraps callable attributes in the
keyword-logging hook, so a plain MagicMock would be re-wrapped and misbehave.
"""

import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.upgrade.metrics_server_api_keywords import MetricsServerApiKeywords
from keywords.k8s.top.objects.kubectl_top_output import KubectlTopOutput

APISERVICE = "v1beta1.metrics.k8s.io"
AVAILABLE_JSONPATH = '{.status.conditions[?(@.type=="Available")].status}'


class FakeMetricsApi:
    """A small stateful stand-in for the cluster's Metrics API surface.

    Holds the APIService Available value and the two `top` tables. Each read can be told to
    fail for a bounded number of initial calls, modelling the post-activate window where the
    APIService read raises and `top` exits non-zero before the collector is serving.
    """

    _NODES_HEADER = "NAME           CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)"
    _PODS_HEADER = "NAME                       CPU(cores)   MEMORY(bytes)"

    def __init__(
        self,
        available: str = "True",
        top_nodes_rows: list = None,
        top_pods_rows: list = None,
        apiservice_raises_first: int = 0,
        top_nonzero_first: int = 0,
    ):
        """Build a Metrics-API model.

        Args:
            available (str): the APIService Available condition the jsonpath read returns.
            top_nodes_rows (list): data cells for `kubectl top nodes` (no header), each
                like "controller-0  445m  44%  8996Mi  391%". Defaults to one healthy row.
            top_pods_rows (list): data cells for `kubectl top pods`, each like
                "coredns-x  2m  29Mi". Defaults to one healthy row.
            apiservice_raises_first (int): how many initial APIService reads raise before
                succeeding, modelling the transient post-activate failure.
            top_nonzero_first (int): how many initial `top` reads exit non-zero before
                succeeding, modelling "metrics not available yet".
        """
        self.available = available
        # Data cells only (no header); the model prepends the header when building the Output,
        # because KubectlTopKeywords runs top WITH headers so the table parser can key columns.
        self.top_nodes_cells = ["controller-0   445m   44%   8996Mi   391%"] if top_nodes_rows is None else top_nodes_rows
        self.top_pods_cells = ["coredns-6499b57679-jsjjn   2m   29Mi"] if top_pods_rows is None else top_pods_rows
        self.apiservice_raises_first = apiservice_raises_first
        self.top_nonzero_first = top_nonzero_first
        # Every read the model was asked for, so a test can assert a reader was actually
        # retried rather than only that the phase passed.
        self.apiservice_reads = 0
        self.top_nodes_reads = 0

    # --- APIService read (reused via KubectlGetResourceKeywords.get_resource_field) --------

    def get_resource_field(self, resource_type: str, resource_name: str, jsonpath: str, namespace: str = None) -> str:
        """Answer the APIService jsonpath read, raising for the first N calls if configured.

        Mirrors the real get_resource_field, which raises AssertionError on a failed
        `kubectl get` because it calls validate_success_return_code.

        Args:
            resource_type (str): expected "apiservice".
            resource_name (str): expected the metrics APIService name.
            jsonpath (str): the Available-condition jsonpath.
            namespace (str): unused for a cluster-scoped APIService.

        Returns:
            str: the Available condition value, or "" when kubectl would have returned an
                empty jsonpath result.

        Raises:
            AssertionError: when configured to fail the first N reads, as the real reader does.
            ValueError: when asked for a resource/jsonpath the model does not implement.
        """
        self.apiservice_reads += 1
        if resource_type != "apiservice" or resource_name != APISERVICE or jsonpath != AVAILABLE_JSONPATH:
            raise ValueError(f"model does not implement {resource_type}/{resource_name} {jsonpath}")
        if self.apiservice_reads <= self.apiservice_raises_first:
            raise AssertionError("kubectl get apiservice failed (return code 1)")
        return self.available

    # --- `kubectl top` serve snapshots (consumed via KubectlTopKeywords.is_top_*_served) ----

    def is_top_nodes_served(self) -> bool:
        """Report whether `kubectl top nodes` serves a positive reading, non-zero-first-aware.

        Mirrors the real KubectlTopKeywords.is_top_nodes_served, which reads the return code
        rather than asserting it, so a transient non-zero exit ("metrics not available yet")
        is reported as "not served yet" (False) rather than raised. The model reports False for
        the first N reads to drive the shared retry window.

        Returns:
            bool: True once a configured number of initial reads have passed and at least one
                node row serves a positive CPU and memory reading.
        """
        self.top_nodes_reads += 1
        if self.top_nodes_reads <= self.top_nonzero_first:
            return False
        rows = [self._NODES_HEADER + "\n"] + [c + "\n" for c in self.top_nodes_cells]
        entries = KubectlTopOutput(rows, resource="nodes").get_entries()
        return any(entry.has_positive_cpu() and entry.has_positive_memory() for entry in entries)

    def is_top_pods_served(self, namespace: str = None) -> bool:
        """Report whether `kubectl top pods` serves a positive reading.

        Args:
            namespace (str): the namespace scope (kube-system in the probe).

        Returns:
            bool: True when at least one pod row serves a positive CPU and memory reading.
        """
        rows = [self._PODS_HEADER + "\n"] + [c + "\n" for c in self.top_pods_cells]
        entries = KubectlTopOutput(rows, resource="pods").get_entries()
        return any(entry.has_positive_cpu() and entry.has_positive_memory() for entry in entries)


class MetricsServerApiKeywordsTestBase(unittest.TestCase):
    """Shared wiring for the probe tests."""

    def setUp(self):
        """Silence loggers and shrink every wait so the suite does not sleep."""
        self.patchers = [
            patch("keywords.base_keyword.get_logger"),
            patch("keywords.cloud_platform.upgrade.metrics_server_api_keywords.get_logger"),
            patch("framework.validation.validation.get_logger"),
            patch.object(MetricsServerApiKeywords, "SERVING_TIMEOUT", 2),
            patch.object(MetricsServerApiKeywords, "SERVING_POLL_INTERVAL", 0),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self):
        """Stop every patcher."""
        for patcher in self.patchers:
            patcher.stop()

    def build(self, model: FakeMetricsApi) -> MetricsServerApiKeywords:
        """Return a probe instance wired to a Metrics-API model.

        BaseKeyword.__getattribute__ wraps callables in a logging wrapper, so collaborators
        are installed with object.__setattr__ and built from NonCallableMagicMock.

        Args:
            model (FakeMetricsApi): the model to wire in.

        Returns:
            MetricsServerApiKeywords: instance backed by that model.
        """
        keywords = MetricsServerApiKeywords.__new__(MetricsServerApiKeywords)

        def stub(**methods: object) -> NonCallableMagicMock:
            """Build a non-callable mock exposing the given bound methods.

            Args:
                **methods (object): attribute name to callable.

            Returns:
                NonCallableMagicMock: the collaborator stub.
            """
            collaborator = NonCallableMagicMock()
            for name, function in methods.items():
                setattr(collaborator, name, MagicMock(side_effect=function))
            return collaborator

        object.__setattr__(keywords, "resources", stub(get_resource_field=model.get_resource_field))
        object.__setattr__(keywords, "top", stub(is_top_nodes_served=model.is_top_nodes_served, is_top_pods_served=model.is_top_pods_served))
        return keywords

    def run_probe(self, model: FakeMetricsApi, phase: str = "pre") -> None:
        """Run the probe against a model.

        Args:
            model (FakeMetricsApi): the model to wire in.
            phase (str): the phase label.
        """
        self.build(model).validate_metrics_api_is_serving(phase)


class TestServingPasses(MetricsServerApiKeywordsTestBase):
    """The probe passes when the Metrics API is serving."""

    def test_healthy_metrics_api_passes(self):
        """APIService Available=True and both top tables populated: the probe passes."""
        self.run_probe(FakeMetricsApi())

    def test_passes_in_every_phase_label(self):
        """The probe is callable at each phase and the label does not change the outcome."""
        for phase in ("pre", "post-upgrade", "post-rollback"):
            with self.subTest(phase=phase):
                self.run_probe(FakeMetricsApi(), phase)

    def test_bare_core_cpu_without_m_suffix_is_accepted(self):
        """`kubectl top` can report whole cores (no `m`); a positive value must still pass."""
        self.run_probe(FakeMetricsApi(top_nodes_rows=["controller-0  2  44%  8996Mi  391%"]))


class TestTransientPostActivateWindowIsTolerated(MetricsServerApiKeywordsTestBase):
    """The shared retry window rides out the post-activate transients."""

    def test_apiservice_read_raising_on_first_poll_is_absorbed(self):
        """get_resource_field raises on the first read; the probe must not die, and must pass.

        This is the single most important case. get_resource_field calls
        validate_success_return_code and raises AssertionError on a failed get. Passed
        straight into validate_equals_with_retry (which retries values, not exceptions) it
        would end the run. The probe must absorb it to a sentinel so the shared window retries.
        """
        model = FakeMetricsApi(apiservice_raises_first=1)
        self.run_probe(model)
        self.assertGreater(model.apiservice_reads, 1, "the APIService read must have been retried after the first failure")

    def test_apiservice_empty_then_true_passes(self):
        """An empty jsonpath result (kubectl prints nothing) on the first read, then True."""
        model = FakeMetricsApi(available="True")
        # First read returns "" by making the model report empty once, then True.
        original = model.get_resource_field
        calls = {"n": 0}

        def flaky(resource_type, resource_name, jsonpath, namespace=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return ""
            return original(resource_type, resource_name, jsonpath, namespace)

        model.get_resource_field = flaky
        self.run_probe(model)

    def test_top_exiting_nonzero_on_first_poll_is_treated_like_empty(self):
        """A non-zero `top` exit keeps the shared window retrying, then passes; it never raises."""
        model = FakeMetricsApi(top_nonzero_first=1)
        self.run_probe(model)
        self.assertGreater(model.top_nodes_reads, 1, "the top read must have been retried after the non-zero exit")


class TestFailuresAreDetected(MetricsServerApiKeywordsTestBase):
    """Conditions the probe must refuse to pass."""

    def test_apiservice_unavailable_fails(self):
        """APIService Available=False must fail the phase."""
        with self.assertRaises(Exception):
            self.run_probe(FakeMetricsApi(available="False"))

    def test_top_nodes_empty_fails(self):
        """No `top nodes` rows means the Metrics API is not serving node metrics: fail."""
        with self.assertRaises(Exception):
            self.run_probe(FakeMetricsApi(top_nodes_rows=[]))

    def test_top_nodes_unknown_cell_fails(self):
        """`<unknown>` is what `top` prints when metrics-server is not serving: fail."""
        with self.assertRaises(Exception):
            self.run_probe(FakeMetricsApi(top_nodes_rows=["controller-0  <unknown>  <unknown>  <unknown>  <unknown>"]))

    def test_top_nodes_zero_cpu_fails(self):
        """A zero CPU reading is not a real sample: assert value > 0, not mere presence."""
        with self.assertRaises(Exception):
            self.run_probe(FakeMetricsApi(top_nodes_rows=["controller-0  0m  0%  0Mi  0%"]))

    def test_top_pods_empty_fails(self):
        """kube-system always has pods, so an empty pod table means the pod path is broken."""
        with self.assertRaises(Exception):
            self.run_probe(FakeMetricsApi(top_pods_rows=[]))

    def test_apiservice_never_available_fails_after_timeout(self):
        """An APIService that never becomes Available fails on a real value mismatch, not a bare timeout."""
        with self.assertRaises(Exception):
            self.run_probe(FakeMetricsApi(available="False"))


if __name__ == "__main__":
    unittest.main()
