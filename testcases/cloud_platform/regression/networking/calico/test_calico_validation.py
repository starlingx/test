"""Calico operator validation tests: namespace security, RBAC, invalid input and reconciliation."""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import fail, validate_equals, validate_greater_than
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.auth.kubectl_auth_keywords import KubectlAuthKeywords
from keywords.k8s.calico.kubectl_calico_node_keywords import KubectlCalicoNodeKeywords
from keywords.k8s.calico.kubectl_calicoctl_keywords import KubectlCalicoctlKeywords
from keywords.k8s.calico.kubectl_get_installation_keywords import KubectlGetInstallationKeywords
from keywords.k8s.calico.kubectl_get_tigerastatus_keywords import KubectlGetTigeraStatusKeywords
from keywords.k8s.calico.kubectl_patch_installation_keywords import KubectlPatchInstallationKeywords
from keywords.k8s.calico.object.installation_ip_pool_object import InstallationIPPoolObject
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_run_pod_keywords import KubectlRunPodKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords

NETWORKING_IMAGES_MANIFEST = "networking-tests"
BUSYBOX_IMAGE_NAME = "busybox"
BUSYBOX_IMAGE_TAG = "1.36.1"
CALICOCTL_IMAGE_NAME = "calico/ctl"
REGISTRY_LOCAL_SECRET = "registry-local-secret"
CALICO_SYSTEM_NAMESPACE = "calico-system"
TIGERA_OPERATOR_NAMESPACE = "tigera-operator"
TEST_NAMESPACE = "default"
CALICO_RESOURCE_DIR = "resources/cloud_platform/networking/calico"
REMOTE_RESOURCE_DIR = "/tmp"
# A ServiceAccount allowed only to read pods in the test namespace, so a denial on the Calico
# namespaces is shown to come from RBAC and not from an identity that can do nothing at all.
RBAC_TEST_USER_RESOURCE = "calico_rbac_test_user.yaml"
RBAC_TEST_USER = "system:serviceaccount:default:calico-rbac-test"
INVALID_CIDR = "999.999.999.0/16"
# The pool added to show that a pool of the other IP family is handled; documentation ranges
# (RFC 3849, RFC 5737) are used so it cannot collide with a real network.
CONFLICTING_POOL_NAME = "conflicting-family-test-pool"
CONFLICTING_POOL_CIDR = {4: "2001:db8:ca1c:ff::/64", 6: "198.51.100.0/24"}
POD_RUNNING_TIMEOUT_SECONDS = 120
# A change that is kept has no event to wait on, so the reconciliation check observes the
# value for a fixed window and fails on the first read that differs.
OPERATOR_RECONCILE_OBSERVATION_SECONDS = 60
OPERATOR_RECONCILE_POLLING_SECONDS = 15


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


def create_rbac_test_user(request: FixtureRequest, ssh_connection: SSHConnection) -> None:
    """Create the limited ServiceAccount used to check RBAC, and register its deletion.

    Args:
        request (FixtureRequest): The pytest request, used to register the cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    remote_path = f"{REMOTE_RESOURCE_DIR}/{RBAC_TEST_USER_RESOURCE}"

    def cleanup_rbac_test_user() -> None:
        get_logger().log_teardown_step("Delete the RBAC test ServiceAccount, Role and RoleBinding")
        KubectlDeletePodsKeywords(ssh_connection).delete_from_yaml(remote_path)

    get_logger().log_setup_step("Create a ServiceAccount that may only read pods in the default namespace")
    FileKeywords(ssh_connection).upload_file(get_stx_resource_path(f"{CALICO_RESOURCE_DIR}/{RBAC_TEST_USER_RESOURCE}"), remote_path, overwrite=True)
    request.addfinalizer(cleanup_rbac_test_user)
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_path)


def validate_rbac_test_user_can_read_default_pods(ssh_connection: SSHConnection) -> None:
    """Validate the RBAC test user is allowed what its Role grants.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    answer = KubectlAuthKeywords(ssh_connection).can_i("list", "pods", namespace=TEST_NAMESPACE, as_user=RBAC_TEST_USER)
    validate_equals(answer.is_allowed(), True, f"{RBAC_TEST_USER} may list pods in {TEST_NAMESPACE}, as its Role grants")


