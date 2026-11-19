"""Calico pod connectivity and NetworkPolicy tests."""

from typing import Optional

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_greater_than, validate_greater_than_or_equal, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_expose_pod_keywords import KubectlExposePodKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_iperf3_keywords import KubectlIperf3Keywords
from keywords.k8s.pods.kubectl_pod_connectivity_keywords import KubectlPodConnectivityKeywords
from keywords.k8s.pods.kubectl_run_pod_keywords import KubectlRunPodKeywords
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.service.kubectl_get_service_keywords import KubectlGetServiceKeywords

NETWORKING_IMAGES_MANIFEST = "networking-tests"
BUSYBOX_IMAGE_NAME = "busybox"
BUSYBOX_IMAGE_TAG = "1.36.1"
NGINX_IMAGE_NAME = "nginx"
NGINX_IMAGE_TAG = "1.27.5-alpine"
IPERF3_IMAGE_NAME = "networkstatic/iperf3"
IPERF3_IMAGE_TAG = "multiarch"
REGISTRY_LOCAL_SECRET = "registry-local-secret"
CALICO_SYSTEM_NAMESPACE = "calico-system"
TEST_NAMESPACE = "default"
CALICO_RESOURCE_DIR = "resources/cloud_platform/networking/calico"
REMOTE_RESOURCE_DIR = "/tmp"
HTTP_PORT = 80
POD_RUNNING_TIMEOUT_SECONDS = 120
HTTP_READY_TIMEOUT_SECONDS = 60
POLICY_PROGRAMMED_TIMEOUT_SECONDS = 60
IPERF3_DURATION_SECONDS = 10
# busybox wget reports a dropped connection as a timeout.
BLOCKED_REQUEST_ERROR = "timed out"


def sync_test_image(request: FixtureRequest, ssh_connection: SSHConnection, image_name: str, image_tag: str) -> str:
    """Sync a test image to the local registry and register its removal.

    Args:
        request (FixtureRequest): The pytest request, used to register the image cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.
        image_name (str): The image name in the networking test images manifest.
        image_tag (str): The image tag in the networking test images manifest.

    Returns:
        str: The local registry reference of the image.
    """
    get_logger().log_setup_step(f"Sync the {image_name}:{image_tag} test image to the local registry")
    docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)

    def cleanup_test_image() -> None:
        get_logger().log_teardown_step(f"Remove the {image_name}:{image_tag} test image from the controller")
        docker_sync_keywords.remove_image_from_manifest(image_name, image_tag, NETWORKING_IMAGES_MANIFEST)

    request.addfinalizer(cleanup_test_image)
    return docker_sync_keywords.sync_image_from_manifest(image_name, image_tag, NETWORKING_IMAGES_MANIFEST)


def copy_registry_pull_secret(ssh_connection: SSHConnection, namespace: str) -> None:
    """Copy the local registry pull secret to a namespace.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        namespace (str): The namespace to copy the secret to.
    """
    get_logger().log_setup_step(f"Copy the local registry pull secret to the {namespace} namespace")
    KubectlCreateSecretsKeywords(ssh_connection).copy_secret_between_namespaces(REGISTRY_LOCAL_SECRET, CALICO_SYSTEM_NAMESPACE, namespace)


def start_test_pod(request: FixtureRequest, ssh_connection: SSHConnection, pod_name: str, image: str, namespace: str, command: Optional[list[str]] = None, node_name: Optional[str] = None) -> str:
    """Start a pod, wait for it to run and register its deletion.

    Args:
        request (FixtureRequest): The pytest request, used to register the pod cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pod_name (str): The pod name.
        image (str): The local registry image reference.
        namespace (str): The pod namespace.
        command (Optional[list[str]]): The command that replaces the image entrypoint, if any.
        node_name (Optional[str]): The node to pin the pod to, if any.

    Returns:
        str: The pod IP address.
    """

    def cleanup_test_pod() -> None:
        get_logger().log_teardown_step(f"Delete pod {namespace}/{pod_name}")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod_name, namespace=namespace)

    request.addfinalizer(cleanup_test_pod)
    pod_spec = {"imagePullSecrets": [{"name": REGISTRY_LOCAL_SECRET}]}
    if node_name:
        pod_spec["nodeName"] = node_name
    KubectlRunPodKeywords(ssh_connection).run_pod(pod_name, image, namespace=namespace, overrides={"spec": pod_spec}, command=command)
    get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    get_pods_keywords.wait_for_pod_status(pod_name, "Running", namespace=namespace, timeout=POD_RUNNING_TIMEOUT_SECONDS)
    return get_pods_keywords.get_pods(namespace=namespace).get_pod(pod_name).get_ip()


