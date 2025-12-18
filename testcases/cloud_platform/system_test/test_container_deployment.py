from datetime import datetime
from time import time
from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.deployments.kubectl_delete_deployments_keywords import KubectlDeleteDeploymentsKeywords
from keywords.k8s.service.kubectl_delete_service_keywords import KubectlDeleteServiceKeywords
from keywords.k8s.service.kubectl_get_service_keywords import KubectlGetServiceKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.deployments.kubectl_get_deployments_keywords import KubectlGetDeploymentsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.rollout.kubectl_rollout_restart_keywords import KubectlRolloutRestartKeywords
from keywords.system_test.timing_logger import TimingLogger
from keywords.system_test.setup_stress_pods import SetupStressPods
from keywords.system_test.metric_reporter_keywords import MetricReporterKeywords


@mark.p0
def test_deploy_small_benchmark(request):
    """
    Deploys pods for the mixed benchmark type.
    Scale up and down the deployments and measures the time taken for each operation.

    Args:
        request: pytest request object
    """
    deploy_benchmark_pods(request, 'small')


@mark.p0
def test_deploy_benchmark_pods_mixed(request):
    """
    Deploys pods for the mixed benchmark type.
    Scale up and down the deployments and measures the time taken for each operation.

    Args:
        request: pytest request object
    """
    deploy_benchmark_pods(request, 'mixed')


@mark.p0
def test_deploy_benchmark_pods_large(request):
    """
    Deploys pods for the mixed benchmark type.
    Scale up and down the deployments and measures the time taken for each operation.

    Args:
        request: pytest request object
    """
    deploy_benchmark_pods(request, 'large')



def deploy_benchmark_pods(request, benchmark):
    """
    Deploys pods for the selected benchmark type.
    Scale up and down the deployments and measures the time taken for each operation.

    Args:
        request: pytest request object
        benchmark: The type of benchmark to run (mixed, large, small, stress)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = f"{benchmark}-benchmark"
    timing_logger = TimingLogger(f"{benchmark}_container_deployment")

    start_time = datetime.utcnow()
    stress_pods = SetupStressPods(ssh_connection)
    deploy_time, scale_up_time = stress_pods.setup_stress_pods(benchmark=benchmark)

    get_logger().log_test_case_step("Scaling down all deployments and calculating time...")
    scale_down_time = stress_pods.scale_deployments(0, namespace)
    get_logger().log_info(f"Time to scale down pods: {scale_down_time:.2f} seconds")
    end_time = datetime.utcnow()

    get_logger().log_test_case_step("Logging timings for deployment operations...")
    timing_logger.log_timings(deploy_time, scale_up_time, scale_down_time)

    get_logger().log_test_case_step("Running metric reporter to collect system metrics...")
    metric_reporter = MetricReporterKeywords(ssh_connection)
    local_metrics_dir = metric_reporter.run_metric_reporter(start_time, end_time)

    get_logger().log_test_case_step(f"Downloading collectd logs to {local_metrics_dir}")
    sftp_client = ssh_connection.get_sftp_client()
    for filename in sftp_client.listdir("/var/log"):
        if filename.startswith("collectd"):
            remote_file = f"/var/log/{filename}"
            local_file = f"{local_metrics_dir}/{filename}"
            sftp_client.get(remote_file, local_file)
            get_logger().log_info(f"Downloaded {filename}")

    def teardown():
        deployments_output = KubectlGetDeploymentsKeywords(ssh_connection).get_deployments(namespace=namespace)
        deployments_objs = deployments_output.get_deployments()
        for deployment in [dep.get_name() for dep in deployments_objs]:
            get_logger().log_info(f"Deleting deployment {deployment} in namespace {namespace}...")
            KubectlDeleteDeploymentsKeywords(ssh_connection).delete_deployment(deployment, namespace=namespace)
        services_output = KubectlGetServiceKeywords(ssh_connection).get_services(namespace)
        services_obj = services_output.get_services()
        for service in [svc.get_name() for svc in services_obj]:
            get_logger().log_info(f"Deleting service {service} in namespace {namespace}...")
            KubectlDeleteServiceKeywords(ssh_connection).delete_service(service, namespace=namespace)

        KubectlDeleteNamespaceKeywords(ssh_connection).delete_namespace(namespace)

    request.addfinalizer(teardown)


@mark.p0
def test_simultaneous_activities(request):
    """
    Verify how effectively pods can be deleted and launched simultaneously.
    Scale down one namespace while scaling up another and measure timing.

    Args:
        request: pytest request object
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    benchmark = 'mixed'
    prime_ns = f"{benchmark}-benchmark"
    second_ns = "simultaneous-benchmark"
    timing_logger = TimingLogger("simultaneous_activities", 
                                 column_headers=["Initial Scale Up Time (s)", 
                                                 "Simultaneous Scale Time (s)"])

    start_time = datetime.utcnow()
    stress_pods = SetupStressPods(ssh_connection)

    get_logger().log_test_case_step(f"Setting up and scaling primary namespace {prime_ns}")
    deploy_time_group1, initial_scale_time__group1 = stress_pods.setup_stress_pods(benchmark=benchmark, 
                                                                                   namespace=prime_ns)

    get_logger().log_test_case_step(f"Setting up secondary namespace {second_ns}")
    deploy_time_group2 = stress_pods.deploy_stress_pods(benchmark=benchmark, 
                                                        namespace=second_ns)

    get_logger().log_test_case_step(f"Scaling down {prime_ns} and scaling up {second_ns} simultaneously")
    t1 = time()
    stress_pods.scale_deployments(0, prime_ns)
    stress_pods.scale_deployments(stress_pods.scale_factor, second_ns)
    pod_getter = KubectlGetPodsKeywords(ssh_connection)
    pod_getter.wait_for_pods_to_reach_status(expected_status=["Running", "Completed"], namespace=prime_ns)
    pod_getter.wait_for_pods_to_reach_status(expected_status=["Running", "Completed"], namespace=second_ns)
    simultaneous_time = time() - t1
    get_logger().log_info(f"Time for simultaneous operations: {simultaneous_time:.2f}s")

    end_time = datetime.utcnow()
    timing_logger.log_timings(initial_scale_time__group1, simultaneous_time)

    validate_equals(pod_getter.wait_for_all_pods_status(expected_statuses=["Running", "Completed"]), 
                    True, "All pods are healthy")

    get_logger().log_test_case_step("Running metric reporter...")
    metric_reporter = MetricReporterKeywords(ssh_connection)
    metric_reporter.run_metric_reporter(start_time, end_time)

    def teardown():
        for ns in [prime_ns, second_ns]:
            deployments_output = KubectlGetDeploymentsKeywords(ssh_connection).get_deployments(namespace=ns)
            for deployment in [dep.get_name() for dep in deployments_output.get_deployments()]:
                KubectlDeleteDeploymentsKeywords(ssh_connection).delete_deployment(deployment, namespace=ns)
            services_output = KubectlGetServiceKeywords(ssh_connection).get_services(ns)
            for service in [svc.get_name() for svc in services_output.get_services()]:
                KubectlDeleteServiceKeywords(ssh_connection).delete_service(service, namespace=ns)
            KubectlDeleteNamespaceKeywords(ssh_connection).delete_namespace(ns)

    request.addfinalizer(teardown)