def select_tested_ip_pool(ssh_connection: SSHConnection) -> InstallationIPPoolObject:
    """Select the Installation CR IP pool the tests change: the IPv4 pool, or the IPv6 pool on an IPv6-only cluster.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        InstallationIPPoolObject: The selected IP pool.
    """
    installation = KubectlGetInstallationKeywords(ssh_connection).get_installation()
    ip_version = 6 if installation.get_ip_family() == "ipv6" else 4
    return installation.get_ip_pool_by_ip_version(ip_version)


def restore_ip_pools_on_teardown(request: FixtureRequest, ssh_connection: SSHConnection) -> None:
    """Record the Installation CR IP pools and register a finalizer that restores them exactly.

    Args:
        request (FixtureRequest): The pytest request, used to register the restore.
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    original_ip_pools_json = KubectlGetInstallationKeywords(ssh_connection).get_installation().get_ip_pools_json()
    get_logger().log_info(f"Original Installation CR IP pools: {original_ip_pools_json}")

    def restore_ip_pools() -> None:
        get_logger().log_teardown_step("Restore the original Installation CR IP pools")
        KubectlPatchInstallationKeywords(LabConnectionKeywords().get_active_controller_ssh()).replace_ip_pools(original_ip_pools_json)

    request.addfinalizer(restore_ip_pools)


def start_busybox_pod(request: FixtureRequest, ssh_connection: SSHConnection, pod_name: str, busybox_image: str) -> str:
    """Start a busybox pod in the test namespace, wait for it to run and register its deletion.

    Args:
        request (FixtureRequest): The pytest request, used to register the pod cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pod_name (str): The pod name.
        busybox_image (str): The busybox image in the local registry.

    Returns:
        str: The pod IP address.
    """

    def cleanup_busybox_pod() -> None:
        get_logger().log_teardown_step(f"Delete pod {pod_name}")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod_name, namespace=TEST_NAMESPACE)

    request.addfinalizer(cleanup_busybox_pod)
    KubectlRunPodKeywords(ssh_connection).run_pod(pod_name, busybox_image, namespace=TEST_NAMESPACE, overrides={"spec": {"imagePullSecrets": [{"name": REGISTRY_LOCAL_SECRET}]}}, command=["sleep", "600"])
    get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    get_pods_keywords.wait_for_pod_status(pod_name, "Running", namespace=TEST_NAMESPACE, timeout=POD_RUNNING_TIMEOUT_SECONDS)
    return get_pods_keywords.get_pods(namespace=TEST_NAMESPACE).get_pod(pod_name).get_ip()


def validate_calico_pods_running(ssh_connection: SSHConnection, change: str) -> None:
    """Validate every calico-system pod is Running after a change.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        change (str): The change that was applied, used in the validation messages.
    """
    calico_pods = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=CALICO_SYSTEM_NAMESPACE).get_pods()
    validate_greater_than(len(calico_pods), 0, "calico-system has pods")
    not_running = sorted(f"{pod.get_name()}: {pod.get_status()}" for pod in calico_pods if pod.get_status() != "Running")
    validate_equals(not_running, [], f"Every calico-system pod is Running after {change}")


@mark.p1
def test_calico_namespaces_pod_security_privileged():
    """Verify the Calico namespaces enforce the privileged pod security level.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - None

    Test Steps:
        1. Verify calico-system and tigera-operator carry pod-security.kubernetes.io/enforce=privileged

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify calico-system and tigera-operator carry pod-security.kubernetes.io/enforce=privileged")
    privileged_namespaces = KubectlGetNamespacesKeywords(ssh_connection).get_namespaces_by_label("pod-security.kubernetes.io/enforce=privileged")
    for namespace in [CALICO_SYSTEM_NAMESPACE, TIGERA_OPERATOR_NAMESPACE]:
        validate_equals(privileged_namespaces.is_namespace(namespace), True, f"Namespace {namespace} has pod-security.kubernetes.io/enforce=privileged")


