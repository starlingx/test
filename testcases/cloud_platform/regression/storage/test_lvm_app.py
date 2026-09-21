from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.host.system_host_disk_keywords import SystemHostDiskKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lvg_keywords import SystemHostLvgKeywords
from keywords.cloud_platform.system.host.system_host_pv_keywords import SystemHostPvKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords
from keywords.k8s.volumesnapshots.kubectl_get_volumesnapshots_keywords import KubectlGetVolumesnapshotsKeywords
from keywords.linux.lvm.lvs_keywords import LvsKeywords

# Common constants, shared by all lvm-csi scenarios (cgts-vg and dedicated VG).
LVM_CSI_APP = "lvm-csi"
LVM_CSI_POOL = "lvmcsi-pool"
TOPOLVM_NAMESPACE = "topolvm-system"
REMOTE_DIR = "/home/sysadmin"

# topolvm pod name prefixes. The scheduler is only deployed on multi-node systems.
TOPOLVM_POD_PREFIXES = ["lvm-csi-topolvm-controller", "lvm-csi-topolvm-lvmd", "lvm-csi-topolvm-node", "lvm-csi-topolvm-scheduler"]

# Constants specific to the cgts-vg (shared VG) scenario.
LVM_VG = "cgts-vg"
# PVC/Pod workload for the cgts-vg scenario (names, local resource manifests and remote paths).
CGTS_VG_WORKLOAD = {
    "pvc_name": "lvm-pvc-cgts-vg",
    "pvc_resource": "resources/cloud_platform/storage/lvm_csi/lvm-pvc-cgts-vg.yaml",
    "pvc_yaml_path": f"{REMOTE_DIR}/lvm-pvc-cgts-vg.yaml",
    "pod_name": "lvm-pod-cgts-vg",
    "pod_resource": "resources/cloud_platform/storage/lvm_csi/lvm-pod-cgts-vg.yaml",
    "pod_yaml_path": f"{REMOTE_DIR}/lvm-pod-cgts-vg.yaml",
}

# Constants specific to the dedicated-disk scenario (VG created on a spare disk; storage class name matches the VG name).
DEDICATED_VG = "lvm-provisioner"
# PVC/Pod workload for the dedicated-disk scenario (names, local resource manifests and remote paths).
DEDICATED_WORKLOAD = {
    "pvc_name": "lvm-pvc-lvm-provisioner",
    "pvc_resource": "resources/cloud_platform/storage/lvm_csi/lvm-pvc-lvm-provisioner.yaml",
    "pvc_yaml_path": f"{REMOTE_DIR}/lvm-pvc-lvm-provisioner.yaml",
    "pod_name": "lvm-pod-lvm-provisioner",
    "pod_resource": "resources/cloud_platform/storage/lvm_csi/lvm-pod-lvm-provisioner.yaml",
    "pod_yaml_path": f"{REMOTE_DIR}/lvm-pod-lvm-provisioner.yaml",
}

# Constants specific to the create-and-restore snapshot scenario (lvm-csi thin).
# The lvm-csi (TopoLVM) VolumeSnapshotClass shared by both the cgts-vg and the dedicated scenarios.
LVM_CSI_SNAPSHOT_CLASS = "lvmcsi-snapshot"
# The file written to the source PVC and expected to survive into the restored PVC.
SNAPSHOT_TEST_FILE = "/mnt1/test.txt"

# --- Snapshot workload for the shared cgts-vg (thin) storage class ---
# Source PVC/Pod (persistent workload: keeps a file instead of deleting it, unlike CGTS_VG_WORKLOAD).
CGTS_VG_SNAPSHOT_SOURCE_WORKLOAD = {
    "pvc_name": "lvm-snap-pvc-cgts-vg",
    "pod_name": "lvm-snap-pod-cgts-vg",
    "resource": "resources/cloud_platform/storage/lvm_csi/lvm-snapshot-pod-cgts-vg.yaml",
    "yaml_path": f"{REMOTE_DIR}/lvm-snapshot-pod-cgts-vg.yaml",
}
# VolumeSnapshotClass + VolumeSnapshot manifest.
CGTS_VG_SNAPSHOT_WORKLOAD = {
    "snapshot_name": "lvmcsi-pvc-snapshot",
    "resource": "resources/cloud_platform/storage/lvm_csi/lvm-csi-snapshot-cgts-vg.yaml",
    "yaml_path": f"{REMOTE_DIR}/lvm-csi-snapshot-cgts-vg.yaml",
}
# Restore PVC/Pod (PVC created from the VolumeSnapshot dataSource).
CGTS_VG_SNAPSHOT_RESTORE_WORKLOAD = {
    "pvc_name": "lvm-snap-restore-pvc-cgts-vg",
    "pod_name": "lvm-snap-restore-pod-cgts-vg",
    "resource": "resources/cloud_platform/storage/lvm_csi/lvm-snapshot-restore-pod-cgts-vg.yaml",
    "yaml_path": f"{REMOTE_DIR}/lvm-snapshot-restore-pod-cgts-vg.yaml",
}

# --- Snapshot workload for the dedicated (lvm-provisioner, thin) storage class ---
DEDICATED_SNAPSHOT_SOURCE_WORKLOAD = {
    "pvc_name": "lvm-snap-pvc-lvm-provisioner",
    "pod_name": "lvm-snap-pod-lvm-provisioner",
    "resource": "resources/cloud_platform/storage/lvm_csi/lvm-snapshot-pod-lvm-provisioner.yaml",
    "yaml_path": f"{REMOTE_DIR}/lvm-snapshot-pod-lvm-provisioner.yaml",
}
DEDICATED_SNAPSHOT_WORKLOAD = {
    "snapshot_name": "lvmcsi-pvc-snapshot-dedicated",
    "resource": "resources/cloud_platform/storage/lvm_csi/lvm-csi-snapshot-lvm-provisioner.yaml",
    "yaml_path": f"{REMOTE_DIR}/lvm-csi-snapshot-lvm-provisioner.yaml",
}
DEDICATED_SNAPSHOT_RESTORE_WORKLOAD = {
    "pvc_name": "lvm-snap-restore-pvc-lvm-provisioner",
    "pod_name": "lvm-snap-restore-pod-lvm-provisioner",
    "resource": "resources/cloud_platform/storage/lvm_csi/lvm-snapshot-restore-pod-lvm-provisioner.yaml",
    "yaml_path": f"{REMOTE_DIR}/lvm-snapshot-restore-pod-lvm-provisioner.yaml",
}


