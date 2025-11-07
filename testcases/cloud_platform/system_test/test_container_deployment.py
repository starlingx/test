from time import time
from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from keywords.docker.login.docker_login_keywords import DockerLoginKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.deployments.kubectl_delete_deployments_keywords import KubectlDeleteDeploymentsKeywords
from keywords.k8s.service.kubectl_delete_service_keywords import KubectlDeleteServiceKeywords
from keywords.k8s.service.kubectl_get_service_keywords import KubectlGetServiceKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.deployments.kubectl_scale_deployements_keywords import KubectlScaleDeploymentsKeywords
from keywords.k8s.deployments.kubectl_get_deployments_keywords import KubectlGetDeploymentsKeywords
import os
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from framework.validation.validation import validate_equals

IMAGES = [
    "gcr.io/kubernetes-e2e-test-images/resource-consumer:1.4",
    "alexeiled/stress-ng",
    "centos/tools:latest",
    "datawiseio/fio:latest"
]
SCALE_FACTOR = 30
SERVICES_PATH = "resources/cloud_platform/system_test/pod_scaling/services"
DEPLOYMENTS_PATH = "resources/cloud_platform/system_test/pod_scaling/deployments"


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
    Scale up and down the deployments and mea'sures the time taken for each operation.

    Args:
        request: pytest request object
        benchmark: The type of benchmark to run (mixed, large, small, stress)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    file_keywords = FileKeywords(ssh_connection)
    namespace = f"{benchmark}-benchmark"
    local_services_dir = get_stx_resource_path(SERVICES_PATH)
    remote_services_dir = "/tmp/system_test/services"
    local_deployments_dir = get_stx_resource_path(f"{DEPLOYMENTS_PATH}/{benchmark}")
    remote_deployments_dir = f"/tmp/system_test/deployments/{benchmark}"

    setup_upload_files(local_services_dir, remote_services_dir, local_deployments_dir, remote_deployments_dir)

    get_logger().log_test_case_step(f"Creating namespace '{namespace}'...)")
    ns_creator = KubectlCreateNamespacesKeywords(ssh_connection)
    raw_namespace_obj = KubectlGetNamespacesKeywords(ssh_connection).get_namespaces()
    namespace_objs = raw_namespace_obj.get_namespaces()
    existing_namespaces = [ns.get_name() for ns in namespace_objs]
    if namespace in existing_namespaces:
        ns_destroyer = KubectlDeleteNamespaceKeywords(ssh_connection)
        ns_destroyer.delete_namespace(namespace)
    ns_creator.create_namespaces(namespace)

    setup_docker_registry(ssh_connection, file_keywords, namespace, IMAGES)

    get_logger().log_test_case_step(f"Apply service yaml files...)")
    service_files = file_keywords.get_files_in_dir(remote_services_dir)
    pod_applier = KubectlApplyPodsKeywords(ssh_connection)
    for svc_yaml in service_files:
        pod_applier.apply_from_yaml(f"{remote_services_dir}/{svc_yaml}",namespace=namespace)

    get_logger().log_test_case_step(f"Apply deployment YAMLs and calculate time....")
    pod_getter = KubectlGetPodsKeywords(ssh_connection)
    deployment_files = file_keywords.get_files_in_dir(remote_deployments_dir)
    start_deploy = time()
    for dep_yaml in deployment_files:
        pod_applier.apply_from_yaml(f"{remote_deployments_dir}/{dep_yaml}",namespace=namespace)

    validate_equals(
            pod_getter.wait_for_all_pods_status(expected_statuses=["Running", "Completed"]),
            True,
            'Logs reached expected state')
    deploy_time = time() - start_deploy
    get_logger().log_info(f"Time to deploy pods for the first time: {deploy_time:.2f} seconds")


    get_logger().log_test_case_step("Scaling up all deployments and calculating time...")
    scale_up_time = scale_deployments(ssh_connection, SCALE_FACTOR, namespace)
    get_logger().log_info(f"Time to scale up pods: {scale_up_time:.2f} seconds")

    get_logger().log_test_case_step("Scaling down all deployments tand calculating time...")
    scale_down_time = scale_deployments(ssh_connection, 0, namespace)
    get_logger().log_info(f"Time to scale down pods: {scale_down_time:.2f} seconds")

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
    

