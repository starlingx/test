"""Calico operator customization tests."""

import ipaddress
import json

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import fail, validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords
from keywords.k8s.calico.kubectl_create_ippool_keywords import KubectlCreateIppoolKeywords
from keywords.k8s.calico.kubectl_get_installation_keywords import KubectlGetInstallationKeywords
from keywords.k8s.calico.kubectl_get_ippools_keywords import KubectlGetIPPoolsKeywords
from keywords.k8s.calico.kubectl_get_tigerastatus_keywords import KubectlGetTigeraStatusKeywords
from keywords.k8s.calico.kubectl_patch_installation_keywords import KubectlPatchInstallationKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_pod_connectivity_keywords import KubectlPodConnectivityKeywords
from keywords.k8s.pods.kubectl_run_pod_keywords import KubectlRunPodKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords

NETWORKING_IMAGES_MANIFEST = "networking-tests"
BUSYBOX_IMAGE_NAME = "busybox"
BUSYBOX_IMAGE_TAG = "1.36.1"
REGISTRY_LOCAL_SECRET = "registry-local-secret"
CALICO_SYSTEM_NAMESPACE = "calico-system"
TEST_NAMESPACE = "default"

# Secondary pool candidates are taken from the documentation ranges (RFC 5737 for IPv4,
# RFC 3849 for IPv6), which are reserved and never assigned to a real network. The first
# candidate that overlaps no Calico pool and no platform address pool is used.
SECONDARY_POOL_CANDIDATES = {
    4: ["198.51.100.0/24", "203.0.113.0/24", "192.0.2.0/24"],
    6: ["2001:db8:ca1c:1::/112", "2001:db8:ca1c:2::/112"],
}
SECONDARY_POOL_BLOCK_SIZE = {4: 26, 6: 122}
CUSTOM_MTU = 2000
# Unlocking a controller can raise 750.006 (a configuration change requires an application
# reapply); it is a transient platform alarm that is not caused by the Calico change under test.
CONFIG_REAPPLY_ALARM_ID = "750.006"
UNLOCK_ACCEPTED_TIMEOUT_SECONDS = 600
POD_RUNNING_TIMEOUT_SECONDS = 120
IPPOOL_VISIBLE_TIMEOUT_SECONDS = 60
MTU_RECONCILE_TIMEOUT_SECONDS = 60
NODE_RECOVERY_TIMEOUT_SECONDS = 900
NODE_OFFLINE_TIMEOUT_SECONDS = 600
CALICO_PODS_RUNNING_TIMEOUT_SECONDS = 300
OPERATOR_HEALTHY_TIMEOUT_SECONDS = 300


def prepare_busybox_image(request: FixtureRequest, ssh_connection: SSHConnection) -> str:
    """Sync the busybox test image to the local registry and make it pullable in the test namespace.

    Args:
        request (FixtureRequest): The pytest request, used to register the image cleanup.
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The local registry reference of the busybox image.
    """
    get_logger().log_setup_step("Sync the busybox test image to the local registry")
    docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)

    def cleanup_busybox_image() -> None:
        get_logger().log_teardown_step("Remove the busybox test image from the controller")
        docker_sync_keywords.remove_image_from_manifest(BUSYBOX_IMAGE_NAME, BUSYBOX_IMAGE_TAG, NETWORKING_IMAGES_MANIFEST)

    request.addfinalizer(cleanup_busybox_image)
    busybox_image = docker_sync_keywords.sync_image_from_manifest(BUSYBOX_IMAGE_NAME, BUSYBOX_IMAGE_TAG, NETWORKING_IMAGES_MANIFEST)

    get_logger().log_setup_step(f"Copy the local registry pull secret to the {TEST_NAMESPACE} namespace")
    KubectlCreateSecretsKeywords(ssh_connection).copy_secret_between_namespaces(REGISTRY_LOCAL_SECRET, CALICO_SYSTEM_NAMESPACE, TEST_NAMESPACE)
    return busybox_image