def _setup_lvm() -> list:
    """
    Perform the lvm-csi test setup and capture the active alarms snapshot.

    - Validate that all hosts are healthy
    - Validate the 'lvm-csi' application is in the initial 'uploaded' state
    - Validate the 'lvm' storage backend is not already configured
    - Capture a snapshot of the active alarms

    Returns:
        list: the snapshot of active alarms captured before the test.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    health_keywords = HealthKeywords(ssh_connection)
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
    alarm_list_keywords = AlarmListKeywords(ssh_connection)

    get_logger().log_setup_step("Validating that all hosts are healthy")
    health_keywords.validate_hosts_health()

    get_logger().log_setup_step(f"Validate the '{LVM_CSI_APP}' application is in the initial 'uploaded' state")
    app_status = application_show_keywords.get_system_application_show(LVM_CSI_APP).get_system_application_object().get_status()
    validate_equals(app_status, "uploaded", f"'{LVM_CSI_APP}' application should be in the 'uploaded' state before the test.")

    get_logger().log_setup_step("Validate the 'lvm' storage backend is not already configured")
    is_lvm_configured = system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm")
    validate_equals(is_lvm_configured, False, "'lvm' backend should not be configured before the test.")

    get_logger().log_setup_step("Capture a snapshot of the active alarms")
    alarms_before = alarm_list_keywords.alarm_list()

    return alarms_before


def _apply_lvm_csi_cgts_vg():
    """
    - Add the 'lvm' storage backend
    - Capture the cgts-vg total size before assigning the lvm-csi function
    - Add the 'lvm-csi' function to the cgts-vg local volume group
    - Wait for the 'lvm-csi' application to be applied
    - Verify the 'lvmcsi-pool' thin pool exists
    - Verify the cgts-vg attributes (name, state, function, type, pool size)
    - Verify the cgts-vg available size dropped to ~50% after provisioning the thin pool
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    lvs_keywords = LvsKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Add 'lvm' as storage backend")
    system_storage_backend_keywords.system_storage_backend_add(backend="lvm", confirmed=True)
    validate_equals(system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"), True, "'lvm' backend should be configured.")

    get_logger().log_test_case_step(f"Capture the '{LVM_VG}' available size before assigning the lvm-csi function")
    avail_size_before = float(system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg().get_avail_size())

    get_logger().log_test_case_step(f"Add the '{LVM_CSI_APP}' function to '{LVM_VG}' on {active_controller}")
    system_host_lvg_keywords.system_host_lvg_modify(host_id=active_controller, lvg_name=LVM_VG, lvm_function="lvm-csi")

    get_logger().log_test_case_step(f"Wait for the '{LVM_CSI_APP}' application to be applied")
    application_show_keywords.validate_app_progress_contains(LVM_CSI_APP, "completed")
    application_show_keywords.validate_app_status(LVM_CSI_APP, "applied")

    get_logger().log_test_case_step(f"Verify the '{LVM_CSI_POOL}' thin pool exists")
    lvmcsi_pool = lvs_keywords.get_lvs().get_logical_volume(LVM_CSI_POOL)
    validate_equals(lvmcsi_pool.is_thin_pool(), True, f"'{LVM_CSI_POOL}' should be a thin pool.")

    get_logger().log_test_case_step(f"Verify the '{LVM_VG}' local volume group attributes on {active_controller}.")
    lvg = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg()
    validate_equals(lvg.get_lvg_name(), LVM_VG, f"LVG Name should be '{LVM_VG}'.")
    validate_equals(lvg.get_state(), "provisioned", f"'{LVM_VG}' state should be 'provisioned'.")
    validate_equals(lvg.get_lvm_function(), "lvm-csi", f"'{LVM_VG}' function should be 'lvm-csi'.")
    validate_equals(lvg.get_lvm_type(), "thin", f"'{LVM_VG}' type should be 'thin'.")
    pool_size = lvg.get_lvm_pool_size()
    pool_size_value = int(pool_size) if pool_size not in (None, "", "None") else 0
    validate_equals(pool_size_value > 0, True, f"'{LVM_VG}' lvm_pool_size should be greater than 0, got '{pool_size}'.")

    get_logger().log_test_case_step(f"Verify the '{LVM_VG}' available size dropped to ~50% after provisioning the thin pool.")

    def is_avail_size_halved() -> bool:
        # sysinv updates the VG available size asynchronously, so poll until it drops to ~50% (with tolerance).
        current_avail_size = float(system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg().get_avail_size())
        remaining_ratio = (current_avail_size / avail_size_before) if avail_size_before else 0
        get_logger().log_info(f"'{LVM_VG}' available size is {current_avail_size} GiB (was {avail_size_before} GiB, ratio {remaining_ratio:.2%}).")
        return 0.45 <= remaining_ratio <= 0.55

    validate_equals_with_retry(is_avail_size_halved, True, f"'{LVM_VG}' available size to drop to ~50% of {avail_size_before} GiB", timeout=300, polling_sleep_time=10)


def _verify_topolvm_pods_running(ssh_connection: SSHConnection):
    """
    Verify that the topolvm-system pods (including topolvm-scheduler) are Running.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
    """
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Verify the pods in '{TOPOLVM_NAMESPACE}' are Running.")
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=TOPOLVM_POD_PREFIXES, namespace=TOPOLVM_NAMESPACE, timeout=300)


def _create_and_verify_pvc_and_pod(ssh_connection: SSHConnection, workload: dict):
    """
    Create the PVC and Pod, then verify the Pod is Running and the PVC is Bound.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
        workload (dict): the PVC/Pod workload to apply, with keys 'pvc_name', 'pvc_resource',
            'pvc_yaml_path', 'pod_name', 'pod_resource' and 'pod_yaml_path' (e.g. CGTS_VG_WORKLOAD or
            DEDICATED_WORKLOAD).
    """
    file_keywords = FileKeywords(ssh_connection)
    kubectl_apply_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    kubectl_get_pvc_keywords = KubectlGetPvcKeywords(ssh_connection)

    get_logger().log_test_case_step("Create the LVM PVC.")
    file_keywords.upload_file(get_stx_resource_path(workload["pvc_resource"]), workload["pvc_yaml_path"])
    kubectl_apply_keywords.apply_from_yaml(workload["pvc_yaml_path"])

    get_logger().log_test_case_step("Create the Pod that writes to the PVC.")
    file_keywords.upload_file(get_stx_resource_path(workload["pod_resource"]), workload["pod_yaml_path"])
    kubectl_apply_keywords.apply_from_yaml(workload["pod_yaml_path"])

    get_logger().log_test_case_step("Verify the Pod is Running and the PVC is Bound.")
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[workload["pod_name"]], namespace="default", timeout=300)
    kubectl_get_pvc_keywords.wait_for_pvcs_to_reach_status("Bound", pvc_names=[workload["pvc_name"]], namespace="default", timeout=300)


def _verify_lvmcsi_pool_used(ssh_connection: SSHConnection):
    """
    Verify that the 'lvmcsi-pool' thin pool has been used (Data% > 0).

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
    """
    lvs_keywords = LvsKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Verify the '{LVM_CSI_POOL}' has been used (Data% > 0).")
    # Raises TimeoutError if the pool data usage never exceeds the threshold within the timeout.
    lvs_keywords.wait_for_lv_data_percent_above(LVM_CSI_POOL, threshold=0.0, timeout=180, polling_interval=10)


def _verify_no_new_alarms(ssh_connection: SSHConnection, alarms_before: list):
    """
    Verify that no new alarms appeared since the snapshot taken during setup.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
        alarms_before (list): the snapshot of active alarms captured during setup.
    """
    get_logger().log_test_case_step("Verify no new alarms appeared during the test.")
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    alarm_list_keywords.set_timeout_in_seconds(300)
    alarm_list_keywords.wait_for_all_alarms_cleared_excluding(excluded_alarms=alarms_before, stable_checks=3, tolerate_query_failure=True)


