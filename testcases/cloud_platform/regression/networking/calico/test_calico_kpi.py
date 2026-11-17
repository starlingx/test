"""Calico operator KPI tests: CPU and memory usage at steady state and under load."""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_less_than_or_equal
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_ensure_applied_keywords import SystemApplicationEnsureAppliedKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_run_pod_keywords import KubectlRunPodKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.top.kubectl_top_keywords import KubectlTopKeywords

NETWORKING_IMAGES_MANIFEST = "networking-tests"
IPERF3_IMAGE_NAME = "networkstatic/iperf3"
IPERF3_IMAGE_TAG = "multiarch"
REGISTRY_LOCAL_SECRET = "registry-local-secret"
CALICO_SYSTEM_NAMESPACE = "calico-system"
TIGERA_OPERATOR_NAMESPACE = "tigera-operator"
TEST_NAMESPACE = "default"
POD_RUNNING_TIMEOUT_SECONDS = 120

# Steady-state KPI sampling: number of samples and the spacing between them.
STEADY_STATE_SAMPLE_COUNT = 8
STEADY_STATE_SAMPLE_INTERVAL_SECONDS = 60
# Provisional CPU upper bounds, set well above the observed usage (single-digit to low tens of
# millicores per Calico pod) so the checks catch runaway usage rather than normal variation.
# Replace them with the reference baselines once those are defined.
STEADY_STATE_CPU_LIMIT_MILLICORES = 500
PEAK_CPU_UNDER_LOAD_LIMIT_MILLICORES = 1000
# Memory leak check: the average of the last samples may grow by at most this percentage over
# the average of the first samples, ignoring growth smaller than the absolute floor so a pod with
# a tiny baseline cannot trip the percentage on a few Mi.
MEMORY_TREND_WINDOW_SAMPLES = 3
MEMORY_GROWTH_LIMIT_PERCENT = 50.0
MEMORY_GROWTH_FLOOR_MEBIBYTES = 20
# Load test: iperf3 run length, how often CPU is sampled while it runs, and the extra time
# allowed for the client pod to finish after the run.
IPERF3_DURATION_SECONDS = 300
IPERF3_PARALLEL_STREAMS = 4
LOAD_SAMPLE_INTERVAL_SECONDS = 30
LOAD_COMPLETION_MARGIN_SECONDS = 60
# Post-load: how far above its baseline a pod's CPU may stay, and how long it has to settle.
POST_LOAD_CPU_TOLERANCE_MILLICORES = 100
POST_LOAD_SETTLE_TIMEOUT_SECONDS = 120


def ensure_metrics_server() -> None:
    """Make sure the metrics-server application is applied, which 'kubectl top' needs."""
    get_logger().log_setup_step("Make sure the metrics-server application is applied")
    app_config = ConfigurationManager.get_app_config()
    app_name = app_config.get_metric_server_app_name()
    SystemApplicationEnsureAppliedKeywords(LabConnectionKeywords().get_active_controller_ssh()).ensure_application_applied(app_name, f"{app_config.get_base_application_path()}{app_name}*.tgz")


def get_restart_counts(ssh_connection: SSHConnection) -> dict[str, int]:
    """Get the container restart count of every calico-system pod.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        dict[str, int]: Pod name mapped to its total container restart count.
    """
    return {pod.get_name(): pod.get_restart_count() for pod in KubectlGetPodsKeywords(ssh_connection).get_pods_json(namespace=CALICO_SYSTEM_NAMESPACE).get_pods()}


@mark.p2
def test_cpu_usage_steady_state():
    """Verify the CPU usage of every Calico pod stays below the limit at steady state.

    Preconditions:
        - Calico operator is installed and healthy
        - No workload churn on the system

    Setup:
        - Make sure the metrics-server application is applied

    Test Steps:
        1. Sample 'kubectl top pods' of calico-system and tigera-operator 8 times, 1 minute apart
        2. Verify every pod appears in every sample and its average CPU is below the limit

    Teardown:
        - None
    """
    ensure_metrics_server()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step(f"Sample 'kubectl top pods' of calico-system and tigera-operator {STEADY_STATE_SAMPLE_COUNT} times, {STEADY_STATE_SAMPLE_INTERVAL_SECONDS}s apart")
    samples = KubectlTopKeywords(ssh_connection).sample_top_pods([CALICO_SYSTEM_NAMESPACE, TIGERA_OPERATOR_NAMESPACE], STEADY_STATE_SAMPLE_COUNT, STEADY_STATE_SAMPLE_INTERVAL_SECONDS)

    get_logger().log_test_case_step("Verify every pod appears in every sample and its average CPU is below the limit")
    validate_equals(samples.get_pods_missing_samples(), [], "Every Calico pod appears in every sample (a missing sample means the pod restarted)")
    for pod_name in samples.get_pod_names():
        cpu_values = samples.get_cpu_millicores(pod_name)
        average_cpu = sum(cpu_values) / len(cpu_values)
        get_logger().log_info(f"Pod {pod_name}: average CPU {average_cpu:.1f}m, maximum {max(cpu_values)}m")
        validate_less_than_or_equal(average_cpu, STEADY_STATE_CPU_LIMIT_MILLICORES, f"Pod {pod_name} average CPU {average_cpu:.1f}m is at most {STEADY_STATE_CPU_LIMIT_MILLICORES}m")