def select_secondary_pool_cidr(ssh_connection: SSHConnection, ip_version: int) -> str:
    """Select a secondary pool CIDR that overlaps no Calico pool and no platform address pool.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        ip_version (int): The IP version of the secondary pool (4 or 6).

    Returns:
        str: The selected CIDR.
    """
    calico_pool_cidrs = KubectlGetInstallationKeywords(ssh_connection).get_installation().get_ip_pool_cidrs()
    calico_pool_cidrs.extend(pool.get_cidr() for pool in KubectlGetIPPoolsKeywords(ssh_connection).get_ippools().get_ippools())
    platform_networks = [pool.get_network() for pool in SystemAddrpoolListKeywords(ssh_connection).get_system_addrpool_list().get_addrpool()]

    for candidate in SECONDARY_POOL_CANDIDATES[ip_version]:
        candidate_network = ipaddress.ip_network(candidate)
        overlaps_calico_pool = any(candidate_network.overlaps(ipaddress.ip_network(cidr, strict=False)) for cidr in calico_pool_cidrs if ipaddress.ip_network(cidr, strict=False).version == ip_version)
        overlaps_platform_network = any(ipaddress.ip_address(network) in candidate_network for network in platform_networks if ipaddress.ip_address(network).version == ip_version)
        if not overlaps_calico_pool and not overlaps_platform_network:
            get_logger().log_info(f"Selected secondary pool CIDR {candidate}; Calico pools {calico_pool_cidrs}; platform networks {platform_networks}")
            return candidate

    # fail() raises, so the function never returns without a CIDR.
    fail(f"Every secondary pool candidate {SECONDARY_POOL_CANDIDATES[ip_version]} overlaps a Calico pool {calico_pool_cidrs} or a platform network {platform_networks}")


