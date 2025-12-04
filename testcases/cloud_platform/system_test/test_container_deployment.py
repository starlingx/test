from datetime import datetime
from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.deployments.kubectl_delete_deployments_keywords import KubectlDeleteDeploymentsKeywords
from keywords.k8s.service.kubectl_delete_service_keywords import KubectlDeleteServiceKeywords
from keywords.k8s.service.kubectl_get_service_keywords import KubectlGetServiceKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.deployments.kubectl_get_deployments_keywords import KubectlGetDeploymentsKeywords
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


