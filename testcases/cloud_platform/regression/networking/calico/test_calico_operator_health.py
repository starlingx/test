"""Calico operator health and Calico Ingress Gateway tests."""

from typing import Optional

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_greater_than, validate_list_contains, validate_not_equals, validate_not_none, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords
from keywords.files.curl_keywords import CurlKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.calico.kubectl_calico_node_keywords import KubectlCalicoNodeKeywords
from keywords.k8s.calico.kubectl_get_felixconfiguration_keywords import KubectlGetFelixConfigurationKeywords
from keywords.k8s.calico.kubectl_get_installation_keywords import KubectlGetInstallationKeywords
from keywords.k8s.calico.kubectl_get_tigerastatus_keywords import KubectlGetTigeraStatusKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.gateway.kubectl_gateway_keywords import KubectlGatewayKeywords
from keywords.k8s.kube_cpusets.kube_cpusets_keywords import KubeCpusetsKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_expose_pod_keywords import KubectlExposePodKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_pod_connectivity_keywords import KubectlPodConnectivityKeywords
from keywords.k8s.pods.kubectl_run_pod_keywords import KubectlRunPodKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.network.ip_address_keywords import IPAddressKeywords

NETWORKING_IMAGES_MANIFEST = "networking-tests"
NGINX_IMAGE_NAME = "nginx"
NGINX_IMAGE_TAG = "1.27.5-alpine"
BUSYBOX_IMAGE_NAME = "busybox"
BUSYBOX_IMAGE_TAG = "1.36.1"
REGISTRY_LOCAL_SECRET = "registry-local-secret"
CALICO_SYSTEM_NAMESPACE = "calico-system"
TIGERA_OPERATOR_NAMESPACE = "tigera-operator"
TEST_NAMESPACE = "default"
CALICO_RESOURCE_DIR = "resources/cloud_platform/networking/calico"
REMOTE_RESOURCE_DIR = "/tmp"
GATEWAY_NAME = "calico-gateway"
GATEWAY_LISTENER_NAME = "http"
HTTP_PORT = 80
# The nginx ingress controller that StarlingX deploys in kube-system.
INGRESS_CONTROLLER_NAMESPACE = "kube-system"
INGRESS_CONTROLLER_LABEL = "app.kubernetes.io/name=ingress-nginx,app.kubernetes.io/component=controller"
POD_RUNNING_TIMEOUT_SECONDS = 120
HTTP_READY_TIMEOUT_SECONDS = 60
HTTP_POLLING_SECONDS = 10


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