@mark.p2
def test_custom_ippool_cidr_post_install(request: FixtureRequest):
    """Verify a secondary Calico IP pool added after install assigns pod addresses.

    Adds a secondary IP pool of the same IP family as the default pool, starts a pod
    pinned to it and checks the pod address comes from the new pool and that the pod
    can reach a pod on the default pool. Does not test removing the default pool.

    Preconditions:
        - Calico operator is installed and healthy

    Setup:
        - Sync the busybox test image to the local registry
        - Copy the local registry pull secret to the default namespace
        - Select a secondary pool CIDR that overlaps no existing pool or platform network

    Test Steps:
        1. Create the secondary IP pool
        2. Verify the secondary pool is listed and the operator stays healthy
        3. Start a pod pinned to the secondary pool and verify its address is in the pool
        4. Verify the pinned pod can ping a pod on the default pool

    Teardown:
        - Delete both pods
        - Delete the secondary IP pool
        - Remove the busybox test image from the controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    busybox_image = prepare_busybox_image(request, ssh_connection)

    get_logger().log_setup_step("Select a secondary pool CIDR that overlaps no existing pool or platform network")
    # On a dual-stack cluster the IPv4 family is exercised.
    ip_version = 6 if KubectlGetInstallationKeywords(ssh_connection).get_installation().get_ip_family() == "ipv6" else 4
    secondary_cidr = select_secondary_pool_cidr(ssh_connection, ip_version)
    pool_name = "custom-test-pool"
    pinned_pod_name = "custom-cidr-test"
    default_pool_pod_name = "custom-cidr-test2"

    # Finalizers run last-in first-out: the pool cleanup is registered first so it runs after the pods are gone.
    def cleanup_pool() -> None:
        get_logger().log_teardown_step(f"Delete IP pool {pool_name}")
        KubectlDeleteResourceKeywords(ssh_connection).delete_resource("ippool", pool_name)

    request.addfinalizer(cleanup_pool)

    def cleanup_pods() -> None:
        get_logger().log_teardown_step(f"Delete pods {pinned_pod_name} and {default_pool_pod_name}")
        delete_pods_keywords = KubectlDeletePodsKeywords(ssh_connection)
        delete_pods_keywords.cleanup_pod(pinned_pod_name, namespace=TEST_NAMESPACE)
        delete_pods_keywords.cleanup_pod(default_pool_pod_name, namespace=TEST_NAMESPACE)

    request.addfinalizer(cleanup_pods)

    get_logger().log_test_case_step(f"Create the secondary IP pool {secondary_cidr}")
    KubectlCreateIppoolKeywords(ssh_connection).create_ippool(pool_name, secondary_cidr, block_size=SECONDARY_POOL_BLOCK_SIZE[ip_version])

    get_logger().log_test_case_step("Verify the secondary pool is listed and the operator stays healthy")
    ippools_keywords = KubectlGetIPPoolsKeywords(ssh_connection)

    def is_secondary_pool_listed() -> bool:
        return ippools_keywords.get_ippools().has_ippool_with_cidr(secondary_cidr)

    validate_equals_with_retry(is_secondary_pool_listed, True, f"IP pool with CIDR {secondary_cidr} is listed", timeout=IPPOOL_VISIBLE_TIMEOUT_SECONDS)
    KubectlGetTigeraStatusKeywords(ssh_connection).validate_healthy()

    get_logger().log_test_case_step("Start a pod pinned to the secondary pool and verify its address is in the pool")
    pool_annotation = f"cni.projectcalico.org/ipv{ip_version}pools"
    pinned_overrides = {
        "metadata": {"annotations": {pool_annotation: json.dumps([pool_name])}},
        "spec": {"imagePullSecrets": [{"name": REGISTRY_LOCAL_SECRET}]},
    }
    run_pod_keywords = KubectlRunPodKeywords(ssh_connection)
    get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    run_pod_keywords.run_pod(pinned_pod_name, busybox_image, namespace=TEST_NAMESPACE, overrides=pinned_overrides, command=["sleep", "3600"])
    get_pods_keywords.wait_for_pod_status(pinned_pod_name, "Running", namespace=TEST_NAMESPACE, timeout=POD_RUNNING_TIMEOUT_SECONDS)
    pinned_pod_ip = get_pods_keywords.get_pods(namespace=TEST_NAMESPACE).get_pod(pinned_pod_name).get_ip()
    get_logger().log_info(f"Pod {pinned_pod_name} address: {pinned_pod_ip}")
    validate_equals(ipaddress.ip_address(pinned_pod_ip) in ipaddress.ip_network(secondary_cidr), True, f"Pod address {pinned_pod_ip} is inside the secondary pool {secondary_cidr}")

    get_logger().log_test_case_step("Verify the pinned pod can ping a pod on the default pool")
    default_pool_overrides = {"spec": {"imagePullSecrets": [{"name": REGISTRY_LOCAL_SECRET}]}}
    run_pod_keywords.run_pod(default_pool_pod_name, busybox_image, namespace=TEST_NAMESPACE, overrides=default_pool_overrides, command=["sleep", "3600"])
    get_pods_keywords.wait_for_pod_status(default_pool_pod_name, "Running", namespace=TEST_NAMESPACE, timeout=POD_RUNNING_TIMEOUT_SECONDS)
    default_pool_pod_ip = get_pods_keywords.get_pods(namespace=TEST_NAMESPACE).get_pod(default_pool_pod_name).get_ip()
    ping_output = KubectlPodConnectivityKeywords(ssh_connection).ping_from_pod(pinned_pod_name, default_pool_pod_ip, namespace=TEST_NAMESPACE)
    validate_str_contains(ping_output, " 0% packet loss", f"Ping from {pinned_pod_ip} to {default_pool_pod_ip} has no packet loss")


def set_custom_mtu(request: FixtureRequest, ssh_connection: SSHConnection) -> None:
    """Set a custom MTU on the Installation CR and wait for the operator to report it.

    Registers a finalizer that removes the custom MTU. The removal is a merge patch with a
    null value, which is a no-op when the MTU is not set, so it cannot mask a test failure.

    Args:
        request (FixtureRequest): The pytest request, used to register the MTU revert.
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """

    def cleanup_custom_mtu() -> None:
        get_logger().log_teardown_step("Remove the custom MTU from the Installation CR")
        KubectlPatchInstallationKeywords(LabConnectionKeywords().get_active_controller_ssh()).patch_installation_merge({"spec": {"calicoNetwork": {"mtu": None}}})

    request.addfinalizer(cleanup_custom_mtu)

    get_logger().log_setup_step(f"Set a custom MTU of {CUSTOM_MTU} on the Installation CR")
    KubectlPatchInstallationKeywords(ssh_connection).patch_installation_merge({"spec": {"calicoNetwork": {"mtu": CUSTOM_MTU}}})
    installation_keywords = KubectlGetInstallationKeywords(ssh_connection)

    def get_mtu() -> int:
        return installation_keywords.get_installation().get_mtu()

    validate_equals_with_retry(get_mtu, CUSTOM_MTU, f"Installation CR reports MTU {CUSTOM_MTU}", timeout=MTU_RECONCILE_TIMEOUT_SECONDS)


def register_standby_unlock(request: FixtureRequest, standby_name: str) -> None:
    """Register a finalizer that unlocks the standby controller if the test leaves it locked.

    A failed reboot or unlock would otherwise leave the lab with a locked controller.

    Args:
        request (FixtureRequest): The pytest request, used to register the recovery.
        standby_name (str): The standby controller name.
    """

    def unlock_standby_if_locked() -> None:
        get_logger().log_teardown_step(f"Unlock {standby_name} if the test left it locked")
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        if SystemHostListKeywords(ssh_connection).get_system_host_list().get_host(standby_name).get_administrative() == "locked":
            SystemHostLockKeywords(ssh_connection).unlock_host(standby_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT_SECONDS, exclude_alarm_ids=[CONFIG_REAPPLY_ALARM_ID])

    request.addfinalizer(unlock_standby_if_locked)


def validate_mtu_persisted(disruption: str) -> None:
    """Validate the custom MTU is still set and the Calico operator is healthy after a disruption.

    Args:
        disruption (str): The disruption that just completed, used in the validation messages.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    validate_equals(KubectlGetInstallationKeywords(ssh_connection).get_installation().get_mtu(), CUSTOM_MTU, f"Installation CR keeps MTU {CUSTOM_MTU} after {disruption}")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status("Running", namespace=CALICO_SYSTEM_NAMESPACE, timeout=CALICO_PODS_RUNNING_TIMEOUT_SECONDS)
    KubectlGetTigeraStatusKeywords(ssh_connection).validate_healthy(timeout=OPERATOR_HEALTHY_TIMEOUT_SECONDS)