def _create_and_restore_snapshot(ssh_connection: SSHConnection, source_workload: dict, snapshot_workload: dict, restore_workload: dict):
    """
    Create a snapshot of an lvm-csi thin PVC and restore it into a new PVC/Pod.

    Mirrors the dell-storage snapshot flow on the lvm-csi (TopoLVM) thin storage class. Works for both
    the shared cgts-vg and the dedicated (lvm-provisioner) storage classes depending on the workloads
    passed in:
    - Upload the snapshot workload manifests (source Pod/PVC, VolumeSnapshotClass/VolumeSnapshot, restore Pod/PVC)
    - Create the source PVC and Pod and verify the Pod is Running and the PVC is Bound
    - Write a test file to the source PVC and sync it, then verify the file exists
    - Create the VolumeSnapshotClass and VolumeSnapshot and wait for the snapshot to be ready to use
    - Create the restore PVC (from the snapshot dataSource) and Pod, verify the Pod is Running and the PVC is Bound
    - Verify the test file written to the source PVC is present in the restored Pod

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
        source_workload (dict): source PVC/Pod workload (keys 'pvc_name', 'pod_name', 'resource', 'yaml_path').
        snapshot_workload (dict): VolumeSnapshotClass/VolumeSnapshot manifest (keys 'snapshot_name', 'resource', 'yaml_path').
        restore_workload (dict): restore PVC/Pod workload (keys 'pvc_name', 'pod_name', 'resource', 'yaml_path').
    """
    file_keywords = FileKeywords(ssh_connection)
    kubectl_apply_file_keywords = KubectlFileApplyKeywords(ssh_connection)
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    kubectl_get_pvc_keywords = KubectlGetPvcKeywords(ssh_connection)
    kubectl_exec_keywords = KubectlExecInPodsKeywords(ssh_connection)
    volumesnapshots_keywords = KubectlGetVolumesnapshotsKeywords(ssh_connection)
    snapshot_name = snapshot_workload["snapshot_name"]
    source_pod = source_workload["pod_name"]
    restore_pod = restore_workload["pod_name"]

    get_logger().log_test_case_step("Upload the snapshot workload manifests to the active controller.")
    for workload in (source_workload, snapshot_workload, restore_workload):
        file_keywords.upload_file(get_stx_resource_path(workload["resource"]), workload["yaml_path"], overwrite=True)

    get_logger().log_test_case_step("Create the source PVC and Pod on the lvm-csi thin storage class.")
    kubectl_apply_file_keywords.apply_resource_from_yaml(source_workload["yaml_path"])

    get_logger().log_test_case_step("Verify the source Pod is Running and the source PVC is Bound.")
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[source_workload["pod_name"]], namespace="default", timeout=300)
    kubectl_get_pvc_keywords.wait_for_pvcs_to_reach_status("Bound", pvc_names=[source_workload["pvc_name"]], namespace="default", timeout=300)

    get_logger().log_test_case_step(f"Write '{SNAPSHOT_TEST_FILE}' to the source Pod '{source_pod}' and sync.")
    kubectl_exec_keywords.run_pod_exec_cmd(source_pod, f"sh -c 'echo lvm-csi-snapshot-data > {SNAPSHOT_TEST_FILE}'")
    kubectl_exec_keywords.run_pod_exec_cmd(source_pod, "sh -c 'sync'")

    get_logger().log_test_case_step(f"Verify '{SNAPSHOT_TEST_FILE}' exists on the source Pod '{source_pod}'.")
    kubectl_exec_keywords.run_pod_exec_cmd(source_pod, f"sh -c 'test -f {SNAPSHOT_TEST_FILE}'")
    validate_equals(ssh_connection.get_return_code(), 0, f"'{SNAPSHOT_TEST_FILE}' should exist on the source Pod.")

    get_logger().log_test_case_step(f"Create the VolumeSnapshotClass '{LVM_CSI_SNAPSHOT_CLASS}' and VolumeSnapshot '{snapshot_name}'.")
    kubectl_apply_file_keywords.apply_resource_from_yaml(snapshot_workload["yaml_path"])

    get_logger().log_test_case_step(f"Wait for the VolumeSnapshot '{snapshot_name}' to be ready to use.")
    snapshot_ready = volumesnapshots_keywords.wait_for_volumesnapshot_status(snapshot_name, "true", namespace="default")
    validate_equals(snapshot_ready, True, f"VolumeSnapshot '{snapshot_name}' should be ready to use.")

    get_logger().log_test_case_step("Create the restore PVC (from the snapshot) and Pod.")
    kubectl_apply_file_keywords.apply_resource_from_yaml(restore_workload["yaml_path"])

    get_logger().log_test_case_step("Verify the restore Pod is Running and the restore PVC is Bound.")
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[restore_workload["pod_name"]], namespace="default", timeout=300)
    kubectl_get_pvc_keywords.wait_for_pvcs_to_reach_status("Bound", pvc_names=[restore_workload["pvc_name"]], namespace="default", timeout=300)

    get_logger().log_test_case_step(f"Verify the restored file '{SNAPSHOT_TEST_FILE}' is present in the restore Pod '{restore_pod}'.")
    kubectl_exec_keywords.run_pod_exec_cmd(restore_pod, f"sh -c 'test -f {SNAPSHOT_TEST_FILE}'")
    validate_equals(ssh_connection.get_return_code(), 0, f"'{SNAPSHOT_TEST_FILE}' should be present in the restored Pod (snapshot restored).")