def copy_registry_pull_secret(ssh_connection: SSHConnection) -> None:
    """Copy the local registry pull secret to the test namespace.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    get_logger().log_setup_step(f"Copy the local registry pull secret to the {TEST_NAMESPACE} namespace")
    KubectlCreateSecretsKeywords(ssh_connection).copy_secret_between_namespaces(REGISTRY_LOCAL_SECRET, CALICO_SYSTEM_NAMESPACE, TEST_NAMESPACE)


def start_test_pod(request: FixtureRequest, ssh_connection: SSHConnection, pod_name: str, image: str, command: Optional[list[str]] = None) -> str:
    """Start a pod in the test namespace, wait for it to run and register its deletion.

    Args:
        request (FixtureRequest): The pytest request, used to register the pod cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pod_name (str): The pod name.
        image (str): The local registry image reference.
        command (Optional[list[str]]): The command that replaces the image entrypoint, if any.

    Returns:
        str: The pod IP address.
    """

    def cleanup_test_pod() -> None:
        get_logger().log_teardown_step(f"Delete pod {pod_name}")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod_name, namespace=TEST_NAMESPACE)

    request.addfinalizer(cleanup_test_pod)
    KubectlRunPodKeywords(ssh_connection).run_pod(pod_name, image, namespace=TEST_NAMESPACE, overrides={"spec": {"imagePullSecrets": [{"name": REGISTRY_LOCAL_SECRET}]}}, command=command)
    get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    get_pods_keywords.wait_for_pod_status(pod_name, "Running", namespace=TEST_NAMESPACE, timeout=POD_RUNNING_TIMEOUT_SECONDS)
    return get_pods_keywords.get_pods(namespace=TEST_NAMESPACE).get_pod(pod_name).get_ip()


def expose_test_pod(request: FixtureRequest, ssh_connection: SSHConnection, pod_name: str) -> None:
    """Expose a test pod as a ClusterIP Service on port 80 and register the Service deletion.

    Args:
        request (FixtureRequest): The pytest request, used to register the Service cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pod_name (str): The pod to expose; the Service takes the same name.
    """

    def cleanup_test_service() -> None:
        get_logger().log_teardown_step(f"Delete Service {pod_name}")
        KubectlDeleteResourceKeywords(ssh_connection).delete_resource("service", pod_name, namespace=TEST_NAMESPACE)

    request.addfinalizer(cleanup_test_service)
    KubectlExposePodKeywords(ssh_connection).expose_pod(pod_name, HTTP_PORT, namespace=TEST_NAMESPACE)


def apply_test_resource(request: FixtureRequest, ssh_connection: SSHConnection, resource_file: str, resource_type: str, resource_name: str) -> None:
    """Apply a Calico test resource file and register the resource deletion.

    Args:
        request (FixtureRequest): The pytest request, used to register the resource cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.
        resource_file (str): The file name under the Calico networking resources directory.
        resource_type (str): The kubectl resource type, used for the cleanup.
        resource_name (str): The resource name defined in the file, used for the cleanup.
    """

    def cleanup_test_resource() -> None:
        get_logger().log_teardown_step(f"Delete {resource_type} {resource_name}")
        KubectlDeleteResourceKeywords(ssh_connection).delete_resource(resource_type, resource_name, namespace=TEST_NAMESPACE)

    request.addfinalizer(cleanup_test_resource)
    remote_path = f"{REMOTE_RESOURCE_DIR}/{resource_file}"
    FileKeywords(ssh_connection).upload_file(get_stx_resource_path(f"{CALICO_RESOURCE_DIR}/{resource_file}"), remote_path, overwrite=True)
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_path)


def enable_calico_gateway(request: FixtureRequest, ssh_connection: SSHConnection) -> str:
    """Enable the Calico Ingress Gateway and register its removal if the test enabled it.

    A gateway that was already enabled before the test is left enabled in teardown.

    Args:
        request (FixtureRequest): The pytest request, used to register the gateway cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The cluster IP family ('ipv4', 'ipv6' or 'dual').
    """
    gateway_keywords = KubectlGatewayKeywords(ssh_connection)
    was_enabled = gateway_keywords.is_gateway_api_enabled()
    get_logger().log_info(f"Calico Ingress Gateway enabled before the test: {was_enabled}")

    def cleanup_calico_gateway() -> None:
        get_logger().log_teardown_step("Disable the Calico Ingress Gateway if the test enabled it")
        if not was_enabled:
            KubectlGatewayKeywords(ssh_connection).disable_gateway_api()

    request.addfinalizer(cleanup_calico_gateway)
    return gateway_keywords.enable_gateway_api()


def get_nodeport_http_status(ssh_connection: SSHConnection, node_ip: str, node_port: int, host_header: Optional[str] = None) -> str:
    """Send an HTTP GET to a NodePort from the active controller and return the status code.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        node_ip (str): The node address.
        node_port (int): The NodePort.
        host_header (Optional[str]): The HTTP Host header, for host-based routing, if any.

    Returns:
        str: The HTTP status code.
    """
    return CurlKeywords(ssh_connection).get_http_status_code(f"http://{IPAddressKeywords(node_ip).get_url_host()}:{node_port}/", host_header=host_header)


@mark.p0
def test_calico_platform_core_affinity():
    """Verify the Calico pods run on the platform CPU cores.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - None

    Test Steps:
        1. Verify the calico-system and tigera-operator namespaces carry the platform label
        2. Verify every calico-system and tigera-operator container is in the platform CPU group

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify the calico-system and tigera-operator namespaces carry the platform label")
    platform_namespaces = KubectlGetNamespacesKeywords(ssh_connection).get_namespaces_by_label("app.starlingx.io/component=platform")
    for namespace in [CALICO_SYSTEM_NAMESPACE, TIGERA_OPERATOR_NAMESPACE]:
        validate_equals(platform_namespaces.is_namespace(namespace), True, f"Namespace {namespace} has the label app.starlingx.io/component=platform")

    get_logger().log_test_case_step("Verify every calico-system and tigera-operator container is in the platform CPU group")
    cpusets_output = KubeCpusetsKeywords(ssh_connection).get_kube_cpusets_output()
    calico_containers = cpusets_output.get_containers_by_namespace(CALICO_SYSTEM_NAMESPACE) + cpusets_output.get_containers_by_namespace(TIGERA_OPERATOR_NAMESPACE)
    validate_greater_than(len(calico_containers), 0, "kube-cpusets lists calico-system and tigera-operator containers")
    non_platform_containers = [f"{container.get_namespace()}/{container.get_pod_name()}: group={container.get_group()}" for container in calico_containers if container.get_group().lower() != "platform"]
    validate_equals(non_platform_containers, [], "Every calico-system and tigera-operator container is in the platform CPU group")