@mark.p2
@mark.lab_has_standby_controller
def test_custom_mtu_persists_graceful_reboot(request: FixtureRequest):
    """Verify a custom MTU persists through a graceful reboot of the standby controller.

    Preconditions:
        - A standby controller is present
        - Calico operator is installed and healthy

    Setup:
        - Set a custom MTU on the Installation CR

    Test Steps:
        1. Lock, reboot and unlock the standby controller
        2. Verify the MTU is unchanged and the operator is healthy

    Teardown:
        - Unlock the standby controller if the test left it locked
        - Remove the custom MTU from the Installation CR
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    set_custom_mtu(request, ssh_connection)

    standby_name = SystemHostListKeywords(ssh_connection).get_standby_controller().get_host_name()
    register_standby_unlock(request, standby_name)
    get_logger().log_test_case_step(f"Lock, reboot and unlock the standby controller {standby_name}")
    lock_keywords = SystemHostLockKeywords(ssh_connection)
    lock_keywords.lock_host(standby_name)
    SystemHostRebootKeywords(ssh_connection).host_reboot(standby_name)
    lock_keywords.unlock_host(standby_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT_SECONDS, exclude_alarm_ids=[CONFIG_REAPPLY_ALARM_ID])

    get_logger().log_test_case_step("Verify the MTU is unchanged and the operator is healthy")
    validate_mtu_persisted("a graceful reboot")


@mark.p2
@mark.lab_has_standby_controller
def test_custom_mtu_persists_ungraceful_reboot(request: FixtureRequest):
    """Verify a custom MTU persists through an ungraceful reboot of the standby controller.

    The standby controller is rebooted with 'reboot -f', which skips the clean service
    shutdown.

    Preconditions:
        - A standby controller is present
        - Calico operator is installed and healthy

    Setup:
        - Set a custom MTU on the Installation CR

    Test Steps:
        1. Force reboot the standby controller and wait for it to recover
        2. Verify the MTU is unchanged and the operator is healthy

    Teardown:
        - Remove the custom MTU from the Installation CR
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    set_custom_mtu(request, ssh_connection)

    host_list_keywords = SystemHostListKeywords(ssh_connection)
    standby_name = host_list_keywords.get_standby_controller().get_host_name()
    get_logger().log_test_case_step(f"Force reboot the standby controller {standby_name} and wait for it to recover")
    # The reboot drops the SSH session to the standby, so the no-wait variant is used and
    # recovery is confirmed from the active controller instead.
    SystemHostRebootKeywords(LabConnectionKeywords().get_ssh_for_hostname(standby_name)).host_force_reboot_no_wait()
    host_list_keywords.wait_for_host_availability(standby_name, ["offline"], timeout=NODE_OFFLINE_TIMEOUT_SECONDS)
    host_list_keywords.wait_for_host_availability(standby_name, ["available"], timeout=NODE_RECOVERY_TIMEOUT_SECONDS)

    get_logger().log_test_case_step("Verify the MTU is unchanged and the operator is healthy")
    validate_mtu_persisted("an ungraceful reboot")