@mark.p2
def test_memory_usage_steady_state():
    """Verify the memory usage of every Calico pod shows no continuous growth at steady state.

    Preconditions:
        - Calico operator is installed and healthy
        - No workload churn on the system

    Setup:
        - Make sure the metrics-server application is applied

    Test Steps:
        1. Sample 'kubectl top pods' of calico-system and tigera-operator 8 times, 1 minute apart
        2. Verify every pod appears in every sample and its memory does not grow past the limit

    Teardown:
        - None
    """
    ensure_metrics_server()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step(f"Sample 'kubectl top pods' of calico-system and tigera-operator {STEADY_STATE_SAMPLE_COUNT} times, {STEADY_STATE_SAMPLE_INTERVAL_SECONDS}s apart")
    samples = KubectlTopKeywords(ssh_connection).sample_top_pods([CALICO_SYSTEM_NAMESPACE, TIGERA_OPERATOR_NAMESPACE], STEADY_STATE_SAMPLE_COUNT, STEADY_STATE_SAMPLE_INTERVAL_SECONDS)

    get_logger().log_test_case_step("Verify every pod appears in every sample and its memory does not grow past the limit")
    validate_equals(samples.get_pods_missing_samples(), [], "Every Calico pod appears in every sample (a missing sample means the pod restarted)")
    for pod_name in samples.get_pod_names():
        memory_values = samples.get_memory_mebibytes(pod_name)
        first_samples_average = sum(memory_values[:MEMORY_TREND_WINDOW_SAMPLES]) / MEMORY_TREND_WINDOW_SAMPLES
        last_samples_average = sum(memory_values[-MEMORY_TREND_WINDOW_SAMPLES:]) / MEMORY_TREND_WINDOW_SAMPLES
        growth_mebibytes = last_samples_average - first_samples_average
        growth_percent = growth_mebibytes / first_samples_average * 100 if first_samples_average else 0.0
        get_logger().log_info(f"Pod {pod_name}: first {MEMORY_TREND_WINDOW_SAMPLES} samples {first_samples_average:.1f}Mi, last {MEMORY_TREND_WINDOW_SAMPLES} samples {last_samples_average:.1f}Mi, growth {growth_mebibytes:.1f}Mi ({growth_percent:.1f}%)")
        # Growth fails only when it exceeds both the percentage limit and the absolute floor.
        allowed_growth_mebibytes = max(MEMORY_GROWTH_FLOOR_MEBIBYTES, first_samples_average * MEMORY_GROWTH_LIMIT_PERCENT / 100)
        validate_less_than_or_equal(growth_mebibytes, allowed_growth_mebibytes, f"Pod {pod_name} memory growth {growth_mebibytes:.1f}Mi is at most {allowed_growth_mebibytes:.1f}Mi ({MEMORY_GROWTH_LIMIT_PERCENT}% of {first_samples_average:.1f}Mi, at least {MEMORY_GROWTH_FLOOR_MEBIBYTES}Mi)")


