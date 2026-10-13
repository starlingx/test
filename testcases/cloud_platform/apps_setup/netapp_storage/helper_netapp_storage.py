"""Helpers shared by the netapp-storage protocol test modules (NFS, iSCSI and FC).

The netapp-storage application exposes one StorageClass per ONTAP driver, and a
platform disruption is exercised the same way for the three protocols: check the
NetApp stack is healthy, keep a pod writing to a NetApp volume across the
disruption, then check the stack is healthy again. Only the capability changes,
and from it the ONTAP driver, the StorageClass and the access mode of the volume.
The flow therefore lives here once and each protocol module supplies its
capability, so that the per-protocol lab markers stay on the test functions.
"""

from pytest import FixtureRequest

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.k8s.continuous_write.kubectl_continuous_write_keywords import KubectlContinuousWriteKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.storageclass.storage_capability_keywords import StorageCapabilityKeywords

NETAPP_NFS_CAPABILITY = "netapp-nfs"
NETAPP_ISCSI_CAPABILITY = "netapp-iscsi"
NETAPP_FC_CAPABILITY = "netapp-fc"
TRIDENT_NAMESPACE = "trident"


def verify_netapp_integrity(ssh_connection: SSHConnection, capability: str) -> None:
    """Verify the netapp-storage stack is healthy end to end for a capability.

    Checks the three layers that have to be up for a NetApp volume to be usable: the
    platform application is applied, the Trident pods are healthy, and the ONTAP
    backend serving the capability reports lastOperationStatus Success.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        capability (str): one of 'netapp-nfs', 'netapp-iscsi' or 'netapp-fc'.
    """
    netapp_storage_app_name = ConfigurationManager.get_app_config().get_netapp_storage_app_name()

    get_logger().log_info(f"Verify the {netapp_storage_app_name} application is applied")
    SystemApplicationListKeywords(ssh_connection).validate_app_status(netapp_storage_app_name, SystemApplicationStatusEnum.APPLIED.value)

    get_logger().log_info(f"Verify the pods in the {TRIDENT_NAMESPACE} namespace are healthy")
    HealthKeywords(ssh_connection).validate_pods_health(namespace=TRIDENT_NAMESPACE)

    StorageCapabilityKeywords(ssh_connection).assert_netapp_backend_available(capability)


def reboot_active_controller_with_continuous_write(request: FixtureRequest, capability: str) -> None:
    """Reboot the active controller while a pod keeps writing to a NetApp volume.

    Shared body of the reboot test of the three NetApp protocols. See the calling
    test functions for the per-protocol steps.

    Args:
        request (FixtureRequest): pytest request fixture used to register the teardown.
        capability (str): one of 'netapp-nfs', 'netapp-iscsi' or 'netapp-fc'.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    system_host_reboot_keywords = SystemHostRebootKeywords(ssh_connection)
    continuous_write_keywords = KubectlContinuousWriteKeywords(ssh_connection)
    active_controller_host_name = system_host_list_keywords.get_active_controller().get_host_name()
    standby_controller_host_name = system_host_list_keywords.get_standby_controller().get_host_name()
    previous_uptime = system_host_list_keywords.get_uptime(active_controller_host_name)

    get_logger().log_test_case_step(f"Checking netapp-storage integrity for {capability} before reboot.")
    verify_netapp_integrity(ssh_connection, capability)

    storage_class_name = StorageCapabilityKeywords(ssh_connection).get_storage_class_name(capability)

    get_logger().log_test_case_step(f"Start the {capability} continuous-write pod on {standby_controller_host_name}.")
    get_logger().log_info(f"Active controller to reboot: {active_controller_host_name}; writer pod pinned to standby: {standby_controller_host_name}")
    pod_name, pvc_name = continuous_write_keywords.ensure_continuous_write_pod(capability, node_name=standby_controller_host_name, storage_class_name=storage_class_name)
    request.addfinalizer(lambda: continuous_write_keywords.cleanup_continuous_write_pod(pod_name, pvc_name))

    write_count_before_reboot = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=0)

    get_logger().log_test_case_step(f"Force reboot {active_controller_host_name}.")
    system_host_reboot_keywords.host_force_reboot()
    system_host_reboot_keywords.wait_for_force_reboot(active_controller_host_name, previous_uptime)

    get_logger().log_test_case_step(f"Performing swact back to {active_controller_host_name}.")
    SystemHostSwactKeywords(ssh_connection).ensure_controller_is_active(active_controller_host_name)

    get_logger().log_test_case_step(f"Verify {pod_name} is still Running after the reboot.")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running")

    get_logger().log_test_case_step(f"Verify {pod_name} kept writing to the {capability} volume.")
    write_count_after_reboot = continuous_write_keywords.wait_for_write_progress(pod_name, previous_count=write_count_before_reboot)
    get_logger().log_info(f"{pod_name} write-cycle count advanced from {write_count_before_reboot} to {write_count_after_reboot} across the reboot")

    get_logger().log_test_case_step(f"Checking netapp-storage integrity for {capability} after reboot.")
    verify_netapp_integrity(ssh_connection, capability)