@mark.p1
def test_non_admin_access_denied(request: FixtureRequest):
    """Verify a user without Calico permissions cannot read the Calico namespaces or roles.

    The user is a ServiceAccount that may read pods in the default namespace, so the
    test first shows the identity is authorized for what it was granted, and then that
    it is refused on the Calico resources.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Create a ServiceAccount that may only read pods in the default namespace

    Test Steps:
        1. Verify the ServiceAccount may list pods in the default namespace
        2. Verify it may not read pods in calico-system or tigera-operator, create deployments in calico-system, or read the tigera-operator ClusterRoleBinding

    Teardown:
        - Delete the ServiceAccount, Role and RoleBinding
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    create_rbac_test_user(request, ssh_connection)

    get_logger().log_test_case_step("Verify the ServiceAccount may list pods in the default namespace")
    validate_rbac_test_user_can_read_default_pods(ssh_connection)

    get_logger().log_test_case_step("Verify it may not read pods in calico-system or tigera-operator, create deployments in calico-system, or read the tigera-operator ClusterRoleBinding")
    auth_keywords = KubectlAuthKeywords(ssh_connection)
    denied_requests = [
        ("get", "pods", CALICO_SYSTEM_NAMESPACE),
        ("get", "pods", TIGERA_OPERATOR_NAMESPACE),
        ("create", "deployments", CALICO_SYSTEM_NAMESPACE),
        ("get", "clusterrolebinding/tigera-operator", None),
    ]
    for verb, resource, namespace in denied_requests:
        answer = auth_keywords.can_i(verb, resource, namespace=namespace, as_user=RBAC_TEST_USER)
        validate_equals(answer.is_denied(), True, f"{RBAC_TEST_USER} is denied '{verb} {resource}' in {namespace or 'the cluster scope'}")


@mark.p1
def test_unauthorized_modifications_denied(request: FixtureRequest):
    """Verify a user without Calico permissions cannot change Calico workloads or configuration.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Create a ServiceAccount that may only read pods in the default namespace

    Test Steps:
        1. Verify the ServiceAccount may list pods in the default namespace
        2. Verify it may not create pods in calico-system, patch the tigera-operator ClusterRole, or patch the Installation CR

    Teardown:
        - Delete the ServiceAccount, Role and RoleBinding
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    create_rbac_test_user(request, ssh_connection)

    get_logger().log_test_case_step("Verify the ServiceAccount may list pods in the default namespace")
    validate_rbac_test_user_can_read_default_pods(ssh_connection)

    get_logger().log_test_case_step("Verify it may not create pods in calico-system, patch the tigera-operator ClusterRole, or patch the Installation CR")
    auth_keywords = KubectlAuthKeywords(ssh_connection)
    denied_requests = [
        ("create", "pods", CALICO_SYSTEM_NAMESPACE),
        ("patch", "clusterrole/tigera-operator", None),
        ("patch", "installations.operator.tigera.io/default", None),
    ]
    for verb, resource, namespace in denied_requests:
        answer = auth_keywords.can_i(verb, resource, namespace=namespace, as_user=RBAC_TEST_USER)
        validate_equals(answer.is_denied(), True, f"{RBAC_TEST_USER} is denied '{verb} {resource}' in {namespace or 'the cluster scope'}")