def expose_test_pod(request: FixtureRequest, ssh_connection: SSHConnection, pod_name: str, namespace: str, service_name: str) -> str:
    """Expose a pod as a ClusterIP Service on port 80 and register the Service deletion.

    Args:
        request (FixtureRequest): The pytest request, used to register the Service cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pod_name (str): The pod to expose.
        namespace (str): The pod namespace.
        service_name (str): The Service name.

    Returns:
        str: The Service ClusterIP.
    """

    def cleanup_test_service() -> None:
        get_logger().log_teardown_step(f"Delete Service {namespace}/{service_name}")
        KubectlDeleteResourceKeywords(ssh_connection).delete_resource("service", service_name, namespace=namespace)

    request.addfinalizer(cleanup_test_service)
    KubectlExposePodKeywords(ssh_connection).expose_pod(pod_name, HTTP_PORT, namespace=namespace, service_name=service_name)
    return KubectlGetServiceKeywords(ssh_connection).get_service(service_name, namespace=namespace).get_cluster_ip()


@mark.p1
def test_pod_to_pod_ping_and_tcp(request: FixtureRequest):
    """Verify a pod can ping another pod and reach it over TCP through a Service.

    On a lab with more than one host that runs pods, the two pods are pinned to
    different hosts so the traffic crosses nodes.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Sync the busybox and nginx test images and copy the local registry pull secret
        - Start a busybox client pod and an nginx server pod, on different hosts when possible

    Test Steps:
        1. Verify the client pod pings the server pod without packet loss
        2. Expose the server pod and verify the client pod reaches it through the Service

    Teardown:
        - Delete the Service and both pods
        - Remove the test images from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    busybox_image = sync_test_image(request, ssh_connection, BUSYBOX_IMAGE_NAME, BUSYBOX_IMAGE_TAG)
    nginx_image = sync_test_image(request, ssh_connection, NGINX_IMAGE_NAME, NGINX_IMAGE_TAG)
    copy_registry_pull_secret(ssh_connection, TEST_NAMESPACE)

    get_logger().log_setup_step("Start a busybox client pod and an nginx server pod, on different hosts when possible")
    # Hosts with the worker subfunction run pods; on a single-host lab both pods share it.
    pod_hosts = [host.get_host_name() for host in SystemHostListKeywords(ssh_connection).get_workers()]
    validate_greater_than(len(pod_hosts), 0, "At least one host runs the worker subfunction")
    start_test_pod(request, ssh_connection, "test-pod-a", busybox_image, TEST_NAMESPACE, command=["sleep", "600"], node_name=pod_hosts[0])
    server_ip = start_test_pod(request, ssh_connection, "test-pod-b", nginx_image, TEST_NAMESPACE, node_name=pod_hosts[-1])
    get_logger().log_info(f"Client on {pod_hosts[0]}, server on {pod_hosts[-1]} at {server_ip}")
    connectivity_keywords = KubectlPodConnectivityKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify the client pod pings the server pod without packet loss")
    ping_output = connectivity_keywords.ping_from_pod("test-pod-a", server_ip, namespace=TEST_NAMESPACE)
    validate_str_contains(ping_output, " 0% packet loss", f"Ping from test-pod-a to test-pod-b ({server_ip}) has no packet loss")

    get_logger().log_test_case_step("Expose the server pod and verify the client pod reaches it through the Service")
    service_ip = expose_test_pod(request, ssh_connection, "test-pod-b", TEST_NAMESPACE, "test-svc")
    # The Service endpoints can lag the Service creation, so the request is retried.
    connectivity_keywords.wait_for_http_get_from_pod("test-pod-a", service_ip, namespace=TEST_NAMESPACE, timeout=HTTP_READY_TIMEOUT_SECONDS)


@mark.p2
@mark.lab_has_min_2_workers
def test_pod_to_pod_iperf3(request: FixtureRequest):
    """Verify iperf3 traffic between pods on two different hosts.

    An iperf3 server DaemonSet places one pod on every host that runs pods; the client
    in one of them measures the bandwidth to the server in another, so the traffic
    crosses the Calico data path between nodes.

    Preconditions:
        - At least two hosts run the worker subfunction
        - Calico operator is installed and healthy

    Setup:
        - Sync the iperf3 test image and copy the local registry pull secret
        - Deploy the iperf3 server DaemonSet and wait for its pods to be ready

    Test Steps:
        1. Run iperf3 from one DaemonSet pod to the server in a pod on another host
        2. Verify the receiver measured a non-zero bandwidth

    Teardown:
        - Delete the iperf3 DaemonSet
        - Remove the iperf3 test image from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    iperf3_image = sync_test_image(request, ssh_connection, IPERF3_IMAGE_NAME, IPERF3_IMAGE_TAG)
    copy_registry_pull_secret(ssh_connection, TEST_NAMESPACE)

    def cleanup_iperf3_daemonset() -> None:
        get_logger().log_teardown_step("Delete the iperf3 DaemonSet")
        KubectlDeleteResourceKeywords(ssh_connection).delete_resource("daemonset", "iperf3-ds", namespace=TEST_NAMESPACE)

    request.addfinalizer(cleanup_iperf3_daemonset)

    get_logger().log_setup_step("Deploy the iperf3 server DaemonSet and wait for its pods to be ready")
    daemonset_path = YamlKeywords(ssh_connection).generate_yaml_file_from_template(get_stx_resource_path(f"{CALICO_RESOURCE_DIR}/iperf3_daemonset.yaml"), {"iperf3_image": iperf3_image}, "iperf3_daemonset.yaml", REMOTE_RESOURCE_DIR)
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(daemonset_path)
    KubectlWaitPodKeywords(ssh_connection).wait_for_pods_ready("app=iperf3", TEST_NAMESPACE)
    iperf3_pods = KubectlGetPodsKeywords(ssh_connection).get_pods_json(namespace=TEST_NAMESPACE, label="app=iperf3").get_pods()
    validate_greater_than_or_equal(len(iperf3_pods), 2, "The iperf3 DaemonSet runs a pod on at least two hosts")
    # A DaemonSet runs one pod per host, so any two of its pods are on different hosts.
    server_pod, client_pod = iperf3_pods[0], iperf3_pods[1]

    get_logger().log_test_case_step(f"Run iperf3 from {client_pod.get_node()} to the server on {server_pod.get_node()}")
    iperf3_result = KubectlIperf3Keywords(ssh_connection).run_iperf3_client_from_pod(client_pod.get_name(), server_pod.get_ip(), namespace=TEST_NAMESPACE, duration_seconds=IPERF3_DURATION_SECONDS)
    get_logger().log_info(f"iperf3 result: {iperf3_result}")

    get_logger().log_test_case_step("Verify the receiver measured a non-zero bandwidth")
    validate_greater_than(iperf3_result.get_received_bits_per_second(), 0, f"iperf3 measured bandwidth from {client_pod.get_node()} to {server_pod.get_node()}")