def _setup_lvm_csi_snapshot() -> list:
    """
    Verify the lvm-csi (TopoLVM) thin provisioning is already applied on the lab.

    This scenario does NOT add or apply lvm-csi; it assumes the lab already has it configured. The
    lvm-csi thin volume group (cgts-vg or the dedicated lvm-provisioner) is guaranteed by the test's
    capability mark (lab_has_lvm_thin_cgts_vg / lab_has_lvm_thin_dedicated), so this setup only
    validates the remaining runtime state and fails (via validate_equals) if any check is not met:

    - Validate that all hosts are healthy
    - Validate the 'lvm-csi' application is already 'applied'
    - Validate the 'lvmcsi-pool' thin pool exists on the active controller
    - Capture a snapshot of the active alarms

    Returns:
        list: the snapshot of active alarms captured before the test.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    health_keywords = HealthKeywords(ssh_connection)
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    lvs_keywords = LvsKeywords(ssh_connection)
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Validating that all hosts are healthy")
    health_keywords.validate_hosts_health()

    get_logger().log_setup_step(f"Validate the '{LVM_CSI_APP}' application is already 'applied'")
    app_status = application_show_keywords.get_system_application_show(LVM_CSI_APP).get_system_application_object().get_status()
    validate_equals(app_status, "applied", f"'{LVM_CSI_APP}' application should be 'applied' on the lab.")

    get_logger().log_setup_step(f"Validate the '{LVM_CSI_POOL}' thin pool exists on {active_controller}")
    lvmcsi_pool = lvs_keywords.get_lvs().get_logical_volume(LVM_CSI_POOL)
    validate_equals(lvmcsi_pool.is_thin_pool(), True, f"'{LVM_CSI_POOL}' should be a thin pool.")

    get_logger().log_setup_step("Capture a snapshot of the active alarms")
    alarms_before = alarm_list_keywords.alarm_list()

    return alarms_before


def _teardown_lvm_csi_snapshot_resources(ssh_connection: SSHConnection, alarms_before: list, source_workload: dict, snapshot_workload: dict, restore_workload: dict):
    """
    Delete only the create-and-restore snapshot resources (leave the lvm-csi setup untouched).

    This scenario does not configure lvm-csi, so it must not remove it. It deletes the restore
    Pod/PVC, the VolumeSnapshot/VolumeSnapshotClass and the source Pod/PVC (plus their manifest
    files), confirms the Pods and PVCs are gone, and verifies no new alarms remain.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
        alarms_before (list): the snapshot of active alarms captured during setup.
        source_workload (dict): source PVC/Pod workload used by the test.
        snapshot_workload (dict): VolumeSnapshotClass/VolumeSnapshot manifest used by the test.
        restore_workload (dict): restore PVC/Pod workload used by the test.
    """
    kubectl_file_delete_keywords = KubectlFileDeleteKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    kubectl_get_pvc_keywords = KubectlGetPvcKeywords(ssh_connection)
    alarm_list_keywords = AlarmListKeywords(ssh_connection)

    # Delete in reverse dependency order: restore workload, then snapshot, then source workload.
    # (the snapshot cannot be deleted while the restore PVC still references it, and the source PVC
    # cannot be deleted while the snapshot references it.)
    for workload in (restore_workload, snapshot_workload, source_workload):
        yaml_path = workload["yaml_path"]
        if file_keywords.file_exists(yaml_path):
            get_logger().log_teardown_step(f"Delete the resources defined by '{yaml_path}'.")
            kubectl_file_delete_keywords.delete_resources(yaml_path, ignore_not_found=True)
            file_keywords.delete_file(yaml_path)

    get_logger().log_teardown_step("Confirm the snapshot source and restore Pods and PVCs are deleted.")
    kubectl_get_pods_keywords.wait_for_pods_to_be_deleted(namespace="default", pod_names=[restore_workload["pod_name"], source_workload["pod_name"]])
    kubectl_get_pvc_keywords.wait_for_pvc_to_be_deleted(restore_workload["pvc_name"], namespace="default")
    kubectl_get_pvc_keywords.wait_for_pvc_to_be_deleted(source_workload["pvc_name"], namespace="default")

    get_logger().log_teardown_step("Verify no new alarms remain after the revert.")
    alarm_list_keywords.wait_for_all_alarms_cleared_excluding(excluded_alarms=alarms_before, stable_checks=3, tolerate_query_failure=True)


def _teardown_lvm_csi_resources(ssh_connection: SSHConnection, alarms_before: list):
    """
    Revert the lvm-csi setup and verify no new alarms remain.

    Deletes the test Pod, PVC and manifest files, resets the 'cgts-vg' function to 'none', deletes
    the 'lvm' storage backend, removes the 'lvm-csi' application (back to its initial 'uploaded'
    state) once nothing can trigger an auto-apply, and verifies that no new alarms remain after the
    revert.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
        alarms_before (list): the snapshot of active alarms captured during setup.
    """
    kubectl_file_delete_keywords = KubectlFileDeleteKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    kubectl_get_pvc_keywords = KubectlGetPvcKeywords(ssh_connection)
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
    system_application_apply_keywords = SystemApplicationApplyKeywords(ssh_connection)
    system_application_remove_keywords = SystemApplicationRemoveKeywords(ssh_connection)
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_teardown_step("Delete the test Pod, PVC and manifest files.")
    # Only delete files that were actually uploaded (a missing file path would fail 'kubectl delete -f').
    for yaml_path in (CGTS_VG_WORKLOAD["pod_yaml_path"], CGTS_VG_WORKLOAD["pvc_yaml_path"]):
        if file_keywords.file_exists(yaml_path):
            kubectl_file_delete_keywords.delete_resources(yaml_path, ignore_not_found=True)
            file_keywords.delete_file(yaml_path)

    # Confirm the Pod and PVC are gone before touching the cgts-vg function, so the reset does not race.
    get_logger().log_teardown_step(f"Confirm the '{CGTS_VG_WORKLOAD['pod_name']}' Pod and '{CGTS_VG_WORKLOAD['pvc_name']}' PVC are deleted.")
    kubectl_get_pods_keywords.wait_for_pods_to_be_deleted(namespace="default", pod_names=[CGTS_VG_WORKLOAD["pod_name"]])
    kubectl_get_pvc_keywords.wait_for_pvc_to_be_deleted(CGTS_VG_WORKLOAD["pvc_name"], namespace="default")

    # 'host-lvg-modify -f none' is rejected while sysinv still counts thin LVs, so wait for thin_cur_lv to reach 0.
    get_logger().log_teardown_step(f"Wait for '{LVM_VG}' thin_cur_lv to reach 0 on {active_controller}.")
    system_host_lvg_keywords.wait_for_thin_cur_lv_zero(active_controller, LVM_VG)

    # Only reset the function if it was actually set to 'lvm-csi' during the test.
    current_function = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg().get_lvm_function()
    if current_function == "lvm-csi":
        get_logger().log_teardown_step(f"Reset the '{LVM_VG}' function to 'none' on {active_controller}.")
        system_host_lvg_keywords.system_host_lvg_modify(host_id=active_controller, lvg_name=LVM_VG, lvm_function="none")
    else:
        get_logger().log_info(f"'{LVM_VG}' function is '{current_function}', no reset needed.")

    get_logger().log_teardown_step("Delete the 'lvm' storage backend.")
    if system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"):
        system_storage_backend_keywords.system_storage_backend_delete(backend="lvm")
    else:
        get_logger().log_info("'lvm' backend is not configured, nothing to delete.")

    if system_application_apply_keywords.is_already_applied(LVM_CSI_APP):
        get_logger().log_teardown_step(f"Remove the '{LVM_CSI_APP}' application (back to 'uploaded').")
        remove_input = SystemApplicationRemoveInput()
        remove_input.set_app_name(LVM_CSI_APP)
        remove_input.set_force_removal(True)
        system_application_remove_keywords.system_application_remove(remove_input)
    else:
        get_logger().log_info(f"'{LVM_CSI_APP}' application is not applied, no removal needed.")

    get_logger().log_teardown_step("Verify no new alarms remain after the revert.")
    alarm_list_keywords.wait_for_all_alarms_cleared_excluding(excluded_alarms=alarms_before, stable_checks=3, tolerate_query_failure=True)


def _apply_lvm_csi_dedicated_thin_vg():
    """
    Apply lvm-csi thin provisioning on a NEW dedicated volume group backed by a spare disk.

    - Add the 'lvm' storage backend
    - Create the dedicated local volume group with the lvm-csi thin function
    - Add a free disk as the dedicated volume group's physical volume
    - Wait for the 'lvm-csi' application to be applied
    - Verify the dedicated volume group attributes (name, state, function, type)
    - Verify the dedicated VG available size dropped to ~1% after provisioning the thin pool (~99% reserved)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    system_host_pv_keywords = SystemHostPvKeywords(ssh_connection)
    system_host_disk_keywords = SystemHostDiskKeywords(ssh_connection)
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Add 'lvm' as storage backend")
    system_storage_backend_keywords.system_storage_backend_add(backend="lvm", confirmed=True)
    validate_equals(system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"), True, "'lvm' backend should be configured.")

    get_logger().log_test_case_step(f"Create the '{DEDICATED_VG}' local volume group with the lvm-csi thin function on {active_controller}")
    system_host_lvg_keywords.system_host_lvg_add(active_controller, DEDICATED_VG, lvm_function="lvm-csi", lvm_type="thin")

    get_logger().log_test_case_step(f"Find a free disk and add it as a physical volume to '{DEDICATED_VG}' on {active_controller}")
    disks = system_host_disk_keywords.get_system_host_disk_list(active_controller).system_host_disks
    system_host_pv_keywords.find_and_add_free_pv(active_controller, DEDICATED_VG, disks)

    get_logger().log_test_case_step(f"Wait for the '{LVM_CSI_APP}' application to be applied")
    application_show_keywords.validate_app_progress_contains(LVM_CSI_APP, "completed")
    application_show_keywords.validate_app_status(LVM_CSI_APP, "applied")

    get_logger().log_test_case_step(f"Verify the '{DEDICATED_VG}' local volume group attributes on {active_controller}.")
    lvg = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, DEDICATED_VG).get_system_host_lvg()
    validate_equals(lvg.get_lvg_name(), DEDICATED_VG, f"LVG Name should be '{DEDICATED_VG}'.")
    validate_equals(lvg.get_state(), "provisioned", f"'{DEDICATED_VG}' state should be 'provisioned'.")
    validate_equals(lvg.get_lvm_function(), "lvm-csi", f"'{DEDICATED_VG}' function should be 'lvm-csi'.")
    validate_equals(lvg.get_lvm_type(), "thin", f"'{DEDICATED_VG}' type should be 'thin'.")

    get_logger().log_test_case_step(f"Verify the '{DEDICATED_VG}' available size dropped to ~1% after provisioning the thin pool (~99% reserved).")

    def is_avail_size_reserved() -> bool:
        # The thin pool reserves ~99% of the VG (available drops to ~1%); sysinv updates this async, so re-read each poll.
        current_lvg = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, DEDICATED_VG).get_system_host_lvg()
        raw_total = current_lvg.get_total_size()
        raw_avail = current_lvg.get_avail_size()
        try:
            vg_total_gib = float(raw_total)
            vg_avail_gib = float(raw_avail)
        except (TypeError, ValueError):
            get_logger().log_info(f"'{DEDICATED_VG}' size not reported yet (total={raw_total}, avail={raw_avail}); still waiting.")
            return False
        if vg_total_gib <= 0:
            get_logger().log_info(f"'{DEDICATED_VG}' total size not reported yet ({vg_total_gib}); still waiting.")
            return False
        avail_ratio = vg_avail_gib / vg_total_gib
        get_logger().log_info(f"'{DEDICATED_VG}' total {vg_total_gib} GiB, available {vg_avail_gib} GiB ({avail_ratio:.2%} available, ~{1 - avail_ratio:.2%} reserved).")
        return avail_ratio <= 0.02

    validate_equals_with_retry(is_avail_size_reserved, True, f"'{DEDICATED_VG}' available size to drop to ~1% (thin pool reserves ~99%)", timeout=300, polling_sleep_time=10)