@mark.p2
def test_resource_usage_under_load(request: FixtureRequest):
    """Verify the Calico pods stay within bounds and do not restart under sustained network load.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Make sure the metrics-server application is applied
        - Sync the iperf3 test image and copy the local registry pull secret
        - Start an iperf3 server pod

    Test Steps:
        1. Record the baseline CPU and the restart count of every calico-system pod
        2. Run an iperf3 client for 5 minutes and sample the calico-system CPU while it runs
        3. Verify the peak CPU is below the limit and no calico-system pod restarted
        4. Verify every calico-system pod returns near its baseline CPU after the load

    Teardown:
        - Delete the iperf3 client and server pods
        - Remove the iperf3 test image from the controller
    """
    ensure_metrics_server()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step(f"Sync the {IPERF3_IMAGE_NAME}:{IPERF3_IMAGE_TAG} test image to the local registry")
    docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)

    def cleanup_iperf3_image() -> None:
        get_logger().log_teardown_step(f"Remove the {IPERF3_IMAGE_NAME}:{IPERF3_IMAGE_TAG} test image from the controller")
        docker_sync_keywords.remove_image_from_manifest(IPERF3_IMAGE_NAME, IPERF3_IMAGE_TAG, NETWORKING_IMAGES_MANIFEST)

    request.addfinalizer(cleanup_iperf3_image)
    iperf3_image = docker_sync_keywords.sync_image_from_manifest(IPERF3_IMAGE_NAME, IPERF3_IMAGE_TAG, NETWORKING_IMAGES_MANIFEST)
    get_logger().log_setup_step(f"Copy the local registry pull secret to the {TEST_NAMESPACE} namespace")
    KubectlCreateSecretsKeywords(ssh_connection).copy_secret_between_namespaces(REGISTRY_LOCAL_SECRET, CALICO_SYSTEM_NAMESPACE, TEST_NAMESPACE)

    delete_pods_keywords = KubectlDeletePodsKeywords(ssh_connection)

    def cleanup_iperf3_pods() -> None:
        get_logger().log_teardown_step("Delete the iperf3 client and server pods")
        delete_pods_keywords.cleanup_pod("iperf-client", namespace=TEST_NAMESPACE)
        delete_pods_keywords.cleanup_pod("iperf-server", namespace=TEST_NAMESPACE)

    request.addfinalizer(cleanup_iperf3_pods)

    get_logger().log_setup_step("Start an iperf3 server pod")
    pod_overrides = {"spec": {"imagePullSecrets": [{"name": REGISTRY_LOCAL_SECRET}]}}
    run_pod_keywords = KubectlRunPodKeywords(ssh_connection)
    get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    run_pod_keywords.run_pod("iperf-server", iperf3_image, namespace=TEST_NAMESPACE, overrides=pod_overrides, command=["iperf3", "-s"])
    get_pods_keywords.wait_for_pod_status("iperf-server", "Running", namespace=TEST_NAMESPACE, timeout=POD_RUNNING_TIMEOUT_SECONDS)
    server_ip = get_pods_keywords.get_pods(namespace=TEST_NAMESPACE).get_pod("iperf-server").get_ip()

    get_logger().log_test_case_step("Record the baseline CPU and the restart count of every calico-system pod")
    top_keywords = KubectlTopKeywords(ssh_connection)
    baseline_cpu = {entry.get_name(): entry.get_cpu_millicores() for entry in top_keywords.wait_for_top_pods_served(CALICO_SYSTEM_NAMESPACE).get_entries()}
    restart_counts_before = get_restart_counts(ssh_connection)
    get_logger().log_info(f"Baseline CPU (millicores): {baseline_cpu}; restart counts: {restart_counts_before}")

    get_logger().log_test_case_step(f"Run an iperf3 client for {IPERF3_DURATION_SECONDS}s and sample the calico-system CPU while it runs")
    run_pod_keywords.run_pod("iperf-client", iperf3_image, namespace=TEST_NAMESPACE, overrides=pod_overrides, command=["iperf3", "-c", server_ip, "-t", str(IPERF3_DURATION_SECONDS), "-P", str(IPERF3_PARALLEL_STREAMS)])
    peak_cpu: dict[str, int] = {}

    def sample_peak_cpu_and_get_client_phase() -> str:
        for entry in top_keywords.wait_for_top_pods_served(CALICO_SYSTEM_NAMESPACE).get_entries():
            peak_cpu[entry.get_name()] = max(peak_cpu.get(entry.get_name(), 0), entry.get_cpu_millicores())
        return get_pods_keywords.get_pods_json(namespace=TEST_NAMESPACE).get_pod("iperf-client").get_status()

    validate_equals_with_retry(sample_peak_cpu_and_get_client_phase, "Succeeded", "The iperf3 client completes while the calico-system CPU is sampled", timeout=IPERF3_DURATION_SECONDS + LOAD_COMPLETION_MARGIN_SECONDS, polling_sleep_time=LOAD_SAMPLE_INTERVAL_SECONDS, failure_values=["Failed"])
    get_logger().log_info(f"Peak CPU under load (millicores): {peak_cpu}")

    get_logger().log_test_case_step("Verify the peak CPU is below the limit and no calico-system pod restarted")
    for pod_name, cpu in peak_cpu.items():
        validate_less_than_or_equal(cpu, PEAK_CPU_UNDER_LOAD_LIMIT_MILLICORES, f"Pod {pod_name} peak CPU {cpu}m under load is at most {PEAK_CPU_UNDER_LOAD_LIMIT_MILLICORES}m")
    # A restart, including an OOMKilled one, increments the container restart count.
    validate_equals(get_restart_counts(ssh_connection), restart_counts_before, "No calico-system pod restarted during the load (restart counts unchanged)")

    get_logger().log_test_case_step("Verify every calico-system pod returns near its baseline CPU after the load")

    def get_pods_above_baseline_tolerance() -> list[str]:
        post_load_cpu = {entry.get_name(): entry.get_cpu_millicores() for entry in top_keywords.wait_for_top_pods_served(CALICO_SYSTEM_NAMESPACE).get_entries()}
        return sorted(f"{pod_name}: {cpu}m (baseline {baseline_cpu.get(pod_name)}m)" for pod_name, cpu in post_load_cpu.items() if cpu > baseline_cpu.get(pod_name, 0) + POST_LOAD_CPU_TOLERANCE_MILLICORES)

    validate_equals_with_retry(get_pods_above_baseline_tolerance, [], f"Every calico-system pod CPU returns to within {POST_LOAD_CPU_TOLERANCE_MILLICORES}m of its baseline", timeout=POST_LOAD_SETTLE_TIMEOUT_SECONDS, polling_sleep_time=LOAD_SAMPLE_INTERVAL_SECONDS)