@mark.p0
def test_crash_rollout_restart(request):
    """
    Measure time to restart all containers using rollout restart.

    Args:
        request: pytest request object
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    benchmark = 'stress'
    namespace = f"{benchmark}-benchmark"
    timing_logger = TimingLogger("crash_rollout_restart", column_headers=["Rollout Restart Time (s)"])

    start_time = datetime.utcnow()
    stress_pods = SetupStressPods(ssh_connection)

    get_logger().log_test_case_step(f"Setting up {benchmark} benchmark...")
    stress_pods.setup_stress_pods(benchmark=benchmark)

    get_logger().log_test_case_step(f"Scaling {namespace} deployments...")
    stress_pods.scale_deployments(stress_pods.scale_factor, namespace)

    get_logger().log_test_case_step(f"Restarting all deployments in {namespace}...")
    t1 = time()
    rollout_keywords = KubectlRolloutRestartKeywords(ssh_connection)
    rollout_keywords.rollout_restart_deployment(namespace)
    pod_getter = KubectlGetPodsKeywords(ssh_connection)
    pod_getter.wait_for_all_pods_status(expected_statuses=["Running", "Completed"])
    restart_time = time() - t1
    get_logger().log_info(f"Time to rollout restart all pods: {restart_time:.2f}s")

    end_time = datetime.utcnow()
    timing_logger.log_timings(restart_time)

    get_logger().log_test_case_step("Running metric reporter...")
    metric_reporter = MetricReporterKeywords(ssh_connection)
    metric_reporter.run_metric_reporter(start_time, end_time)

    def teardown():
        deployments_output = KubectlGetDeploymentsKeywords(ssh_connection).get_deployments(namespace=namespace)
        for deployment in [dep.get_name() for dep in deployments_output.get_deployments()]:
            KubectlDeleteDeploymentsKeywords(ssh_connection).delete_deployment(deployment, namespace=namespace)
        services_output = KubectlGetServiceKeywords(ssh_connection).get_services(namespace)
        for service in [svc.get_name() for svc in services_output.get_services()]:
            KubectlDeleteServiceKeywords(ssh_connection).delete_service(service, namespace=namespace)
        KubectlDeleteNamespaceKeywords(ssh_connection).delete_namespace(namespace)

    request.addfinalizer(teardown)


@mark.p0
def test_pod_scaling_background(request):
    """
    Measure scale-up/scale-down time with background pods running.

    Args:
        request: pytest request object
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    background_ns = "background-benchmark"

    get_logger().log_test_case_step("Deploying background pods...")
    stress_pods = SetupStressPods(ssh_connection)
    stress_pods.deploy_stress_pods(benchmark="background", namespace=background_ns)
    
    get_logger().log_test_case_step("Running small benchmark with background pods...")
    deploy_benchmark_pods(request, 'small')

    def teardown():
        deployments_output = KubectlGetDeploymentsKeywords(ssh_connection).get_deployments(namespace=background_ns)
        for deployment in [dep.get_name() for dep in deployments_output.get_deployments()]:
            KubectlDeleteDeploymentsKeywords(ssh_connection).delete_deployment(deployment, namespace=background_ns)
        KubectlDeleteNamespaceKeywords(ssh_connection).delete_namespace(background_ns)

    request.addfinalizer(teardown)