def _apply_lvm_csi_dedicated_thick_vg():
    """
    Apply lvm-csi thick provisioning on a NEW dedicated volume group backed by a spare disk.

    - Add the 'lvm' storage backend
    - Create the dedicated local volume group with the lvm-csi thick function (no '-t' option)
    - Add a free disk as the dedicated volume group's physical volume
    - Wait for the 'lvm-csi' application to be applied
    - Verify the dedicated volume group attributes (name, state, function, type)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    system_host_pv_keywords = SystemHostPvKeywords(ssh_connection)
    system_host_disk_keywords = SystemHostDiskKeywords(ssh_connection)
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Add 'lvm' as storage backend")
    system_storage_backend_keywords.system_storage_backend_add(backend="lvm", confirmed=True)
    validate_equals(system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"), True, "'lvm' backend should be configured.")

    get_logger().log_test_case_step(f"Create the '{DEDICATED_VG}' local volume group with the lvm-csi thick function on {active_controller}")
    system_host_lvg_keywords.system_host_lvg_add(active_controller, DEDICATED_VG, lvm_function="lvm-csi")

    get_logger().log_test_case_step(f"Find a free disk and add it as a physical volume to '{DEDICATED_VG}' on {active_controller}")
    disks = system_host_disk_keywords.get_system_host_disk_list(active_controller).system_host_disks
    system_host_pv_keywords.find_and_add_free_pv(active_controller, DEDICATED_VG, disks)

    get_logger().log_test_case_step(f"Wait for the '{LVM_CSI_APP}' application to be applied")
    application_show_keywords.validate_app_progress_contains(LVM_CSI_APP, "completed")
    application_show_keywords.validate_app_status(LVM_CSI_APP, "applied")

    get_logger().log_test_case_step(f"Verify the '{DEDICATED_VG}' local volume group attributes on {active_controller}.")
    lvg = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, DEDICATED_VG).get_system_host_lvg()
    validate_equals(lvg.get_lvg_name(), DEDICATED_VG, f"LVG Name should be '{DEDICATED_VG}'.")
    validate_equals(lvg.get_state(), "provisioned", f"'{DEDICATED_VG}' state should be 'provisioned'.")
    validate_equals(lvg.get_lvm_function(), "lvm-csi", f"'{DEDICATED_VG}' function should be 'lvm-csi'.")
    validate_equals(lvg.get_lvm_type(), "thick", f"'{DEDICATED_VG}' type should be 'thick'.")


def _verify_dedicated_thick_lv_provisioned(ssh_connection: SSHConnection):
    """
    Verify that a logical volume was provisioned on the dedicated thick VG.

    With thick provisioning there is no thin pool: space is only consumed once a PVC/Pod is created,
    which materializes a logical volume in the 'lvm-provisioner' VG. This polls 'host-lvg-show' until
    the VG reports at least one current logical volume (lvm_cur_lv > 0).

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
    """
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step(f"Verify a logical volume was provisioned on '{DEDICATED_VG}' (current LVs > 0).")

    def has_current_lv_on_dedicated_vg() -> bool:
        # The LV is created asynchronously after the PVC/Pod is bound, so poll until current LVs > 0.
        current_lvs = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, DEDICATED_VG).get_system_host_lvg().get_current_lvs()
        get_logger().log_info(f"'{DEDICATED_VG}' current LVs: {current_lvs}.")
        return int(current_lvs) > 0

    validate_equals_with_retry(has_current_lv_on_dedicated_vg, True, f"a logical volume to be provisioned on '{DEDICATED_VG}'", timeout=300, polling_sleep_time=10)


def _teardown_lvm_csi_dedicated_thin_vg(ssh_connection: SSHConnection, alarms_before: list):
    """
    Revert the dedicated-disk lvm-csi setup and verify no new alarms remain.

    Deletes the test Pod, PVC and manifest files, waits for the VG's thin LV count to reach 0, removes
    the dedicated volume group (which frees the spare disk), deletes the 'lvm' storage backend, removes
    the 'lvm-csi' application (back to its initial 'uploaded' state), and verifies that no new alarms
    remain after the revert.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
        alarms_before (list): the snapshot of active alarms captured during setup.
    """
    kubectl_file_delete_keywords = KubectlFileDeleteKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    kubectl_get_pvc_keywords = KubectlGetPvcKeywords(ssh_connection)
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
    system_application_apply_keywords = SystemApplicationApplyKeywords(ssh_connection)
    system_application_remove_keywords = SystemApplicationRemoveKeywords(ssh_connection)
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_teardown_step("Delete the test Pod, PVC and manifest files.")
    for yaml_path in (DEDICATED_WORKLOAD["pod_yaml_path"], DEDICATED_WORKLOAD["pvc_yaml_path"]):
        if file_keywords.file_exists(yaml_path):
            kubectl_file_delete_keywords.delete_resources(yaml_path, ignore_not_found=True)
            file_keywords.delete_file(yaml_path)

    get_logger().log_teardown_step(f"Confirm the '{DEDICATED_WORKLOAD['pod_name']}' Pod and '{DEDICATED_WORKLOAD['pvc_name']}' PVC are deleted.")
    kubectl_get_pods_keywords.wait_for_pods_to_be_deleted(namespace="default", pod_names=[DEDICATED_WORKLOAD["pod_name"]])
    kubectl_get_pvc_keywords.wait_for_pvc_to_be_deleted(DEDICATED_WORKLOAD["pvc_name"], namespace="default")

    # Remove the dedicated VG entirely (frees the disk), only if it is present (a failure before creation is safe).
    lvg_names = [lvg.get_lvg_name() for lvg in system_host_lvg_keywords.get_system_host_lvg_list(active_controller).get_system_host_lvg()]
    if DEDICATED_VG in lvg_names:
        # 'host-lvg-delete' is rejected while the VG still has a provisioned LV, so wait for Current LVs (lvm_cur_lv) to reach 0.
        get_logger().log_teardown_step(f"Wait for '{DEDICATED_VG}' current LVs to reach 0 on {active_controller}.")

        def is_dedicated_vg_empty() -> bool:
            current_lvs = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, DEDICATED_VG).get_system_host_lvg().get_current_lvs()
            get_logger().log_info(f"'{DEDICATED_VG}' current LVs: {current_lvs}.")
            return int(current_lvs) == 0

        validate_equals_with_retry(is_dedicated_vg_empty, True, f"'{DEDICATED_VG}' current LVs to reach 0", timeout=300, polling_sleep_time=10)

        get_logger().log_teardown_step(f"Delete the '{DEDICATED_VG}' local volume group on {active_controller}.")
        system_host_lvg_keywords.system_host_lvg_delete(active_controller, DEDICATED_VG)
    else:
        get_logger().log_info(f"'{DEDICATED_VG}' local volume group is not present, nothing to delete.")

    get_logger().log_teardown_step("Delete the 'lvm' storage backend.")
    if system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"):
        system_storage_backend_keywords.system_storage_backend_delete(backend="lvm")
    else:
        get_logger().log_info("'lvm' backend is not configured, nothing to delete.")

    if system_application_apply_keywords.is_already_applied(LVM_CSI_APP):
        get_logger().log_teardown_step(f"Remove the '{LVM_CSI_APP}' application (back to 'uploaded').")
        remove_input = SystemApplicationRemoveInput()
        remove_input.set_app_name(LVM_CSI_APP)
        remove_input.set_force_removal(True)
        system_application_remove_keywords.system_application_remove(remove_input)
    else:
        get_logger().log_info(f"'{LVM_CSI_APP}' application is not applied, no removal needed.")

    get_logger().log_teardown_step("Verify no new alarms remain after the revert.")
    alarm_list_keywords.wait_for_all_alarms_cleared_excluding(excluded_alarms=alarms_before, stable_checks=3, tolerate_query_failure=True)


@mark.p2
@mark.lab_is_simplex
def test_lvm_csi_thin_cgts_vg_sx(request):
    """
    Validate lvm-csi thin provisioning on the shared cgts-vg on AIO-SX.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Add the 'lvm-csi' function to the cgts-vg local volume group
        - Wait for the 'lvm-csi' application to be applied
        - Verify the 'lvmcsi-pool' thin pool exists and the cgts-vg attributes (name, state, function, type, pool size)
        - Verify the cgts-vg available size dropped to ~50% after provisioning the thin pool
        - Create an LVM PVC on the cgts-vg (thin) storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify the lvmcsi-pool has been used (Data% > 0)
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Reset the cgts-vg function to 'none'
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_resources(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_cgts_vg()
    _create_and_verify_pvc_and_pod(ssh_connection, CGTS_VG_WORKLOAD)
    _verify_lvmcsi_pool_used(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_is_duplex
def test_lvm_csi_thin_cgts_vg_dx(request):
    """
    Validate lvm-csi thin provisioning on the shared cgts-vg on AIO-DX.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Add the 'lvm-csi' function to the cgts-vg local volume group
        - Wait for the 'lvm-csi' application to be applied
        - Verify the 'lvmcsi-pool' thin pool exists and the cgts-vg attributes (name, state, function, type, pool size)
        - Verify the cgts-vg available size dropped to ~50% after provisioning the thin pool
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create an LVM PVC on the cgts-vg (thin) storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify the lvmcsi-pool has been used (Data% > 0)
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Reset the cgts-vg function to 'none'
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_resources(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_cgts_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection, CGTS_VG_WORKLOAD)
    _verify_lvmcsi_pool_used(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_compute
def test_lvm_csi_thin_cgts_vg_compute(request):
    """
    Validate lvm-csi thin provisioning on the shared cgts-vg on a lab with compute.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Add the 'lvm-csi' function to the cgts-vg local volume group
        - Wait for the 'lvm-csi' application to be applied
        - Verify the 'lvmcsi-pool' thin pool exists and the cgts-vg attributes (name, state, function, type, pool size)
        - Verify the cgts-vg available size dropped to ~50% after provisioning the thin pool
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create an LVM PVC on the cgts-vg (thin) storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify the lvmcsi-pool has been used (Data% > 0)
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Reset the cgts-vg function to 'none'
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_resources(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_cgts_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection, CGTS_VG_WORKLOAD)
    _verify_lvmcsi_pool_used(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_is_simplex
@mark.lab_has_free_disk
def test_lvm_csi_dedicated_thin_vg_sx(request):
    """
    Validate lvm-csi thin provisioning on a dedicated volume group backed by a spare disk on AIO-SX.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Create the 'lvm-provisioner' local volume group with the lvm-csi thin function
        - Find a free disk and add it as the dedicated volume group's physical volume
        - Wait for the 'lvm-csi' application to be applied
        - Verify the dedicated volume group attributes (name, state, function, type)
        - Verify the dedicated VG available size dropped to ~1% after provisioning the thin pool (~99% reserved)
        - Create an LVM PVC on the dedicated (lvm-provisioner) storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify the lvmcsi-pool has been used (Data% > 0)
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Delete the dedicated volume group (frees the disk)
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_dedicated_thin_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thin_vg()
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_lvmcsi_pool_used(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_is_duplex
@mark.lab_has_free_disk
def test_lvm_csi_dedicated_thin_vg_dx(request):
    """
    Validate lvm-csi thin provisioning on a dedicated volume group backed by a spare disk on AIO-DX.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Create the 'lvm-provisioner' local volume group with the lvm-csi thin function
        - Find a free disk and add it as the dedicated volume group's physical volume
        - Wait for the 'lvm-csi' application to be applied
        - Verify the dedicated volume group attributes (name, state, function, type)
        - Verify the dedicated VG available size dropped to ~1% after provisioning the thin pool (~99% reserved)
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create an LVM PVC on the dedicated (lvm-provisioner) storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify the lvmcsi-pool has been used (Data% > 0)
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Delete the dedicated volume group (frees the disk)
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_dedicated_thin_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thin_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_lvmcsi_pool_used(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_compute
@mark.lab_has_free_disk
def test_lvm_csi_dedicated_thin_vg_compute(request):
    """
    Validate lvm-csi thin provisioning on a dedicated volume group backed by a spare disk on a lab with compute.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Create the 'lvm-provisioner' local volume group with the lvm-csi thin function
        - Find a free disk and add it as the dedicated volume group's physical volume
        - Wait for the 'lvm-csi' application to be applied
        - Verify the dedicated volume group attributes (name, state, function, type)
        - Verify the dedicated VG available size dropped to ~1% after provisioning the thin pool (~99% reserved)
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create an LVM PVC on the dedicated (lvm-provisioner) storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify the lvmcsi-pool has been used (Data% > 0)
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Delete the dedicated volume group (frees the disk)
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_dedicated_thin_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thin_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_lvmcsi_pool_used(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_is_simplex
@mark.lab_has_free_disk
def test_lvm_csi_dedicated_thick_vg_sx(request):
    """
    Validate lvm-csi thick provisioning on a dedicated volume group backed by a spare disk on AIO-SX.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Create the 'lvm-provisioner' local volume group with the lvm-csi thick function
        - Find a free disk and add it as the dedicated volume group's physical volume
        - Wait for the 'lvm-csi' application to be applied
        - Verify the dedicated volume group attributes (name, state, function, type)
        - Verify the dedicated VG available size dropped to ~0 (thick reserves the whole VG)
        - Create an LVM PVC on the dedicated (lvm-provisioner) storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Delete the dedicated volume group (frees the disk)
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_dedicated_thin_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thick_vg()
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_dedicated_thick_lv_provisioned(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_is_duplex
@mark.lab_has_free_disk
def test_lvm_csi_dedicated_thick_vg_dx(request):
    """
    Validate lvm-csi thick provisioning on a dedicated volume group backed by a spare disk on AIO-DX.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Create the 'lvm-provisioner' local volume group with the lvm-csi thick function
        - Find a free disk and add it as the dedicated volume group's physical volume
        - Wait for the 'lvm-csi' application to be applied
        - Verify the dedicated volume group attributes (name, state, function, type)
        - Verify the dedicated VG available size dropped to ~0 (thick reserves the whole VG)
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create an LVM PVC on the dedicated (lvm-provisioner) storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Delete the dedicated volume group (frees the disk)
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_dedicated_thin_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thick_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_dedicated_thick_lv_provisioned(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_compute
@mark.lab_has_free_disk
def test_lvm_csi_dedicated_thick_vg_compute(request):
    """
    Validate lvm-csi thick provisioning on a dedicated volume group backed by a spare disk on a lab with compute.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Create the 'lvm-provisioner' local volume group with the lvm-csi thick function
        - Find a free disk and add it as the dedicated volume group's physical volume
        - Wait for the 'lvm-csi' application to be applied
        - Verify the dedicated volume group attributes (name, state, function, type)
        - Verify the dedicated VG available size dropped to ~0 (thick reserves the whole VG)
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create an LVM PVC on the dedicated (lvm-provisioner) storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Delete the dedicated volume group (frees the disk)
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_dedicated_thin_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thick_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_dedicated_thick_lv_provisioned(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_lvm_thin_cgts_vg
@mark.lab_is_simplex
def test_lvm_csi_thin_snapshot_cgts_vg_sx(request):
    """
    Validate lvm-csi thin create-and-restore snapshot on the shared cgts-vg on AIO-SX.

    This scenario assumes lvm-csi thin is ALREADY configured on the lab. It does not add the 'lvm'
    backend or apply the 'lvm-csi' application; it only verifies the required state (and skips if not
    configured).

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm' storage backend is already configured
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the cgts-vg has the lvm-csi thin function and the 'lvmcsi-pool' thin pool exists
        - Capture a snapshot of the active alarms

    Test Steps:
        - Create the source PVC/Pod on the cgts-vg (thin) storage class
        - Write a test file to the source PVC, sync it and verify it exists
        - Create the VolumeSnapshotClass and VolumeSnapshot and wait for the snapshot to be ready
        - Create the restore PVC (from the snapshot) and Pod, verify the Pod is Running and the PVC is Bound
        - Verify the test file is present in the restored Pod
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the restore Pod/PVC, the VolumeSnapshot/VolumeSnapshotClass and the source Pod/PVC (and manifest files)
        - Verify no new alarms remain after the revert
        - The lvm-csi setup (backend, cgts-vg function, application) is left untouched
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm_csi_snapshot()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_snapshot_resources(ssh_connection, alarms_before, CGTS_VG_SNAPSHOT_SOURCE_WORKLOAD, CGTS_VG_SNAPSHOT_WORKLOAD, CGTS_VG_SNAPSHOT_RESTORE_WORKLOAD)

    request.addfinalizer(teardown)

    _create_and_restore_snapshot(ssh_connection, CGTS_VG_SNAPSHOT_SOURCE_WORKLOAD, CGTS_VG_SNAPSHOT_WORKLOAD, CGTS_VG_SNAPSHOT_RESTORE_WORKLOAD)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_lvm_thin_cgts_vg
@mark.lab_is_duplex
def test_lvm_csi_thin_snapshot_cgts_vg_dx(request):
    """
    Validate lvm-csi thin create-and-restore snapshot on the shared cgts-vg on AIO-DX.

    This scenario assumes lvm-csi thin is ALREADY configured on the lab. It does not add the 'lvm'
    backend or apply the 'lvm-csi' application; it only verifies the required state (and skips if not
    configured).

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm' storage backend is already configured
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the cgts-vg has the lvm-csi thin function and the 'lvmcsi-pool' thin pool exists
        - Capture a snapshot of the active alarms

    Test Steps:
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create the source PVC/Pod on the cgts-vg (thin) storage class
        - Write a test file to the source PVC, sync it and verify it exists
        - Create the VolumeSnapshotClass and VolumeSnapshot and wait for the snapshot to be ready
        - Create the restore PVC (from the snapshot) and Pod, verify the Pod is Running and the PVC is Bound
        - Verify the test file is present in the restored Pod
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the restore Pod/PVC, the VolumeSnapshot/VolumeSnapshotClass and the source Pod/PVC (and manifest files)
        - Verify no new alarms remain after the revert
        - The lvm-csi setup (backend, cgts-vg function, application) is left untouched
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm_csi_snapshot()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_snapshot_resources(ssh_connection, alarms_before, CGTS_VG_SNAPSHOT_SOURCE_WORKLOAD, CGTS_VG_SNAPSHOT_WORKLOAD, CGTS_VG_SNAPSHOT_RESTORE_WORKLOAD)

    request.addfinalizer(teardown)

    _verify_topolvm_pods_running(ssh_connection)
    _create_and_restore_snapshot(ssh_connection, CGTS_VG_SNAPSHOT_SOURCE_WORKLOAD, CGTS_VG_SNAPSHOT_WORKLOAD, CGTS_VG_SNAPSHOT_RESTORE_WORKLOAD)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_lvm_thin_cgts_vg
@mark.lab_has_compute
def test_lvm_csi_thin_snapshot_cgts_vg_compute(request):
    """
    Validate lvm-csi thin create-and-restore snapshot on the shared cgts-vg on a lab with compute.

    This scenario assumes lvm-csi thin is ALREADY configured on the lab. It does not add the 'lvm'
    backend or apply the 'lvm-csi' application; it only verifies the required state (and skips if not
    configured).

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm' storage backend is already configured
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the cgts-vg has the lvm-csi thin function and the 'lvmcsi-pool' thin pool exists
        - Capture a snapshot of the active alarms

    Test Steps:
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create the source PVC/Pod on the cgts-vg (thin) storage class
        - Write a test file to the source PVC, sync it and verify it exists
        - Create the VolumeSnapshotClass and VolumeSnapshot and wait for the snapshot to be ready
        - Create the restore PVC (from the snapshot) and Pod, verify the Pod is Running and the PVC is Bound
        - Verify the test file is present in the restored Pod
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the restore Pod/PVC, the VolumeSnapshot/VolumeSnapshotClass and the source Pod/PVC (and manifest files)
        - Verify no new alarms remain after the revert
        - The lvm-csi setup (backend, cgts-vg function, application) is left untouched
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm_csi_snapshot()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_snapshot_resources(ssh_connection, alarms_before, CGTS_VG_SNAPSHOT_SOURCE_WORKLOAD, CGTS_VG_SNAPSHOT_WORKLOAD, CGTS_VG_SNAPSHOT_RESTORE_WORKLOAD)

    request.addfinalizer(teardown)

    _verify_topolvm_pods_running(ssh_connection)
    _create_and_restore_snapshot(ssh_connection, CGTS_VG_SNAPSHOT_SOURCE_WORKLOAD, CGTS_VG_SNAPSHOT_WORKLOAD, CGTS_VG_SNAPSHOT_RESTORE_WORKLOAD)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_lvm_thin_dedicated
@mark.lab_is_simplex
def test_lvm_csi_thin_snapshot_dedicated_vg_sx(request):
    """
    Validate lvm-csi thin create-and-restore snapshot on the dedicated (lvm-provisioner) VG on AIO-SX.

    This scenario assumes lvm-csi thin is ALREADY configured on the lab with a dedicated
    'lvm-provisioner' volume group. It does not add the 'lvm' backend or apply the 'lvm-csi'
    application; it only verifies the required state (and fails if not configured).

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the lvm-provisioner VG has a provisioned lvm-csi thin disk and the 'lvmcsi-pool' thin pool exists
        - Capture a snapshot of the active alarms

    Test Steps:
        - Create the source PVC/Pod on the dedicated (lvm-provisioner, thin) storage class
        - Write a test file to the source PVC, sync it and verify it exists
        - Create the VolumeSnapshotClass and VolumeSnapshot and wait for the snapshot to be ready
        - Create the restore PVC (from the snapshot) and Pod, verify the Pod is Running and the PVC is Bound
        - Verify the test file is present in the restored Pod
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the restore Pod/PVC, the VolumeSnapshot/VolumeSnapshotClass and the source Pod/PVC (and manifest files)
        - Verify no new alarms remain after the revert
        - The lvm-csi setup (backend, lvm-provisioner VG, application) is left untouched
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm_csi_snapshot()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_snapshot_resources(ssh_connection, alarms_before, DEDICATED_SNAPSHOT_SOURCE_WORKLOAD, DEDICATED_SNAPSHOT_WORKLOAD, DEDICATED_SNAPSHOT_RESTORE_WORKLOAD)

    request.addfinalizer(teardown)

    _create_and_restore_snapshot(ssh_connection, DEDICATED_SNAPSHOT_SOURCE_WORKLOAD, DEDICATED_SNAPSHOT_WORKLOAD, DEDICATED_SNAPSHOT_RESTORE_WORKLOAD)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_lvm_thin_dedicated
@mark.lab_is_duplex
def test_lvm_csi_thin_snapshot_dedicated_vg_dx(request):
    """
    Validate lvm-csi thin create-and-restore snapshot on the dedicated (lvm-provisioner) VG on AIO-DX.

    This scenario assumes lvm-csi thin is ALREADY configured on the lab with a dedicated
    'lvm-provisioner' volume group. It does not add the 'lvm' backend or apply the 'lvm-csi'
    application; it only verifies the required state (and fails if not configured).

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the lvm-provisioner VG has a provisioned lvm-csi thin disk and the 'lvmcsi-pool' thin pool exists
        - Capture a snapshot of the active alarms

    Test Steps:
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create the source PVC/Pod on the dedicated (lvm-provisioner, thin) storage class
        - Write a test file to the source PVC, sync it and verify it exists
        - Create the VolumeSnapshotClass and VolumeSnapshot and wait for the snapshot to be ready
        - Create the restore PVC (from the snapshot) and Pod, verify the Pod is Running and the PVC is Bound
        - Verify the test file is present in the restored Pod
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the restore Pod/PVC, the VolumeSnapshot/VolumeSnapshotClass and the source Pod/PVC (and manifest files)
        - Verify no new alarms remain after the revert
        - The lvm-csi setup (backend, lvm-provisioner VG, application) is left untouched
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm_csi_snapshot()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_snapshot_resources(ssh_connection, alarms_before, DEDICATED_SNAPSHOT_SOURCE_WORKLOAD, DEDICATED_SNAPSHOT_WORKLOAD, DEDICATED_SNAPSHOT_RESTORE_WORKLOAD)

    request.addfinalizer(teardown)

    _verify_topolvm_pods_running(ssh_connection)
    _create_and_restore_snapshot(ssh_connection, DEDICATED_SNAPSHOT_SOURCE_WORKLOAD, DEDICATED_SNAPSHOT_WORKLOAD, DEDICATED_SNAPSHOT_RESTORE_WORKLOAD)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_lvm_thin_dedicated
@mark.lab_has_compute
def test_lvm_csi_thin_snapshot_dedicated_vg_compute(request):
    """
    Validate lvm-csi thin create-and-restore snapshot on the dedicated (lvm-provisioner) VG on a lab with compute.

    This scenario assumes lvm-csi thin is ALREADY configured on the lab with a dedicated
    'lvm-provisioner' volume group. It does not add the 'lvm' backend or apply the 'lvm-csi'
    application; it only verifies the required state (and fails if not configured).

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the lvm-provisioner VG has a provisioned lvm-csi thin disk and the 'lvmcsi-pool' thin pool exists
        - Capture a snapshot of the active alarms

    Test Steps:
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create the source PVC/Pod on the dedicated (lvm-provisioner, thin) storage class
        - Write a test file to the source PVC, sync it and verify it exists
        - Create the VolumeSnapshotClass and VolumeSnapshot and wait for the snapshot to be ready
        - Create the restore PVC (from the snapshot) and Pod, verify the Pod is Running and the PVC is Bound
        - Verify the test file is present in the restored Pod
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the restore Pod/PVC, the VolumeSnapshot/VolumeSnapshotClass and the source Pod/PVC (and manifest files)
        - Verify no new alarms remain after the revert
        - The lvm-csi setup (backend, lvm-provisioner VG, application) is left untouched
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm_csi_snapshot()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_snapshot_resources(ssh_connection, alarms_before, DEDICATED_SNAPSHOT_SOURCE_WORKLOAD, DEDICATED_SNAPSHOT_WORKLOAD, DEDICATED_SNAPSHOT_RESTORE_WORKLOAD)

    request.addfinalizer(teardown)

    _verify_topolvm_pods_running(ssh_connection)
    _create_and_restore_snapshot(ssh_connection, DEDICATED_SNAPSHOT_SOURCE_WORKLOAD, DEDICATED_SNAPSHOT_WORKLOAD, DEDICATED_SNAPSHOT_RESTORE_WORKLOAD)
    _verify_no_new_alarms(ssh_connection, alarms_before)
