import os
from time import time
from typing import Any, List, Tuple

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from keywords.docker.login.docker_login_keywords import DockerLoginKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.deployments.kubectl_get_deployments_keywords import KubectlGetDeploymentsKeywords
from keywords.k8s.deployments.kubectl_scale_deployements_keywords import KubectlScaleDeploymentsKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords


class SetupStressPods:
    """
    Class for setting up stress pods for benchmark testing.

    This class provides functionality to deploy, scale, and manage stress pods
    for various benchmark types including mixed, large, small, and stress tests.
    """

    def __init__(self, ssh_connection: Any) -> None:
        """
        Initialize the SetupStressPods class.

        Args:
            ssh_connection (Any): SSH connection to the target system
        """
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)
        self.images = ["gcr.io/kubernetes-e2e-test-images/resource-consumer:1.4", "alexeiled/stress-ng", "centos/tools:latest", "datawiseio/fio:latest"]
        self.scale_factor = 30
        self.services_path = "resources/cloud_platform/system_test/pod_scaling/services"
        self.deployments_path = "resources/cloud_platform/system_test/pod_scaling/deployments"

    def setup_stress_pods(self, benchmark: str) -> Tuple[float, float]:
        """
        Set up stress pods for benchmark testing.

        Args:
            benchmark (str): The benchmark type to set up

        Returns:
            Tuple[float, float]: Tuple of deploy time and scale up time in seconds
        """
        namespace = f"{benchmark}-benchmark"
        local_services_dir = get_stx_resource_path(self.services_path)
        remote_services_dir = "/tmp/system_test/services"
        local_deployments_dir = get_stx_resource_path(f"{self.deployments_path}/{benchmark}")
        remote_deployments_dir = f"/tmp/system_test/deployments/{benchmark}"

        self._setup_upload_files(local_services_dir, remote_services_dir, local_deployments_dir, remote_deployments_dir)

        get_logger().log_info(f"Creating namespace '{namespace}'...")
        ns_creator = KubectlCreateNamespacesKeywords(self.ssh_connection)
        raw_namespace_obj = KubectlGetNamespacesKeywords(self.ssh_connection).get_namespaces()
        namespace_objs = raw_namespace_obj.get_namespaces()
        existing_namespaces = [ns.get_name() for ns in namespace_objs]
        if namespace in existing_namespaces:
            ns_destroyer = KubectlDeleteNamespaceKeywords(self.ssh_connection)
            ns_destroyer.delete_namespace(namespace)
        ns_creator.create_namespaces(namespace)

        self._setup_docker_registry(namespace, self.images)

        get_logger().log_info("Apply services YAMLs....")
        service_files = self.file_keywords.get_files_in_dir(remote_services_dir)
        pod_applier = KubectlApplyPodsKeywords(self.ssh_connection)
        for svc_yaml in service_files:
            pod_applier.apply_from_yaml(f"{remote_services_dir}/{svc_yaml}", namespace=namespace)

        get_logger().log_info("Apply deployment YAMLs and calculate time....")
        pod_getter = KubectlGetPodsKeywords(self.ssh_connection)
        deployment_files = self.file_keywords.get_files_in_dir(remote_deployments_dir)
        start_deploy = time()
        for dep_yaml in deployment_files:
            pod_applier.apply_from_yaml(f"{remote_deployments_dir}/{dep_yaml}", namespace=namespace)
            validate_equals(pod_getter.wait_for_all_pods_status(expected_statuses=["Running", "Completed"]), True, "Logs reached expected state")
        deploy_time = time() - start_deploy
        get_logger().log_info(f"Time to deploy pods for the first time: {deploy_time:.2f} seconds")

        get_logger().log_info("Scaling up all deployments and calculating time...")
        scale_up_time = self.scale_deployments(self.scale_factor, namespace)
        get_logger().log_info(f"Time to scale up pods: {scale_up_time:.2f} seconds")

        return deploy_time, scale_up_time

    def _setup_upload_files(self, local_services_dir: str, remote_services_dir: str, local_deployments_dir: str, remote_deployments_dir: str) -> None:
        """
        Upload necessary files to the controller node for the pod scaling test.

        Args:
            local_services_dir (str): Path to the local directory containing service YAML files
            remote_services_dir (str): Path to the remote directory where service YAML files will be uploaded
            local_deployments_dir (str): Path to the local directory containing deployment YAML files
            remote_deployments_dir (str): Path to the remote directory where deployment YAML files will be uploaded
        """
        get_logger().log_info("Uploading service yaml files ...")
        self.file_keywords.create_directory(remote_services_dir)
        for filename in os.listdir(local_services_dir):
            local_file = os.path.join(local_services_dir, filename)
            remote_file = f"{remote_services_dir}/{filename}"
            if os.path.isfile(local_file):
                self.file_keywords.upload_file(local_file, remote_file, overwrite=True)

        get_logger().log_info("Uploading deployment yaml files ...")
        self.file_keywords.create_directory(remote_deployments_dir)
        for filename in os.listdir(local_deployments_dir):
            local_file = os.path.join(local_deployments_dir, filename)
            remote_file = f"{remote_deployments_dir}/{filename}"
            if os.path.isfile(local_file):
                self.file_keywords.upload_file(local_file, remote_file, overwrite=True)

        get_logger().log_info("Uploading netdef yaml files ...")
        local_netdef_file = get_stx_resource_path("resources/cloud_platform/system_test/pod_scaling/netdef-data0.yaml")
        self.file_keywords.upload_file(local_netdef_file, f"{remote_deployments_dir}/netdef-data0.yaml", overwrite=True)

    def _setup_docker_registry(self, namespace: str, images: List[str]) -> None:
        """
        Set up the local Docker registry by pulling, tagging, and pushing necessary images.

        Args:
            namespace (str): Kubernetes namespace
            images (List[str]): List of Docker images to process
        """
        docker_config = ConfigurationManager.get_docker_config()
        local_registry = docker_config.get_local_registry()
        registry_url = local_registry.get_registry_url()
        registry_user = local_registry.get_user_name()
        registry_pass = local_registry.get_password()

        get_logger().log_test_case_step(f"Creating secrets for namespace {namespace}")
        secret_creator = KubectlCreateSecretsKeywords(self.ssh_connection)
        secret_creator.create_secret_for_registry(local_registry, "regcred", namespace=namespace)

        docker_login = DockerLoginKeywords(self.ssh_connection)
        docker_login.login(registry_user, registry_pass, registry_url)

        docker_images = DockerImagesKeywords(self.ssh_connection)
        docker_loader = DockerLoadImageKeywords(self.ssh_connection)

        get_logger().log_test_case_step(f"Pull, tag and push images to {registry_url}")
        for image in images:
            get_logger().log_info(f"Processing image: {image}")
            docker_images.pull_image(image)
            tagged_image = f"{registry_url}/{image}"
            docker_loader.tag_docker_image_for_registry(image, image, local_registry)
            docker_loader.push_docker_image_to_registry(image, local_registry)
            get_logger().log_info(f"Successfully pushed {image} to {tagged_image}")

    def scale_deployments(self, replicas: int, namespace: str) -> float:
        """
        Scale all deployments in the specified namespace according to replicas.

        Args:
            replicas (int): The desired number of replicas for each deployment
            namespace (str): The Kubernetes namespace containing the deployments

        Returns:
            float: The time taken to scale the deployments
        """
        pod_getter = KubectlGetPodsKeywords(self.ssh_connection)
        pod_scaler = KubectlScaleDeploymentsKeywords(self.ssh_connection)
        deployments_obj = KubectlGetDeploymentsKeywords(self.ssh_connection).get_deployments(namespace=namespace)
        deployments = deployments_obj.get_deployments()
        start_scale = time()
        for deployment in deployments:
            pod_scaler.scale_deployment(deployment.get_name(), replicas=int(replicas / len(deployments)), namespace=namespace)
        assert pod_getter.wait_for_all_pods_status(expected_statuses=["Running", "Completed"])
        scale_time = time() - start_scale

        return scale_time
