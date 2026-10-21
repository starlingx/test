from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.upgrade.objects.metrics_api_readout import MetricsApiReadout
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.top.kubectl_top_keywords import KubectlTopKeywords


class MetricsServerApiKeywords(K8sBaseKeyword):
    """
    This class contains the metrics-server Metrics-API serving check.

    The functional truth for metrics-server is that the aggregated Metrics API
    (metrics.k8s.io/v1beta1) is registered, available, and returns resource samples - a
    stronger claim than the one pod status can support. The v1beta1.metrics.k8s.io APIService
    can report Available=False (an aggregation-layer, serving-cert or kubelet-TLS problem)
    while the metrics-server pod is Running and Ready, so a pod-health check reports the
    application healthy while `kubectl top` and every HPA that depends on it are broken.

    Three reads establish that the API is serving:
        the APIService reports its Available condition True;
        `kubectl top nodes` returns a positive node reading (via KubectlTopKeywords);
        `kubectl top pods -n kube-system` returns a positive pod reading.

    The check is callable at each phase of a platform upgrade rather than once, which is what
    lets one test case assert the same functional truth before the upgrade, after it, and
    after the rollback. It is read-only: it creates nothing, registers no finalizer, and takes
    no pytest request.

    The post-activate transient window - in which the APIService read can fail and `kubectl
    top` can exit non-zero before the collector is serving - is ridden out by a single
    validate_equals_with_retry wait on "all three reads served together", so there is no
    hand-rolled sleep loop here and the wait logs consistently with the rest of the framework.
    The two `top` reads get their stability from KubectlTopKeywords.wait_for_top_*_served,
    which own the retry; the APIService read is taken non-asserting so a transient failed get
    becomes a sentinel the shared window retries rather than an exception that ends the run.
    One shared window rather than three independent waits is deliberate: independent waits
    would let the APIService wait pass and then the `top` wait fail on the same transient lag a
    shared window rides out.

    After the window the hard assertions run once on the settled snapshot, so a genuinely
    broken API fails on a real value mismatch naming what was wrong rather than on a bare
    timeout.
    """

    APISERVICE_NAME = "v1beta1.metrics.k8s.io"
    AVAILABLE_JSONPATH = '{.status.conditions[?(@.type=="Available")].status}'
    KUBE_SYSTEM_NAMESPACE = "kube-system"
    # Matches the pod-readiness window the test case uses around a host reboot: the API is
    # not served the instant the pod reports Ready, and `top` lags the APIService further.
    SERVING_TIMEOUT = 900
    SERVING_POLL_INTERVAL = 15
    # Returned by the APIService read when it could not be completed, so the shared window keeps
    # retrying rather than the read raising out of the wait. Deliberately not a value any
    # assertion accepts.
    UNREADABLE = ""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Instance of the class.

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.

        """
        super().__init__(ssh_connection)
        self.resources = KubectlGetResourceKeywords(ssh_connection)
        self.top = KubectlTopKeywords(ssh_connection)

    def validate_metrics_api_is_serving(self, phase: str) -> None:
        """
        Assert the metrics-server Metrics API is serving at this phase.

        Waits in one bounded window for all three reads to be served, then asserts once:
            the APIService Available condition equals "True";
            `kubectl top nodes` has a parseable, non-zero node reading;
            `kubectl top pods -n kube-system` has a parseable pod reading.

        Args:
            phase (str): where in the upgrade this check is running, used to label every
                assertion so a failure in one phase is distinguishable from the same failure
                in another, for example "pre" or "post-upgrade".

        """
        validate_equals_with_retry(
            lambda: self._read_all().is_fully_served(),
            True,
            f"[{phase}] metrics-server Metrics API is serving (APIService Available and both `kubectl top` reads positive)",
            timeout=self.SERVING_TIMEOUT,
            polling_sleep_time=self.SERVING_POLL_INTERVAL,
        )

        readout = self._read_all()
        validate_equals(readout.get_available(), "True", f"[{phase}] metrics-server APIService {self.APISERVICE_NAME} must report Available=True")
        validate_equals(readout.is_top_nodes_served(), True, f"[{phase}] `kubectl top nodes` must return a parseable, non-zero node reading")
        validate_equals(readout.is_top_pods_served(), True, f"[{phase}] `kubectl top pods -n {self.KUBE_SYSTEM_NAMESPACE}` must return a parseable pod reading")

    def _read_all(self) -> MetricsApiReadout:
        """
        Take one snapshot of the three Metrics-API reads.

        Returns:
            MetricsApiReadout: the APIService Available value and whether each `top` read served.

        """
        return MetricsApiReadout(
            self._read_apiservice_available(),
            self._read_top_nodes_served(),
            self._read_top_pods_served(),
        )

    def _read_apiservice_available(self) -> str:
        """
        Read the APIService Available condition, absorbing a transient read failure.

        get_resource_field raises AssertionError on a failed `kubectl get`, and the first
        post-activate read can fail while the aggregation layer settles. A raise here would end
        the run, so it is absorbed to the UNREADABLE sentinel to keep the shared window
        retrying (validate_*_with_retry retries values, not exceptions).

        Returns:
            str: the Available condition value ("True" when serving), or the UNREADABLE
                sentinel when the read could not be completed.

        """
        try:
            return self.resources.get_resource_field("apiservice", self.APISERVICE_NAME, self.AVAILABLE_JSONPATH)
        except AssertionError as read_error:
            get_logger().log_info(f"Could not read the metrics APIService, will retry: {read_error}")
            return self.UNREADABLE

    def _read_top_nodes_served(self) -> bool:
        """
        Report whether `kubectl top nodes` currently serves a positive node reading.

        One non-asserting snapshot. The retrying is done by the shared window in
        validate_metrics_api_is_serving, so this read must not block; it reports False when the
        Metrics API is not serving yet rather than waiting.

        Returns:
            bool: True when at least one node serves a positive CPU and memory reading.

        """
        return self.top.is_top_nodes_served()

    def _read_top_pods_served(self) -> bool:
        """
        Report whether `kubectl top pods -n kube-system` currently serves a positive reading.

        kube-system always has pods, so a served Metrics API returns at least one pod with a
        positive CPU and memory reading. One non-asserting snapshot, for the same
        shared-window reason as the node read.

        Returns:
            bool: True when at least one pod serves a positive CPU and memory reading.

        """
        return self.top.is_top_pods_served(namespace=self.KUBE_SYSTEM_NAMESPACE)
