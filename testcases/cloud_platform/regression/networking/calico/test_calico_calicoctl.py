"""calicoctl tests against the Calico operator."""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_greater_than
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords
from keywords.k8s.calico.kubectl_calico_node_keywords import KubectlCalicoNodeKeywords
from keywords.k8s.calico.kubectl_calicoctl_keywords import KubectlCalicoctlKeywords
from keywords.k8s.calico.kubectl_get_installation_keywords import KubectlGetInstallationKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_run_pod_keywords import KubectlRunPodKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords

NETWORKING_IMAGES_MANIFEST = "networking-tests"
CALICOCTL_IMAGE_NAME = "calico/ctl"
BUSYBOX_IMAGE_NAME = "busybox"
BUSYBOX_IMAGE_TAG = "1.36.1"
REGISTRY_LOCAL_SECRET = "registry-local-secret"
CALICO_SYSTEM_NAMESPACE = "calico-system"
TEST_NAMESPACE = "default"
POD_RUNNING_TIMEOUT_SECONDS = 120


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


def setup_calicoctl(request: FixtureRequest, ssh_connection: SSHConnection) -> str:
    """Sync the calicoctl image that matches the installed Calico release and create its RBAC resources.

    Args:
        request (FixtureRequest): The pytest request, used to register the cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The calicoctl image in the local registry.
    """
    calico_release = KubectlCalicoNodeKeywords(ssh_connection).get_calico_release()
    calicoctl_image = sync_test_image(request, ssh_connection, CALICOCTL_IMAGE_NAME, calico_release)

    get_logger().log_setup_step("Create the calicoctl ServiceAccount, ClusterRole and ClusterRoleBinding if missing")
    created_rbac = KubectlCalicoctlKeywords(ssh_connection).setup_calicoctl_rbac()

    def cleanup_calicoctl() -> None:
        get_logger().log_teardown_step("Delete the calicoctl pod and the RBAC resources the test created")
        KubectlCalicoctlKeywords(ssh_connection).teardown_calicoctl(delete_rbac=created_rbac)

    request.addfinalizer(cleanup_calicoctl)
    return calicoctl_image


@mark.p1
def test_calicoctl_get_ippool(request: FixtureRequest):
    """Verify calicoctl lists every IP pool configured in the Installation CR.

    The comparison is by CIDR set, so extra pools created by other features (for
    example SR-IOV pools) or a second IP family do not affect the result.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Sync the calicoctl image that matches the installed Calico release
        - Create the calicoctl RBAC resources if they are missing

    Test Steps:
        1. List the IP pools with calicoctl
        2. Verify every Installation CR IP pool CIDR is listed by calicoctl

    Teardown:
        - Delete the calicoctl pod, and the calicoctl RBAC resources if the test created them
        - Remove the calicoctl image from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    calicoctl_image = setup_calicoctl(request, ssh_connection)

    get_logger().log_test_case_step("List the IP pools with calicoctl")
    calicoctl_ippools = KubectlCalicoctlKeywords(ssh_connection).get_ippools(calicoctl_image)
    get_logger().log_info(f"calicoctl IP pools: {calicoctl_ippools}")

    get_logger().log_test_case_step("Verify every Installation CR IP pool CIDR is listed by calicoctl")
    installation_cidrs = KubectlGetInstallationKeywords(ssh_connection).get_installation().get_ip_pool_cidrs()
    validate_greater_than(len(installation_cidrs), 0, "The Installation CR configures at least one IP pool")
    missing_cidrs = [cidr for cidr in installation_cidrs if not calicoctl_ippools.has_ippool_with_cidr(cidr)]
    validate_equals(missing_cidrs, [], f"calicoctl lists every Installation CR IP pool CIDR {installation_cidrs}")


@mark.p1
def test_calicoctl_get_workload_endpoints(request: FixtureRequest):
    """Verify calicoctl reports a workload endpoint with an address for a running pod.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Sync the calicoctl image that matches the installed Calico release
        - Create the calicoctl RBAC resources if they are missing
        - Sync the busybox test image and copy the local registry pull secret

    Test Steps:
        1. Start a busybox pod
        2. Verify calicoctl reports a workload endpoint with an assigned network for the pod

    Teardown:
        - Delete the busybox pod
        - Delete the calicoctl pod, and the calicoctl RBAC resources if the test created them
        - Remove the test images from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    calicoctl_image = setup_calicoctl(request, ssh_connection)
    busybox_image = sync_test_image(request, ssh_connection, BUSYBOX_IMAGE_NAME, BUSYBOX_IMAGE_TAG)
    get_logger().log_setup_step(f"Copy the local registry pull secret to the {TEST_NAMESPACE} namespace")
    KubectlCreateSecretsKeywords(ssh_connection).copy_secret_between_namespaces(REGISTRY_LOCAL_SECRET, CALICO_SYSTEM_NAMESPACE, TEST_NAMESPACE)
    pod_name = "wep-test"
    delete_pods_keywords = KubectlDeletePodsKeywords(ssh_connection)

    def cleanup_pod() -> None:
        get_logger().log_teardown_step(f"Delete pod {pod_name}")
        delete_pods_keywords.cleanup_pod(pod_name, namespace=TEST_NAMESPACE)

    request.addfinalizer(cleanup_pod)

    get_logger().log_test_case_step(f"Start a busybox pod {pod_name}")
    # A pod left behind by an interrupted run would make 'kubectl run' fail with AlreadyExists.
    delete_pods_keywords.cleanup_pod(pod_name, namespace=TEST_NAMESPACE)
    KubectlRunPodKeywords(ssh_connection).run_pod(pod_name, busybox_image, namespace=TEST_NAMESPACE, overrides={"spec": {"imagePullSecrets": [{"name": REGISTRY_LOCAL_SECRET}]}}, command=["sleep", "600"])
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running", namespace=TEST_NAMESPACE, timeout=POD_RUNNING_TIMEOUT_SECONDS)

    get_logger().log_test_case_step("Verify calicoctl reports a workload endpoint with an assigned network for the pod")
    workload_endpoints = KubectlCalicoctlKeywords(ssh_connection).get_workload_endpoints(calicoctl_image)
    validate_equals(workload_endpoints.has_workload_endpoint(pod_name), True, f"calicoctl reports a workload endpoint for pod {pod_name}")
    validate_greater_than(len(workload_endpoints.get_workload_endpoint(pod_name).get_networks()), 0, f"The workload endpoint of pod {pod_name} has an assigned network")