@mark.p1
def test_cross_namespace_communication_with_policy(request: FixtureRequest):
    """Verify a NetworkPolicy blocks cross-namespace traffic only in the direction it targets.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Sync the busybox and nginx test images
        - Create the ns-alpha and ns-beta namespaces and copy the local registry pull secret to both
        - Start a busybox client and an nginx server in ns-alpha, and an nginx server in ns-beta
        - Expose both nginx servers as Services

    Test Steps:
        1. Verify ns-alpha reaches ns-beta through the Service and the pod address
        2. Apply a NetworkPolicy that drops ingress to ns-beta from ns-alpha
        3. Verify ns-alpha can no longer reach ns-beta through the Service or the pod address
        4. Verify ns-beta still reaches ns-alpha
        5. Delete the NetworkPolicy and verify ns-alpha reaches ns-beta again

    Teardown:
        - Delete the ns-alpha and ns-beta namespaces, which removes the pods, Services and NetworkPolicy
        - Remove the test images from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    busybox_image = sync_test_image(request, ssh_connection, BUSYBOX_IMAGE_NAME, BUSYBOX_IMAGE_TAG)
    nginx_image = sync_test_image(request, ssh_connection, NGINX_IMAGE_NAME, NGINX_IMAGE_TAG)

    get_logger().log_setup_step("Create the ns-alpha and ns-beta namespaces")
    delete_namespace_keywords = KubectlDeleteNamespaceKeywords(ssh_connection)
    create_namespace_keywords = KubectlCreateNamespacesKeywords(ssh_connection)
    for namespace in ["ns-alpha", "ns-beta"]:

        def cleanup_namespace(namespace_to_delete: str = namespace) -> None:
            get_logger().log_teardown_step(f"Delete namespace {namespace_to_delete}")
            delete_namespace_keywords.cleanup_namespace(namespace_to_delete)

        request.addfinalizer(cleanup_namespace)
        create_namespace_keywords.create_namespaces(namespace)
        copy_registry_pull_secret(ssh_connection, namespace)

    get_logger().log_setup_step("Start the test pods and expose the nginx servers as Services")
    start_test_pod(request, ssh_connection, "pod-alpha", busybox_image, "ns-alpha", command=["sleep", "600"])
    start_test_pod(request, ssh_connection, "pod-alpha-server", nginx_image, "ns-alpha")
    beta_pod_ip = start_test_pod(request, ssh_connection, "pod-beta", nginx_image, "ns-beta")
    beta_service_ip = expose_test_pod(request, ssh_connection, "pod-beta", "ns-beta", "svc-beta")
    alpha_service_ip = expose_test_pod(request, ssh_connection, "pod-alpha-server", "ns-alpha", "svc-alpha")
    connectivity_keywords = KubectlPodConnectivityKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify ns-alpha reaches ns-beta through the Service and the pod address")
    for target_ip in [beta_service_ip, beta_pod_ip]:
        connectivity_keywords.wait_for_http_get_from_pod("pod-alpha", target_ip, namespace="ns-alpha", timeout=HTTP_READY_TIMEOUT_SECONDS)

    get_logger().log_test_case_step("Apply a NetworkPolicy that drops ingress to ns-beta from ns-alpha")
    policy_path = f"{REMOTE_RESOURCE_DIR}/deny_cross_ns_policy.yaml"
    FileKeywords(ssh_connection).upload_file(get_stx_resource_path(f"{CALICO_RESOURCE_DIR}/deny_cross_ns_policy.yaml"), policy_path, overwrite=True)
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(policy_path)

    get_logger().log_test_case_step("Verify ns-alpha can no longer reach ns-beta through the Service or the pod address")
    for target_ip in [beta_service_ip, beta_pod_ip]:
        blocked_output = connectivity_keywords.wait_for_http_get_from_pod_to_fail("pod-alpha", target_ip, namespace="ns-alpha", timeout=POLICY_PROGRAMMED_TIMEOUT_SECONDS)
        validate_str_contains(blocked_output, BLOCKED_REQUEST_ERROR, f"The request from ns-alpha to {target_ip} is dropped by the NetworkPolicy")

    get_logger().log_test_case_step("Verify ns-beta still reaches ns-alpha")
    connectivity_keywords.wait_for_http_get_from_pod("pod-beta", alpha_service_ip, namespace="ns-beta", timeout=HTTP_READY_TIMEOUT_SECONDS)

    get_logger().log_test_case_step("Delete the NetworkPolicy and verify ns-alpha reaches ns-beta again")
    KubectlDeletePodsKeywords(ssh_connection).delete_from_yaml(policy_path)
    connectivity_keywords.wait_for_http_get_from_pod("pod-alpha", beta_service_ip, namespace="ns-alpha", timeout=POLICY_PROGRAMMED_TIMEOUT_SECONDS)