@mark.p2
def test_invalid_cidr_rejected(request: FixtureRequest):
    """Verify an invalid IP pool CIDR in the Installation CR does not break pod networking.

    The operator may reject the CIDR or report Degraded; that is reported for
    information only, because it differs between builds. The required behaviour is that
    the Calico pods keep running and new pods are still addressed from the original pool.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Sync the busybox test image and copy the local registry pull secret
        - Record the Installation CR IP pools

    Test Steps:
        1. Set an invalid CIDR on the IPv4 pool (the IPv6 pool on an IPv6-only cluster)
        2. Verify every calico-system pod is still Running
        3. Verify a new pod is addressed from the original pool

    Teardown:
        - Delete the test pod
        - Restore the original Installation CR IP pools
        - Remove the busybox test image from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    busybox_image = sync_test_image(request, ssh_connection, BUSYBOX_IMAGE_NAME, BUSYBOX_IMAGE_TAG)
    get_logger().log_setup_step(f"Copy the local registry pull secret to the {TEST_NAMESPACE} namespace")
    KubectlCreateSecretsKeywords(ssh_connection).copy_secret_between_namespaces(REGISTRY_LOCAL_SECRET, CALICO_SYSTEM_NAMESPACE, TEST_NAMESPACE)
    get_logger().log_setup_step("Record the Installation CR IP pools")
    restore_ip_pools_on_teardown(request, ssh_connection)
    tested_pool = select_tested_ip_pool(ssh_connection)

    get_logger().log_test_case_step(f"Set the invalid CIDR {INVALID_CIDR} on the IP pool {tested_pool.get_cidr()}")
    installation = KubectlGetInstallationKeywords(ssh_connection).get_installation()
    KubectlPatchInstallationKeywords(ssh_connection).replace_ip_pools(installation.get_ip_pools_json_with_cidr_replaced(tested_pool.get_cidr(), INVALID_CIDR))
    get_logger().log_info(f"TigeraStatus after the invalid CIDR (for information): {KubectlGetTigeraStatusKeywords(ssh_connection).get_tigerastatus()}")

    get_logger().log_test_case_step("Verify every calico-system pod is still Running")
    validate_calico_pods_running(ssh_connection, "the invalid CIDR patch")

    get_logger().log_test_case_step("Verify a new pod is addressed from the original pool")
    pod_ip = start_busybox_pod(request, ssh_connection, "neg-cidr-test", busybox_image)
    validate_equals(tested_pool.contains_ip(pod_ip), True, f"Pod address {pod_ip} is inside the original pool {tested_pool.get_cidr()}")


@mark.p2
def test_conflicting_ip_family_override(request: FixtureRequest):
    """Verify adding an IP pool of the other IP family to a single-stack cluster does not break pod networking.

    The operator may reject the pool or report Degraded; that is reported for
    information only, because it differs between builds. The required behaviour is that
    the Calico pods keep running and new pods are still addressed from the original pool.

    Preconditions:
        - The cluster is single-stack (IPv4 or IPv6)
        - Calico operator is installed and healthy

    Setup:
        - Sync the busybox test image and copy the local registry pull secret
        - Record the Installation CR IP pools

    Test Steps:
        1. Verify the cluster is single-stack
        2. Add an IP pool of the other IP family to the Installation CR
        3. Verify every calico-system pod is still Running
        4. Verify a new pod is addressed from the original pool

    Teardown:
        - Delete the test pod
        - Restore the original Installation CR IP pools
        - Remove the busybox test image from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    busybox_image = sync_test_image(request, ssh_connection, BUSYBOX_IMAGE_NAME, BUSYBOX_IMAGE_TAG)
    get_logger().log_setup_step(f"Copy the local registry pull secret to the {TEST_NAMESPACE} namespace")
    KubectlCreateSecretsKeywords(ssh_connection).copy_secret_between_namespaces(REGISTRY_LOCAL_SECRET, CALICO_SYSTEM_NAMESPACE, TEST_NAMESPACE)
    get_logger().log_setup_step("Record the Installation CR IP pools")
    restore_ip_pools_on_teardown(request, ssh_connection)

    get_logger().log_test_case_step("Verify the cluster is single-stack")
    installation = KubectlGetInstallationKeywords(ssh_connection).get_installation()
    ip_family = installation.get_ip_family()
    if ip_family == "dual":
        fail("The cluster is dual-stack, so no IP pool of a conflicting family can be added; this scenario needs a single-stack cluster")
    tested_pool = select_tested_ip_pool(ssh_connection)
    conflicting_cidr = CONFLICTING_POOL_CIDR[tested_pool.get_ip_version()]

    get_logger().log_test_case_step(f"Add the IP pool {conflicting_cidr} of the other IP family to the Installation CR")
    KubectlPatchInstallationKeywords(ssh_connection).replace_ip_pools(installation.get_ip_pools_json_with_added_pool(CONFLICTING_POOL_NAME, conflicting_cidr))
    get_logger().log_info(f"TigeraStatus after the conflicting pool (for information): {KubectlGetTigeraStatusKeywords(ssh_connection).get_tigerastatus()}")

    get_logger().log_test_case_step("Verify every calico-system pod is still Running")
    validate_calico_pods_running(ssh_connection, "adding the conflicting IP pool")

    get_logger().log_test_case_step("Verify a new pod is addressed from the original pool")
    pod_ip = start_busybox_pod(request, ssh_connection, "neg-conflict-test", busybox_image)
    validate_equals(tested_pool.contains_ip(pod_ip), True, f"Pod address {pod_ip} is inside the original pool {tested_pool.get_cidr()}")