def setup_upload_files(
        local_services_dir: str,
        remote_services_dir: str,
        local_deployments_dir: str,
        remote_deployments_dir: str
    ) -> None:
        """
        Uploads necessary files to the controller node for the pod scaling test.

        Args:
            local_services_dir (str): Path to the local directory containing service YAML files.
            remote_services_dir (str): Path to the remote directory where service YAML files will be uploaded.
            local_deployments_dir (str): Path to the local directory containing deployment YAML files.
            remote_deployments_dir (str): Path to the remote directory where deployment YAML files will be uploaded.
        """
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        file_keywords = FileKeywords(ssh_connection)

        get_logger().log_info(f"Uploading service yaml files ...")
        file_keywords.create_directory(remote_services_dir)
        for filename in os.listdir(local_services_dir):
            local_file = os.path.join(local_services_dir, filename)
            remote_file = f"{remote_services_dir}/{filename}"
            if os.path.isfile(local_file):
                file_keywords.upload_file(local_file, remote_file, overwrite=True)

        get_logger().log_info(f"Uploading deployment yaml files ...")
        file_keywords.create_directory(remote_deployments_dir)
        for filename in os.listdir(local_deployments_dir):
            local_file = os.path.join(local_deployments_dir, filename)
            remote_file = f"{remote_deployments_dir}/{filename}"
            if os.path.isfile(local_file):
                file_keywords.upload_file(local_file, remote_file, overwrite=True)

        get_logger().log_info(f"Uploading netdef yaml files ...")
        local_netdef_file = get_stx_resource_path("resources/cloud_platform/system_test/pod_scaling/netdef-data0.yaml")
        file_keywords.upload_file(local_netdef_file, f"{remote_deployments_dir}/netdef-data0.yaml", overwrite=True)



def setup_docker_registry(ssh_connection, file_keywords, namespace, images):

    """
    Sets up the local Docker registry by pulling, tagging, and pushing necessary images.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    docker_config = ConfigurationManager.get_docker_config()
    local_registry = docker_config.get_registry("local_registry")
    registry_url = local_registry.get_registry_url()
    registry_user = local_registry.get_user_name()
    registry_pass = local_registry.get_password()

    get_logger().log_test_case_step(f"Creating secrets for namespace {namespace}")
    secret_creator = KubectlCreateSecretsKeywords(ssh_connection)
    secret_creator.create_secret_for_registry(local_registry, "regcred", namespace=namespace)

    docker_login = DockerLoginKeywords(ssh_connection)
    docker_login.login(registry_user, registry_pass, registry_url)

    docker_images = DockerImagesKeywords(ssh_connection)
    docker_loader = DockerLoadImageKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Pull, tag and push images to {registry_url}")
    for image in images:
        get_logger().log_info(f"Processing image: {image}")
        docker_images.pull_image(image)
        tagged_image = f"{registry_url}/{image}"
        docker_loader.tag_docker_image_for_registry(image, image, local_registry)
        docker_loader.push_docker_image_to_registry(image, local_registry)
        get_logger().log_info(f"Successfully pushed {image} to {tagged_image}")

def scale_deployments(ssh_connection, replicas, namespace):
    """
        Scales all deployments in the specified namespace according to replicas.

    Args:
        ssh_connection: The SSH connection to the target host.
        replicas: The desired number of replicas for each deployment.
        namespace: The Kubernetes namespace containing the deployments.

    returns:
        The time taken to scale the deployments: float
    """
    pod_getter = KubectlGetPodsKeywords(ssh_connection)
    pod_scaler = KubectlScaleDeploymentsKeywords(ssh_connection)
    deployments_obj = KubectlGetDeploymentsKeywords(ssh_connection).get_deployments(namespace=namespace)
    deployments = deployments_obj.get_deployments();
    start_scale = time()
    for deployment in deployments:
        pod_scaler.scale_deployment(deployment.get_name(),
                                    replicas=int(replicas/len(deployments)),
                                    namespace=namespace)
    assert pod_getter.wait_for_all_pods_status(expected_statuses=["Running", "Completed"])
    scale_time = time() - start_scale

    return scale_time