@mark.p1
def test_external_access_via_gateway(request: FixtureRequest):
    """Verify external access to a pod through a Calico Ingress Gateway HTTPRoute.

    StarlingX deploys no LoadBalancer controller, so the Gateway is never given an
    external address and stays Programmed=False (AddressNotAssigned). Traffic is sent
    to the Envoy proxy NodePort instead.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Sync the nginx test image and copy the local registry pull secret
        - Start an nginx pod and expose it as a Service
        - Enable the Calico Ingress Gateway

    Test Steps:
        1. Create a Gateway and an HTTPRoute to the nginx Service
        2. Verify the Gateway listener is Programmed and the HTTPRoute is Accepted
        3. Verify the Envoy proxy pod is Running with every container ready
        4. Verify the nginx pod answers HTTP 200 through the Envoy proxy NodePort

    Teardown:
        - Delete the HTTPRoute and the Gateway
        - Disable the Calico Ingress Gateway if the test enabled it
        - Delete the nginx Service and pod
        - Remove the nginx test image from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    nginx_image = sync_test_image(request, ssh_connection, NGINX_IMAGE_NAME, NGINX_IMAGE_TAG)
    copy_registry_pull_secret(ssh_connection)

    get_logger().log_setup_step("Start an nginx pod and expose it as a Service")
    start_test_pod(request, ssh_connection, "web", nginx_image)
    expose_test_pod(request, ssh_connection, "web")

    get_logger().log_setup_step("Enable the Calico Ingress Gateway")
    ip_family = enable_calico_gateway(request, ssh_connection)

    get_logger().log_test_case_step("Create a Gateway and an HTTPRoute to the nginx Service")
    apply_test_resource(request, ssh_connection, "gateway.yaml", "gateway", GATEWAY_NAME)
    apply_test_resource(request, ssh_connection, "httproute.yaml", "httproute", "web-route")

    get_logger().log_test_case_step("Verify the Gateway listener is Programmed and the HTTPRoute is Accepted")
    gateway_keywords = KubectlGatewayKeywords(ssh_connection)
    gateway_keywords.wait_for_gateway_listener_programmed(GATEWAY_NAME, GATEWAY_LISTENER_NAME)
    gateway_keywords.wait_for_httproute_accepted("web-route", GATEWAY_NAME)

    get_logger().log_test_case_step("Verify the Envoy proxy pod is Running with every container ready")
    envoy_proxy_pod = gateway_keywords.wait_for_envoy_proxy_ready(GATEWAY_NAME)

    get_logger().log_test_case_step("Verify the nginx pod answers HTTP 200 through the Envoy proxy NodePort")
    node_ip = gateway_keywords.get_envoy_proxy_node_ip(envoy_proxy_pod, ip_family)
    node_port = gateway_keywords.get_envoy_service(GATEWAY_NAME).get_node_port(HTTP_PORT)

    def get_web_http_status() -> str:
        return get_nodeport_http_status(ssh_connection, node_ip, node_port)

    validate_equals_with_retry(get_web_http_status, "200", f"nginx answers HTTP 200 through the Envoy proxy NodePort {node_ip}:{node_port}", timeout=HTTP_READY_TIMEOUT_SECONDS, polling_sleep_time=HTTP_POLLING_SECONDS)


@mark.p1
def test_multiple_httproutes_single_gateway(request: FixtureRequest):
    """Verify one Calico Ingress Gateway routes two host names to two backends.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Sync the nginx test image and copy the local registry pull secret
        - Start two nginx pods (app1, app2) and expose each as a Service
        - Enable the Calico Ingress Gateway

    Test Steps:
        1. Create a Gateway and one HTTPRoute per host name
        2. Verify the Gateway listener is Programmed and both HTTPRoutes are Accepted
        3. Verify the Envoy proxy pod is Running with every container ready
        4. Verify each host name answers HTTP 200 through the Envoy proxy NodePort

    Teardown:
        - Delete both HTTPRoutes and the Gateway
        - Disable the Calico Ingress Gateway if the test enabled it
        - Delete both Services and pods
        - Remove the nginx test image from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    nginx_image = sync_test_image(request, ssh_connection, NGINX_IMAGE_NAME, NGINX_IMAGE_TAG)
    copy_registry_pull_secret(ssh_connection)

    get_logger().log_setup_step("Start two nginx pods (app1, app2) and expose each as a Service")
    for app_name in ["app1", "app2"]:
        start_test_pod(request, ssh_connection, app_name, nginx_image)
        expose_test_pod(request, ssh_connection, app_name)

    get_logger().log_setup_step("Enable the Calico Ingress Gateway")
    ip_family = enable_calico_gateway(request, ssh_connection)

    get_logger().log_test_case_step("Create a Gateway and one HTTPRoute per host name")
    apply_test_resource(request, ssh_connection, "gateway.yaml", "gateway", GATEWAY_NAME)
    apply_test_resource(request, ssh_connection, "httproute_app1.yaml", "httproute", "app1-route")
    apply_test_resource(request, ssh_connection, "httproute_app2.yaml", "httproute", "app2-route")

    get_logger().log_test_case_step("Verify the Gateway listener is Programmed and both HTTPRoutes are Accepted")
    gateway_keywords = KubectlGatewayKeywords(ssh_connection)
    gateway_keywords.wait_for_gateway_listener_programmed(GATEWAY_NAME, GATEWAY_LISTENER_NAME)
    for route_name in ["app1-route", "app2-route"]:
        gateway_keywords.wait_for_httproute_accepted(route_name, GATEWAY_NAME)

    get_logger().log_test_case_step("Verify the Envoy proxy pod is Running with every container ready")
    envoy_proxy_pod = gateway_keywords.wait_for_envoy_proxy_ready(GATEWAY_NAME)

    get_logger().log_test_case_step("Verify each host name answers HTTP 200 through the Envoy proxy NodePort")
    node_ip = gateway_keywords.get_envoy_proxy_node_ip(envoy_proxy_pod, ip_family)
    node_port = gateway_keywords.get_envoy_service(GATEWAY_NAME).get_node_port(HTTP_PORT)
    for host_name in ["app1.local", "app2.local"]:

        def get_host_http_status() -> str:
            return get_nodeport_http_status(ssh_connection, node_ip, node_port, host_header=host_name)

        validate_equals_with_retry(get_host_http_status, "200", f"Host {host_name} answers HTTP 200 through the Envoy proxy NodePort {node_ip}:{node_port}", timeout=HTTP_READY_TIMEOUT_SECONDS, polling_sleep_time=HTTP_POLLING_SECONDS)