@mark.p2
@mark.lab_has_standby_controller
def test_custom_mtu_persists_lock_unlock(request: FixtureRequest):
    """Verify a custom MTU persists through a lock and unlock of the standby controller.

    Preconditions:
        - A standby controller is present
        - Calico operator is installed and healthy

    Setup:
        - Set a custom MTU on the Installation CR

    Test Steps:
        1. Lock and unlock the standby controller
        2. Verify the MTU is unchanged and the operator is healthy

    Teardown:
        - Unlock the standby controller if the test left it locked
        - Remove the custom MTU from the Installation CR
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    set_custom_mtu(request, ssh_connection)

    standby_name = SystemHostListKeywords(ssh_connection).get_standby_controller().get_host_name()
    register_standby_unlock(request, standby_name)
    get_logger().log_test_case_step(f"Lock and unlock the standby controller {standby_name}")
    lock_keywords = SystemHostLockKeywords(ssh_connection)
    lock_keywords.lock_host(standby_name)
    lock_keywords.unlock_host(standby_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT_SECONDS, exclude_alarm_ids=[CONFIG_REAPPLY_ALARM_ID])

    get_logger().log_test_case_step("Verify the MTU is unchanged and the operator is healthy")
    validate_mtu_persisted("a lock and unlock")


@mark.p2
@mark.lab_has_standby_controller
def test_custom_mtu_persists_swact(request: FixtureRequest):
    """Verify a custom MTU persists through a swact of the controllers.

    Preconditions:
        - A standby controller is present
        - Calico operator is installed and healthy

    Setup:
        - Set a custom MTU on the Installation CR

    Test Steps:
        1. Swact the controllers
        2. Verify the MTU is unchanged and the operator is healthy

    Teardown:
        - Remove the custom MTU from the Installation CR
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    set_custom_mtu(request, ssh_connection)

    get_logger().log_test_case_step("Swact the controllers")
    SystemHostSwactKeywords(ssh_connection).host_swact()

    get_logger().log_test_case_step("Verify the MTU is unchanged and the operator is healthy")
    validate_mtu_persisted("a swact")