@mark.p2
def test_operator_does_not_revert_calicoctl_changes(request: FixtureRequest):
    """Verify the operator does not revert a calicoctl change to an operator-managed IP pool.

    The Calico operator does not reconcile a direct calicoctl edit of a managed IP pool
    back to the Installation CR value, so a natOutgoing change made with calicoctl stays
    until it is changed back.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Sync the calicoctl image that matches the installed Calico release
        - Create the calicoctl RBAC resources if they are missing
        - Record the natOutgoing value of the operator-managed IP pool

    Test Steps:
        1. Toggle natOutgoing on the IP pool with calicoctl
        2. Verify the change is kept for the whole observation window
        3. Verify the Calico operator is healthy

    Teardown:
        - Restore the original natOutgoing value with calicoctl
        - Delete the calicoctl pod, and the calicoctl RBAC resources if the test created them
        - Remove the calicoctl image from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    calicoctl_image = sync_test_image(request, ssh_connection, CALICOCTL_IMAGE_NAME, KubectlCalicoNodeKeywords(ssh_connection).get_calico_release())
    calicoctl_keywords = KubectlCalicoctlKeywords(ssh_connection)

    get_logger().log_setup_step("Create the calicoctl ServiceAccount, ClusterRole and ClusterRoleBinding if missing")
    created_rbac = calicoctl_keywords.setup_calicoctl_rbac()

    def cleanup_calicoctl() -> None:
        get_logger().log_teardown_step("Delete the calicoctl pod and the RBAC resources the test created")
        KubectlCalicoctlKeywords(ssh_connection).teardown_calicoctl(delete_rbac=created_rbac)

    request.addfinalizer(cleanup_calicoctl)

    get_logger().log_setup_step("Record the natOutgoing value of the operator-managed IP pool")
    # The operator names the Calico IP pool after the Installation CR pool.
    pool_name = select_tested_ip_pool(ssh_connection).get_name()
    original_nat_outgoing = calicoctl_keywords.get_ippools(calicoctl_image).get_ippool_by_name(pool_name).get_nat_outgoing()
    toggled_nat_outgoing = not original_nat_outgoing
    get_logger().log_info(f"IP pool {pool_name} natOutgoing before the change: {original_nat_outgoing}")

    def restore_nat_outgoing() -> None:
        get_logger().log_teardown_step(f"Restore natOutgoing={original_nat_outgoing} on IP pool {pool_name}")
        KubectlCalicoctlKeywords(ssh_connection).patch_ippool(calicoctl_image, pool_name, {"spec": {"natOutgoing": original_nat_outgoing}})

    request.addfinalizer(restore_nat_outgoing)

    get_logger().log_test_case_step(f"Set natOutgoing={toggled_nat_outgoing} on IP pool {pool_name} with calicoctl")
    calicoctl_keywords.patch_ippool(calicoctl_image, pool_name, {"spec": {"natOutgoing": toggled_nat_outgoing}})

    get_logger().log_test_case_step(f"Verify the change is kept for {OPERATOR_RECONCILE_OBSERVATION_SECONDS}s")
    calicoctl_keywords.validate_ippool_nat_outgoing_unchanged(calicoctl_image, pool_name, toggled_nat_outgoing, OPERATOR_RECONCILE_OBSERVATION_SECONDS, OPERATOR_RECONCILE_POLLING_SECONDS)

    get_logger().log_test_case_step("Verify the Calico operator is healthy")
    KubectlGetTigeraStatusKeywords(ssh_connection).validate_healthy()