@mark.p1
def test_calico_images_from_local_registry():
    """Verify every Calico image is pulled from the local registry.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - None

    Test Steps:
        1. Verify every calico-system and tigera-operator container and init container image comes from the local registry
        2. Verify the Installation CR points the operator at the local registry with a pull secret

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    local_registry_url = ConfigurationManager.get_docker_config().get_local_registry().get_registry_url()

    get_logger().log_test_case_step("Verify every calico-system and tigera-operator container and init container image comes from the local registry")
    get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    all_images = []
    for namespace in [CALICO_SYSTEM_NAMESPACE, TIGERA_OPERATOR_NAMESPACE]:
        pods_output = get_pods_keywords.get_pods_json(namespace)
        all_images.extend(pods_output.get_all_container_images())
        all_images.extend(pods_output.get_all_init_container_images())
    validate_greater_than(len(all_images), 0, "The calico-system and tigera-operator pods report at least one image")
    non_local_images = [image for image in all_images if not image.startswith(f"{local_registry_url}/")]
    validate_equals(non_local_images, [], f"Every Calico image is pulled from {local_registry_url}")

    get_logger().log_test_case_step("Verify the Installation CR points the operator at the local registry with a pull secret")
    installation = KubectlGetInstallationKeywords(ssh_connection).get_installation()
    validate_not_none(installation.get_registry(), "The Installation CR sets a registry")
    validate_str_contains(installation.get_registry(), local_registry_url, f"The Installation CR registry is under {local_registry_url}")
    validate_not_equals(installation.get_image_pull_secret_names(), [], "The Installation CR sets at least one image pull secret")


@mark.p1
def test_felix_configuration_failsafe_settings():
    """Verify the FelixConfiguration values StarlingX sets, including the failsafe ports.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - None

    Test Steps:
        1. Verify defaultEndpointToHostAction, logSeverityScreen and iptablesBackend
        2. Verify the failsafe inbound and outbound host ports

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    felix = KubectlGetFelixConfigurationKeywords(ssh_connection).get_felixconfiguration()

    get_logger().log_test_case_step("Verify defaultEndpointToHostAction, logSeverityScreen and iptablesBackend")
    validate_equals(felix.get_default_endpoint_to_host_action(), "Accept", "FelixConfiguration defaultEndpointToHostAction is Accept")
    validate_equals(felix.get_log_severity_screen(), "Info", "FelixConfiguration logSeverityScreen is Info")
    validate_equals(felix.get_iptables_backend(), "NFT", "FelixConfiguration iptablesBackend is NFT")

    get_logger().log_test_case_step("Verify the failsafe inbound and outbound host ports")
    inbound_ports = felix.get_failsafe_inbound_ports()
    for expected_port in [("TCP", 22), ("UDP", 68), ("TCP", 179), ("TCP", 6443)]:
        validate_list_contains(expected_port, inbound_ports, f"Failsafe inbound host ports include {expected_port[0]}/{expected_port[1]}")
    outbound_ports = felix.get_failsafe_outbound_ports()
    for expected_port in [("UDP", 53), ("UDP", 67), ("TCP", 179), ("TCP", 6443)]:
        validate_list_contains(expected_port, outbound_ports, f"Failsafe outbound host ports include {expected_port[0]}/{expected_port[1]}")


@mark.p1
def test_nginx_and_calico_gateway_coexistence(request: FixtureRequest):
    """Verify the nginx ingress controller keeps serving traffic after the Calico Ingress Gateway is enabled.

    Both paths are checked from a client pod inside the cluster: the nginx ingress
    controller pod, and the Envoy proxy Service ClusterIP.

    Preconditions:
        - Calico operator is installed and healthy
        - The StarlingX nginx ingress controller is deployed

    Setup:
        - Sync the nginx and busybox test images and copy the local registry pull secret
        - Start a busybox client pod

    Test Steps:
        1. Verify the nginx ingress controller pod is Running
        2. Expose an nginx app through an Ingress and verify the ingress controller serves it
        3. Enable the Calico Ingress Gateway and expose a second nginx app through an HTTPRoute
        4. Verify the Envoy proxy Service ClusterIP serves the second app
        5. Verify the nginx ingress controller still serves the first app
        6. Verify the Calico operator is healthy

    Teardown:
        - Delete the HTTPRoute, the Gateway and the Ingress
        - Disable the Calico Ingress Gateway if the test enabled it
        - Delete both Services and all pods
        - Remove the test images from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    nginx_image = sync_test_image(request, ssh_connection, NGINX_IMAGE_NAME, NGINX_IMAGE_TAG)
    busybox_image = sync_test_image(request, ssh_connection, BUSYBOX_IMAGE_NAME, BUSYBOX_IMAGE_TAG)
    copy_registry_pull_secret(ssh_connection)

    get_logger().log_setup_step("Start a busybox client pod")
    start_test_pod(request, ssh_connection, "curl-client", busybox_image, command=["sleep", "3600"])
    connectivity_keywords = KubectlPodConnectivityKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify the nginx ingress controller pod is Running")
    ingress_controller_pods = [pod for pod in KubectlGetPodsKeywords(ssh_connection).get_pods_json(namespace=INGRESS_CONTROLLER_NAMESPACE, label=INGRESS_CONTROLLER_LABEL).get_pods() if pod.get_status() == "Running"]
    validate_greater_than(len(ingress_controller_pods), 0, f"An nginx ingress controller pod ({INGRESS_CONTROLLER_LABEL}) is Running in {INGRESS_CONTROLLER_NAMESPACE}")
    ingress_controller_ip = ingress_controller_pods[0].get_ip()

    get_logger().log_test_case_step("Expose an nginx app through an Ingress and verify the ingress controller serves it")
    start_test_pod(request, ssh_connection, "nginx-app", nginx_image)
    expose_test_pod(request, ssh_connection, "nginx-app")
    apply_test_resource(request, ssh_connection, "ingress_nginx_app.yaml", "ingress", "nginx-app-ingress")
    connectivity_keywords.wait_for_http_get_from_pod("curl-client", ingress_controller_ip, namespace=TEST_NAMESPACE, host_header="nginx-app.test", timeout=HTTP_READY_TIMEOUT_SECONDS)

    get_logger().log_test_case_step("Enable the Calico Ingress Gateway and expose a second nginx app through an HTTPRoute")
    enable_calico_gateway(request, ssh_connection)
    apply_test_resource(request, ssh_connection, "gateway.yaml", "gateway", GATEWAY_NAME)
    gateway_keywords = KubectlGatewayKeywords(ssh_connection)
    gateway_keywords.wait_for_gateway_accepted(GATEWAY_NAME)
    start_test_pod(request, ssh_connection, "gateway-app", nginx_image)
    expose_test_pod(request, ssh_connection, "gateway-app")
    apply_test_resource(request, ssh_connection, "httproute_gateway_app.yaml", "httproute", "gateway-app-route")
    gateway_keywords.wait_for_httproute_accepted("gateway-app-route", GATEWAY_NAME)

    get_logger().log_test_case_step("Verify the Envoy proxy Service ClusterIP serves the second app")
    envoy_cluster_ip = gateway_keywords.get_envoy_service(GATEWAY_NAME).get_cluster_ip()
    connectivity_keywords.wait_for_http_get_from_pod("curl-client", envoy_cluster_ip, namespace=TEST_NAMESPACE, host_header="gateway-app.test", timeout=HTTP_READY_TIMEOUT_SECONDS)

    get_logger().log_test_case_step("Verify the nginx ingress controller still serves the first app")
    connectivity_keywords.wait_for_http_get_from_pod("curl-client", ingress_controller_ip, namespace=TEST_NAMESPACE, host_header="nginx-app.test", timeout=HTTP_READY_TIMEOUT_SECONDS)

    get_logger().log_test_case_step("Verify the Calico operator is healthy")
    KubectlGetTigeraStatusKeywords(ssh_connection).validate_healthy()


@mark.p1
def test_calico_node_bird_status():
    """Verify calico-node reports every bird instance ready with a BGP peers table.

    Reads 'calico-node -show-status' inside a calico-node pod, which reports one bird
    instance per IP family.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - None

    Test Steps:
        1. Verify calico-node reports at least one bird instance
        2. Verify every bird instance is ready and prints its BGP peers table

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify calico-node reports at least one bird instance")
    node_status = KubectlCalicoNodeKeywords(ssh_connection).get_calico_node_status()
    ip_versions = node_status.get_ip_versions()
    validate_greater_than(len(ip_versions), 0, "calico-node reports at least one bird instance")

    get_logger().log_test_case_step("Verify every bird instance is ready and prints its BGP peers table")
    for ip_version in ip_versions:
        validate_equals(node_status.is_bird_ready(ip_version), True, f"bird {ip_version} is ready")
        validate_equals(node_status.has_bgp_peers_section(ip_version), True, f"bird {ip_version} prints its BGP peers table")


@mark.p1
@mark.lab_has_standby_controller
def test_calico_node_bgp_peers_established():
    """Verify calico-node reports every BGP peer as Established on a multi-node lab.

    A single-node lab has no BGP peers, so this test needs a standby controller.

    Preconditions:
        - A standby controller is present
        - Calico operator is installed and healthy

    Setup:
        - None

    Test Steps:
        1. Verify calico-node reports at least one BGP peer
        2. Verify every BGP peer is Established

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify calico-node reports at least one BGP peer")
    node_status = KubectlCalicoNodeKeywords(ssh_connection).get_calico_node_status()
    validate_greater_than(len(node_status.get_bgp_peers()), 0, "calico-node reports at least one BGP peer")

    get_logger().log_test_case_step("Verify every BGP peer is Established")
    validate_equals(node_status.get_bgp_peers_not_established(), [], "Every BGP peer is Established")
