from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.system_application_abort_keywords import SystemApplicationAbortKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
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

# lvm-csi helm override coordinates ('system helm-override-show lvm-csi lvm-csi topolvm-system')
# and the expected device-class values rendered per provisioning mode.
LVM_CSI_CHART = "lvm-csi"
LVM_CSI_NAMESPACE = "topolvm-system"
# Thin on the shared cgts-vg: device-class 'cgts-vg-thin' with the 'lvmcsi-pool' thin pool.
CGTS_VG_THIN_DEVICE_CLASS = "cgts-vg-thin"
LVM_CSI_THIN_POOL = "lvmcsi-pool"
# Thick on the dedicated lvm-provisioner VG: device-class 'lvm-provisioner-thick', no thin pool.
DEDICATED_THICK_DEVICE_CLASS = "lvm-provisioner-thick"

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

# Constants for the coexistence scenario (thin cgts-vg + thick dedicated at the same time).
# A single multi-document manifest with two PVCs (one per storage class) and one Pod writing to both.
COEXIST_RESOURCE = "resources/cloud_platform/storage/lvm_csi/lvm-pod-coexistence-cgts-vg-thick.yaml"
COEXIST_YAML_PATH = f"{REMOTE_DIR}/lvm-pod-coexistence-cgts-vg-thick.yaml"
COEXIST_POD = "lvm-pod-coexist"
COEXIST_PVC_CGTS_VG = "lvm-pvc-coexist-cgts-vg"
COEXIST_PVC_DEDICATED = "lvm-pvc-coexist-dedicated"

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
    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"):
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
    validate_equals(pool_size > 0, True, f"'{LVM_VG}' lvm_pool_size should be greater than 0, got '{pool_size}'.")

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


def _verify_lvm_csi_overrides(ssh_connection: SSHConnection, device_class: str, lvm_type: str, volume_group: str):
    """
    Verify the lvm-csi system helm overrides rendered for a given provisioning mode.

    Reads 'system helm-override-show lvm-csi lvm-csi topolvm-system' and validates the device-class
    the app renders: its name, type and backing volume group. For thin, it additionally asserts the
    thin-pool and its over-provisioning ratio are present; for thick, it asserts no thin-pool is
    rendered. This is the "application override validation" check.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
        device_class (str): expected device-class name (e.g. 'cgts-vg-thin', 'lvm-provisioner-thick').
        lvm_type (str): expected provisioning type ('thin' or 'thick').
        volume_group (str): expected backing volume group (e.g. 'cgts-vg', 'lvm-provisioner').
    """
    get_logger().log_test_case_step(f"Read the lvm-csi helm overrides and validate the '{device_class}' device-class.")
    show_object = SystemHelmOverrideKeywords(ssh_connection).get_system_helm_override_show(LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE).get_helm_override_show()
    # 'system helm-override-show' is parsed as a vertical table, so system_overrides is the YAML text
    # of the override block (not a nested dict). Validate the rendered device-class by its key fields
    # appearing in that text.
    system_overrides = str(show_object.get_system_overrides())
    validate_equals(system_overrides.strip() not in ("", "None"), True, "lvm-csi system overrides should not be empty.")

    validate_str_contains(system_overrides, device_class, "lvm-csi device-class name")
    validate_str_contains(system_overrides, f"type: {lvm_type}", "lvm-csi device-class type")
    validate_str_contains(system_overrides, f"volume-group: {volume_group}", "lvm-csi device-class volume-group")

    if lvm_type == "thin":
        get_logger().log_test_case_step("Validate the thin-pool and its over-provisioning ratio are rendered.")
        validate_str_contains(system_overrides, LVM_CSI_THIN_POOL, "lvm-csi thin-pool name")
        validate_str_contains(system_overrides, "overprovision-ratio", "lvm-csi thin-pool over-provisioning ratio")
    else:
        get_logger().log_test_case_step("Validate no thin-pool is rendered for the thick device-class.")
        validate_equals("thin-pool" in system_overrides, False, "thick lvm-csi overrides should not render a thin-pool.")


def _verify_lvm_csi_helm_override_and_chart_attribute(ssh_connection: SSHConnection):
    """
    Validate helm override update/delete and chart-attribute-modify on the lvm-csi chart.

    These operations act on the 'lvm-csi' chart in 'topolvm-system' and are identical regardless of
    the thin/thick provisioning mode (the mode only changes the rendered device-class, not these
    operations). Shared by the thin and thick scenarios.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
    """
    helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
    helm_attribute_keywords = SystemHelmChartAttributeModifyKeywords(ssh_connection)

    get_logger().log_test_case_step("Update a user helm override on the lvm-csi chart and verify it is recorded.")
    helm_override_keywords.update_helm_override_via_set("scheduler.enabled=true", LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE)
    user_overrides = helm_override_keywords.get_system_helm_override_show(LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE).get_helm_override_show().get_user_overrides()
    validate_str_contains(str(user_overrides), "scheduler", "lvm-csi user override should record the scheduler override")

    get_logger().log_test_case_step("Delete the user helm override and verify user_overrides is cleared.")
    helm_override_keywords.delete_system_helm_override(LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE)
    cleared_overrides = helm_override_keywords.get_system_helm_override_show(LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE).get_helm_override_show().get_user_overrides()
    validate_equals(str(cleared_overrides).strip() in ("", "None"), True, "lvm-csi user_overrides should be cleared after delete.")

    get_logger().log_test_case_step("Disable the lvm-csi chart and verify the attributes show 'enabled: false'.")
    helm_attribute_keywords.helm_chart_attribute_modify_enabled("false", LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE)
    disabled_attributes = helm_override_keywords.get_system_helm_override_show(LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE).get_helm_override_show().get_attributes()
    validate_str_contains(str(disabled_attributes), "enabled: false", "lvm-csi chart attributes should contain 'enabled: false'")

    get_logger().log_test_case_step("Re-enable the lvm-csi chart and verify the attributes show 'enabled: true'.")
    helm_attribute_keywords.helm_chart_attribute_modify_enabled("true", LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE)
    enabled_attributes = helm_override_keywords.get_system_helm_override_show(LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE).get_helm_override_show().get_attributes()
    validate_str_contains(str(enabled_attributes), "enabled: true", "lvm-csi chart attributes should contain 'enabled: true'")


def _teardown_lvm_csi_chart_overrides(ssh_connection: SSHConnection):
    """
    Re-enable the lvm-csi chart and clear any leftover user overrides.

    Used by the helm-override/chart-attribute scenarios before the provisioning teardown, so a test
    that fails mid-way does not leave the chart disabled or a user override behind.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
    """
    helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
    helm_attribute_keywords = SystemHelmChartAttributeModifyKeywords(ssh_connection)

    get_logger().log_teardown_step("Re-enable the lvm-csi chart and clear any user overrides.")
    helm_attribute_keywords.helm_chart_attribute_modify_enabled("true", LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE)
    current_user_overrides = helm_override_keywords.get_system_helm_override_show(LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE).get_helm_override_show().get_user_overrides()
    if current_user_overrides is not None and str(current_user_overrides).strip() not in ("", "None"):
        helm_override_keywords.delete_system_helm_override(LVM_CSI_APP, LVM_CSI_CHART, LVM_CSI_NAMESPACE)


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
    system_application_list_keywords = SystemApplicationListKeywords(ssh_connection)
    system_application_abort_keywords = SystemApplicationAbortKeywords(ssh_connection)
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

    # Resetting the cgts-vg function above makes the platform-managed lvm-csi re-apply.
    # 'storage-backend-delete' is rejected while the app is in transition, so if an apply is in
    # progress, abort it and wait for a terminal state before deleting the backend.
    app_status = system_application_list_keywords.get_system_application_list().get_application(LVM_CSI_APP).get_status()
    if app_status == "applying":
        get_logger().log_teardown_step(f"Abort the in-progress '{LVM_CSI_APP}' apply so the backend delete is not rejected.")
        system_application_abort_keywords.system_application_abort(LVM_CSI_APP)
        system_application_list_keywords.validate_app_status_in_list(LVM_CSI_APP, ["applied", "apply-failed"], timeout=600, polling_sleep_time=15)

    # Delete the 'lvm' storage backend FIRST, then VALIDATE it is gone. lvm-csi is platform-managed
    # (desired_state 'applied'); while the backend is configured, sysinv re-applies the app, so
    # removing the app before the backend lets a reapply put it back to 'applied'. Deleting the
    # backend first removes that desired state so the later app-remove sticks.
    get_logger().log_teardown_step("Delete the 'lvm' storage backend.")
    if system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"):
        system_storage_backend_keywords.system_storage_backend_delete(backend="lvm")
    get_logger().log_teardown_step("Validate the 'lvm' storage backend is no longer configured.")
    validate_equals_with_retry(
        lambda: system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"),
        False,
        "'lvm' storage backend should be deleted after teardown",
        timeout=300,
        polling_sleep_time=10,
    )

    # Now remove the app (back to 'uploaded') if not already uploaded, then VALIDATE it reached
    # 'uploaded'. With the backend gone, no reapply is triggered, so the removal is durable.
    app_status = system_application_list_keywords.get_system_application_list().get_application(LVM_CSI_APP).get_status()
    if app_status != "uploaded":
        get_logger().log_teardown_step(f"Remove the '{LVM_CSI_APP}' application (currently '{app_status}') back to 'uploaded'.")
        remove_input = SystemApplicationRemoveInput()
        remove_input.set_app_name(LVM_CSI_APP)
        remove_input.set_force_removal(True)
        system_application_remove_keywords.system_application_remove(remove_input)
    get_logger().log_teardown_step(f"Validate the '{LVM_CSI_APP}' application is back to 'uploaded'.")
    system_application_list_keywords.validate_app_status(LVM_CSI_APP, "uploaded", timeout=600, polling_sleep_time=15)

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
    used_disk_paths = system_host_pv_keywords.get_used_pv_device_paths(active_controller)
    free_disks = system_host_disk_keywords.get_system_host_disk_list(active_controller).get_free_disks(used_disk_paths)
    system_host_pv_keywords.add_free_pv(active_controller, DEDICATED_VG, free_disks)

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
    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"):
        system_storage_backend_keywords.system_storage_backend_add(backend="lvm", confirmed=True)
    validate_equals(system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"), True, "'lvm' backend should be configured.")

    get_logger().log_test_case_step(f"Create the '{DEDICATED_VG}' local volume group with the lvm-csi thick function on {active_controller}")
    system_host_lvg_keywords.system_host_lvg_add(active_controller, DEDICATED_VG, lvm_function="lvm-csi")

    get_logger().log_test_case_step(f"Find a free disk and add it as a physical volume to '{DEDICATED_VG}' on {active_controller}")
    used_disk_paths = system_host_pv_keywords.get_used_pv_device_paths(active_controller)
    free_disks = system_host_disk_keywords.get_system_host_disk_list(active_controller).get_free_disks(used_disk_paths)
    system_host_pv_keywords.add_free_pv(active_controller, DEDICATED_VG, free_disks)

    get_logger().log_test_case_step(f"Wait for the '{LVM_CSI_APP}' application to be applied")
    application_show_keywords.validate_app_progress_contains(LVM_CSI_APP, "completed")
    application_show_keywords.validate_app_status(LVM_CSI_APP, "applied")

    get_logger().log_test_case_step(f"Verify the '{DEDICATED_VG}' local volume group attributes on {active_controller}.")
    lvg = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, DEDICATED_VG).get_system_host_lvg()
    validate_equals(lvg.get_lvg_name(), DEDICATED_VG, f"LVG Name should be '{DEDICATED_VG}'.")
    validate_equals(lvg.get_state(), "provisioned", f"'{DEDICATED_VG}' state should be 'provisioned'.")
    validate_equals(lvg.get_lvm_function(), "lvm-csi", f"'{DEDICATED_VG}' function should be 'lvm-csi'.")
    validate_equals(lvg.get_lvm_type(), "thick", f"'{DEDICATED_VG}' type should be 'thick'.")


def _verify_dedicated_vg_lv_provisioned(ssh_connection: SSHConnection):
    """
    Verify that a logical volume was provisioned on the dedicated VG.

    Once a PVC/Pod is created, a logical volume is materialized in the 'lvm-provisioner' VG. This
    polls 'host-lvg-show' until the VG reports at least one current logical volume (lvm_cur_lv > 0).
    Works for both thin and thick dedicated VGs.

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


def _teardown_lvm_csi_dedicated_vg(ssh_connection: SSHConnection, alarms_before: list):
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
    system_application_list_keywords = SystemApplicationListKeywords(ssh_connection)
    system_application_abort_keywords = SystemApplicationAbortKeywords(ssh_connection)
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

    # Deleting the dedicated VG above makes the platform-managed lvm-csi re-apply.
    # 'storage-backend-delete' is rejected while the app is in transition, so if an apply is in
    # progress, abort it and wait for a terminal state before deleting the backend.
    app_status = system_application_list_keywords.get_system_application_list().get_application(LVM_CSI_APP).get_status()
    if app_status == "applying":
        get_logger().log_teardown_step(f"Abort the in-progress '{LVM_CSI_APP}' apply so the backend delete is not rejected.")
        system_application_abort_keywords.system_application_abort(LVM_CSI_APP)
        system_application_list_keywords.validate_app_status_in_list(LVM_CSI_APP, ["applied", "apply-failed"], timeout=600, polling_sleep_time=15)

    # Delete the 'lvm' storage backend FIRST, then VALIDATE it is gone. lvm-csi is platform-managed
    # (desired_state 'applied'); while the backend is configured, sysinv re-applies the app, so
    # removing the app before the backend lets a reapply put it back to 'applied'. Deleting the
    # backend first removes that desired state so the later app-remove sticks.
    get_logger().log_teardown_step("Delete the 'lvm' storage backend.")
    if system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"):
        system_storage_backend_keywords.system_storage_backend_delete(backend="lvm")
    get_logger().log_teardown_step("Validate the 'lvm' storage backend is no longer configured.")
    validate_equals_with_retry(
        lambda: system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"),
        False,
        "'lvm' storage backend should be deleted after teardown",
        timeout=300,
        polling_sleep_time=10,
    )

    # Now remove the app (back to 'uploaded') if not already uploaded, then VALIDATE it reached
    # 'uploaded'. With the backend gone, no reapply is triggered, so the removal is durable.
    app_status = system_application_list_keywords.get_system_application_list().get_application(LVM_CSI_APP).get_status()
    if app_status != "uploaded":
        get_logger().log_teardown_step(f"Remove the '{LVM_CSI_APP}' application (currently '{app_status}') back to 'uploaded'.")
        remove_input = SystemApplicationRemoveInput()
        remove_input.set_app_name(LVM_CSI_APP)
        remove_input.set_force_removal(True)
        system_application_remove_keywords.system_application_remove(remove_input)
    get_logger().log_teardown_step(f"Validate the '{LVM_CSI_APP}' application is back to 'uploaded'.")
    system_application_list_keywords.validate_app_status(LVM_CSI_APP, "uploaded", timeout=600, polling_sleep_time=15)

    get_logger().log_teardown_step("Verify no new alarms remain after the revert.")
    alarm_list_keywords.wait_for_all_alarms_cleared_excluding(excluded_alarms=alarms_before, stable_checks=3, tolerate_query_failure=True)


def _teardown_lvm_csi_coexistence(ssh_connection: SSHConnection, alarms_before: list):
    """
    Revert the coexistence setup (thin cgts-vg + thick dedicated) and verify no new alarms remain.

    Deletes the coexistence Pod and both PVCs, resets the cgts-vg function to 'none', deletes the
    dedicated 'lvm-provisioner' volume group (frees the disk), deletes the 'lvm' storage backend,
    removes the 'lvm-csi' application (back to 'uploaded'), and verifies no new alarms remain.

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
    system_application_list_keywords = SystemApplicationListKeywords(ssh_connection)
    system_application_abort_keywords = SystemApplicationAbortKeywords(ssh_connection)
    system_application_remove_keywords = SystemApplicationRemoveKeywords(ssh_connection)
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_teardown_step("Delete the coexistence Pod, PVCs and manifest file.")
    if file_keywords.file_exists(COEXIST_YAML_PATH):
        kubectl_file_delete_keywords.delete_resources(COEXIST_YAML_PATH, ignore_not_found=True)
        file_keywords.delete_file(COEXIST_YAML_PATH)

    get_logger().log_teardown_step("Confirm the coexistence Pod and both PVCs are deleted.")
    kubectl_get_pods_keywords.wait_for_pods_to_be_deleted(namespace="default", pod_names=[COEXIST_POD])
    kubectl_get_pvc_keywords.wait_for_pvc_to_be_deleted(COEXIST_PVC_CGTS_VG, namespace="default")
    kubectl_get_pvc_keywords.wait_for_pvc_to_be_deleted(COEXIST_PVC_DEDICATED, namespace="default")

    # 'host-lvg-modify -f none' is rejected while sysinv still counts thin LVs, so wait for thin_cur_lv to reach 0.
    get_logger().log_teardown_step(f"Wait for '{LVM_VG}' thin_cur_lv to reach 0 on {active_controller}.")
    system_host_lvg_keywords.wait_for_thin_cur_lv_zero(active_controller, LVM_VG)

    current_function = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg().get_lvm_function()
    if current_function == "lvm-csi":
        get_logger().log_teardown_step(f"Reset the '{LVM_VG}' function to 'none' on {active_controller}.")
        system_host_lvg_keywords.system_host_lvg_modify(host_id=active_controller, lvg_name=LVM_VG, lvm_function="none")

    # Delete the dedicated VG entirely (frees the disk), only if it is present.
    lvg_names = [lvg.get_lvg_name() for lvg in system_host_lvg_keywords.get_system_host_lvg_list(active_controller).get_system_host_lvg()]
    if DEDICATED_VG in lvg_names:
        # 'host-lvg-delete' is rejected while the VG still has a provisioned LV, so wait for Current LVs to reach 0.
        get_logger().log_teardown_step(f"Wait for '{DEDICATED_VG}' current LVs to reach 0 on {active_controller}.")

        def is_dedicated_vg_empty() -> bool:
            current_lvs = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, DEDICATED_VG).get_system_host_lvg().get_current_lvs()
            get_logger().log_info(f"'{DEDICATED_VG}' current LVs: {current_lvs}.")
            return int(current_lvs) == 0

        validate_equals_with_retry(is_dedicated_vg_empty, True, f"'{DEDICATED_VG}' current LVs to reach 0", timeout=300, polling_sleep_time=10)

        get_logger().log_teardown_step(f"Delete the '{DEDICATED_VG}' local volume group on {active_controller}.")
        system_host_lvg_keywords.system_host_lvg_delete(active_controller, DEDICATED_VG)

    # Resetting the cgts-vg function and deleting the dedicated VG above makes the platform-managed
    # lvm-csi re-apply. 'storage-backend-delete' is rejected while the app is in transition, so if an
    # apply is in progress, abort it and wait for a terminal state before deleting the backend.
    app_status = system_application_list_keywords.get_system_application_list().get_application(LVM_CSI_APP).get_status()
    if app_status == "applying":
        get_logger().log_teardown_step(f"Abort the in-progress '{LVM_CSI_APP}' apply so the backend delete is not rejected.")
        system_application_abort_keywords.system_application_abort(LVM_CSI_APP)
        system_application_list_keywords.validate_app_status_in_list(LVM_CSI_APP, ["applied", "apply-failed"], timeout=600, polling_sleep_time=15)

    # Delete the 'lvm' storage backend FIRST, then VALIDATE it is gone. lvm-csi is platform-managed
    # (desired_state 'applied'); while the backend is configured, sysinv re-applies the app, so
    # removing the app before the backend lets a reapply put it back to 'applied'. Deleting the
    # backend first removes that desired state so the later app-remove sticks.
    get_logger().log_teardown_step("Delete the 'lvm' storage backend.")
    if system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"):
        system_storage_backend_keywords.system_storage_backend_delete(backend="lvm")
    get_logger().log_teardown_step("Validate the 'lvm' storage backend is no longer configured.")
    validate_equals_with_retry(
        lambda: system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"),
        False,
        "'lvm' storage backend should be deleted after teardown",
        timeout=300,
        polling_sleep_time=10,
    )

    # Now remove the app (back to 'uploaded') if not already uploaded, then VALIDATE it reached
    # 'uploaded'. With the backend gone, no reapply is triggered, so the removal is durable.
    app_status = system_application_list_keywords.get_system_application_list().get_application(LVM_CSI_APP).get_status()
    if app_status != "uploaded":
        get_logger().log_teardown_step(f"Remove the '{LVM_CSI_APP}' application (currently '{app_status}') back to 'uploaded'.")
        remove_input = SystemApplicationRemoveInput()
        remove_input.set_app_name(LVM_CSI_APP)
        remove_input.set_force_removal(True)
        system_application_remove_keywords.system_application_remove(remove_input)
    get_logger().log_teardown_step(f"Validate the '{LVM_CSI_APP}' application is back to 'uploaded'.")
    system_application_list_keywords.validate_app_status(LVM_CSI_APP, "uploaded", timeout=600, polling_sleep_time=15)

    get_logger().log_teardown_step("Verify no new alarms remain after the revert.")
    alarm_list_keywords.wait_for_all_alarms_cleared_excluding(excluded_alarms=alarms_before, stable_checks=3, tolerate_query_failure=True)


def _create_and_verify_coexistence_workload(ssh_connection: SSHConnection):
    """
    Create the coexistence Pod with two PVCs (one on cgts-vg thin, one on lvm-provisioner thick).

    Uploads the single multi-document manifest, creates both PVCs and the Pod, and verifies the Pod
    is Running and both PVCs are Bound.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
    """
    file_keywords = FileKeywords(ssh_connection)
    kubectl_apply_file_keywords = KubectlFileApplyKeywords(ssh_connection)
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    kubectl_get_pvc_keywords = KubectlGetPvcKeywords(ssh_connection)

    get_logger().log_test_case_step("Create the two PVCs (thin cgts-vg + thick dedicated) and the Pod that writes to both.")
    file_keywords.upload_file(get_stx_resource_path(COEXIST_RESOURCE), COEXIST_YAML_PATH, overwrite=True)
    kubectl_apply_file_keywords.apply_resource_from_yaml(COEXIST_YAML_PATH)

    get_logger().log_test_case_step("Verify the Pod is Running and both PVCs are Bound.")
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[COEXIST_POD], namespace="default", timeout=300)
    kubectl_get_pvc_keywords.wait_for_pvcs_to_reach_status("Bound", pvc_names=[COEXIST_PVC_CGTS_VG, COEXIST_PVC_DEDICATED], namespace="default", timeout=300)


def _add_two_pvs_to_dedicated_vg(ssh_connection: SSHConnection, lvm_type: str):
    """
    Create an empty dedicated lvm-csi VG and add two spare disks as physical volumes.

    Shared by the thin and thick 'add two dedicated disks' scenarios. Creates the dedicated
    'lvm-provisioner' VG with the given lvm_type, adds a first spare disk (verifying one PV), then a
    second spare disk (verifying two PVs and a larger total size), and waits for lvm-csi to apply.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
        lvm_type (str): the lvm-csi provisioning type for the dedicated VG ('thin' or 'thick').
    """
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    system_host_pv_keywords = SystemHostPvKeywords(ssh_connection)
    system_host_disk_keywords = SystemHostDiskKeywords(ssh_connection)
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Add 'lvm' as storage backend")
    system_storage_backend_keywords.system_storage_backend_add(backend="lvm", confirmed=True)
    validate_equals(system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"), True, "'lvm' backend should be configured.")

    # A thick VG is created without the '-t' option; a thin VG passes '-t thin'.
    lvg_type_option = "thin" if lvm_type == "thin" else None
    get_logger().log_test_case_step(f"Create the empty '{DEDICATED_VG}' dedicated {lvm_type} volume group (no physical volume yet) on {active_controller}.")
    system_host_lvg_keywords.system_host_lvg_add(active_controller, DEDICATED_VG, lvm_function="lvm-csi", lvm_type=lvg_type_option)

    get_logger().log_test_case_step(f"Add a first spare disk as a physical volume to '{DEDICATED_VG}' on {active_controller}.")
    used_disk_paths = system_host_pv_keywords.get_used_pv_device_paths(active_controller)
    free_disks = system_host_disk_keywords.get_system_host_disk_list(active_controller).get_free_disks(used_disk_paths)
    system_host_pv_keywords.add_free_pv(active_controller, DEDICATED_VG, free_disks)

    get_logger().log_test_case_step(f"Verify '{DEDICATED_VG}' reports one physical volume.")
    validate_equals_with_retry(lambda: system_host_pv_keywords.count_pvs_in_lvg(active_controller, DEDICATED_VG), 1, f"'{DEDICATED_VG}' should report one physical volume after the first disk", timeout=300, polling_sleep_time=10)

    get_logger().log_test_case_step(f"Capture the '{DEDICATED_VG}' total size after the first physical volume.")
    total_size_after_first = float(system_host_lvg_keywords.get_system_host_lvg_show(active_controller, DEDICATED_VG).get_system_host_lvg().get_total_size())

    get_logger().log_test_case_step(f"Add a second spare disk as a physical volume to '{DEDICATED_VG}' on {active_controller}.")
    used_disk_paths = system_host_pv_keywords.get_used_pv_device_paths(active_controller)
    free_disks = system_host_disk_keywords.get_system_host_disk_list(active_controller).get_free_disks(used_disk_paths)
    system_host_pv_keywords.add_free_pv(active_controller, DEDICATED_VG, free_disks)

    get_logger().log_test_case_step(f"Verify '{DEDICATED_VG}' now reports two physical volumes.")
    validate_equals_with_retry(lambda: system_host_pv_keywords.count_pvs_in_lvg(active_controller, DEDICATED_VG), 2, f"'{DEDICATED_VG}' should report two physical volumes after the second disk", timeout=300, polling_sleep_time=10)

    get_logger().log_test_case_step(f"Verify the '{DEDICATED_VG}' total size increased after the second physical volume (was {total_size_after_first} GiB).")
    system_host_lvg_keywords.wait_for_total_size_above(active_controller, DEDICATED_VG, total_size_after_first, timeout=300, polling_interval=10)

    get_logger().log_test_case_step(f"Wait for the '{LVM_CSI_APP}' application to be applied.")
    application_show_keywords.validate_app_progress_contains(LVM_CSI_APP, "completed")
    application_show_keywords.validate_app_status(LVM_CSI_APP, "applied")


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
def test_lvm_csi_thin_override_validation(request):
    """
    Validate the lvm-csi application overrides rendered for thin cgts-vg provisioning.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend and assign the lvm-csi function to the cgts-vg
        - Wait for the 'lvm-csi' application to be applied
        - Read the lvm-csi helm overrides and validate the thin device-class (name 'cgts-vg-thin',
          type thin, volume-group cgts-vg, thin-pool name and over-provisioning ratio)
        - Verify no new alarms appeared during the test

    Teardown:
        - Reset the cgts-vg function to 'none', delete the 'lvm' storage backend
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
    _verify_lvm_csi_overrides(ssh_connection, device_class=CGTS_VG_THIN_DEVICE_CLASS, lvm_type="thin", volume_group=LVM_VG)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_free_disk
def test_lvm_csi_thick_override_validation(request):
    """
    Validate the lvm-csi application overrides rendered for thick dedicated-VG provisioning.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend and create the dedicated 'lvm-provisioner' thick VG on a free disk
        - Wait for the 'lvm-csi' application to be applied
        - Read the lvm-csi helm overrides and validate the thick device-class (name
          'lvm-provisioner-thick', type thick, volume-group lvm-provisioner, no thin-pool)
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the dedicated volume group, delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thick_vg()
    _verify_lvm_csi_overrides(ssh_connection, device_class=DEDICATED_THICK_DEVICE_CLASS, lvm_type="thick", volume_group=DEDICATED_VG)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
def test_lvm_csi_thin_helm_override_and_chart_attribute(request):
    """
    Validate helm override update and chart-attribute-modify on lvm-csi (thin cgts-vg).

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend and assign the lvm-csi function to the cgts-vg, apply lvm-csi
        - Update a user helm override ('--set scheduler.enabled=true') and verify it is recorded in
          the chart user_overrides
        - Delete the user helm override and verify user_overrides is cleared
        - Disable the lvm-csi chart ('helm-chart-attribute-modify --enabled false') and verify the
          chart attributes show 'enabled: false'
        - Re-enable the lvm-csi chart and verify the chart attributes show 'enabled: true'
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete any leftover user override and re-enable the chart
        - Reset the cgts-vg function to 'none', delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_chart_overrides(ssh_connection)
        _teardown_lvm_csi_resources(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_cgts_vg()
    _verify_lvm_csi_helm_override_and_chart_attribute(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_free_disk
def test_lvm_csi_thick_helm_override_and_chart_attribute(request):
    """
    Validate helm override update and chart-attribute-modify on lvm-csi (thick dedicated VG).

    The helm override and chart-attribute operations act on the same 'lvm-csi' chart/namespace as
    the thin case and are provisioning-agnostic; this covers them in the thick context for parity.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend and create the dedicated 'lvm-provisioner' thick VG, apply lvm-csi
        - Update a user helm override ('--set scheduler.enabled=true') and verify it is recorded
        - Delete the user helm override and verify user_overrides is cleared
        - Disable the lvm-csi chart and verify the attributes show 'enabled: false'
        - Re-enable the lvm-csi chart and verify the attributes show 'enabled: true'
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete any leftover user override and re-enable the chart
        - Delete the dedicated volume group, delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_chart_overrides(ssh_connection)
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thick_vg()
    _verify_lvm_csi_helm_override_and_chart_attribute(ssh_connection)
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
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

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
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

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
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

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
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thick_vg()
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_dedicated_vg_lv_provisioned(ssh_connection)
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
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thick_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_dedicated_vg_lv_provisioned(ssh_connection)
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
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_dedicated_thick_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_dedicated_vg_lv_provisioned(ssh_connection)
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


@mark.p2
@mark.lab_has_lvm
def test_lvm_csi_force_remove_auto_apply(request):
    """
    Validate that force-removing lvm-csi triggers an automatic re-apply.

    This scenario requires the 'lvm' storage backend to be configured (lab_has_lvm capability) and
    assumes lvm-csi is already applied. It does not add or apply lvm-csi manually. Because the
    lvm-csi function is still assigned to a local volume group, sysinv detects that the application
    should be applied and re-applies it automatically after the forced removal (no manual
    'system application-apply' is issued).

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the 'lvmcsi-pool' thin pool exists on the active controller
        - Capture a snapshot of the active alarms

    Test Steps:
        - Capture the 'lvm-csi' updated_at timestamp
        - Force-remove the 'lvm-csi' application
        - Verify sysinv automatically re-applies it (status 'applied', progress 'completed', updated_at changed)
        - Verify the 'lvmcsi-pool' thin pool exists again after the automatic re-apply
        - Verify no new alarms appeared during the test

    Teardown:
        - Verify no new alarms remain (the lvm-csi setup is left applied, as it was before the test)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    system_application_remove_keywords = SystemApplicationRemoveKeywords(ssh_connection)
    lvs_keywords = LvsKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    alarms_before = _setup_lvm_csi_snapshot()

    def teardown():
        _verify_no_new_alarms(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Capture the '{LVM_CSI_APP}' updated_at timestamp before the removal.")
    updated_at_before = application_show_keywords.get_system_application_show(LVM_CSI_APP).get_system_application_object().get_updated_at()

    get_logger().log_test_case_step(f"Force-remove the '{LVM_CSI_APP}' application.")
    remove_input = SystemApplicationRemoveInput()
    remove_input.set_app_name(LVM_CSI_APP)
    remove_input.set_force_removal(True)
    system_application_remove_keywords.system_application_remove(remove_input)

    get_logger().log_test_case_step(f"Verify sysinv automatically re-applies '{LVM_CSI_APP}' (the lvm-csi function is still assigned to a volume group).")
    application_show_keywords.validate_app_updated_at_changed(LVM_CSI_APP, updated_at_before)
    application_show_keywords.validate_app_progress_contains(LVM_CSI_APP, "completed")
    application_show_keywords.validate_app_status(LVM_CSI_APP, "applied")

    get_logger().log_test_case_step(f"Verify the '{LVM_CSI_POOL}' thin pool exists after the automatic re-apply on {active_controller}.")
    lvmcsi_pool = lvs_keywords.get_lvs().get_logical_volume(LVM_CSI_POOL)
    validate_equals(lvmcsi_pool.is_thin_pool(), True, f"'{LVM_CSI_POOL}' should be a thin pool after the automatic re-apply.")

    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_lvm_thin_cgts_vg
def test_lvm_csi_delete_app(request):
    """
    Validate that deleting the platform-managed lvm-csi application is self-healed by sysinv.

    This scenario requires lvm-csi thin on the shared cgts-vg (lab_has_lvm_thin_cgts_vg capability).
    lvm-csi is a platform-managed application with desired_state 'applied' (its metadata also lists
    'remove' as a forbidden manual operation). Because of that, the periodic sysinv app-operations
    audit re-uploads any missing managed app (auto uploading missing platform managed apps) and then
    re-applies it to reach its desired state - this happens regardless of the cgts-vg lvm-csi
    function assignment. This test force-removes and deletes lvm-csi and then verifies sysinv
    automatically brings it back (re-upload -> re-apply), leaving the lab in its original state.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the 'lvmcsi-pool' thin pool exists on the active controller
        - Capture a snapshot of the active alarms

    Test Steps:
        - Force-remove the 'lvm-csi' application (applied -> uploaded)
        - Delete the 'lvm-csi' application (it briefly leaves the application list)
        - Verify sysinv automatically re-uploads the application (it reappears in the list)
        - Verify sysinv automatically re-applies it (status back to 'applied')
        - Verify the 'lvmcsi-pool' thin pool exists again after the automatic re-apply

    Teardown:
        - Wait for the 'lvm-csi' application to be 'applied' (apply manually as a fallback)
        - Verify no new alarms remain (the lvm-csi setup is left applied, as it was before the test)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    application_list_keywords = SystemApplicationListKeywords(ssh_connection)
    system_application_remove_keywords = SystemApplicationRemoveKeywords(ssh_connection)
    system_application_delete_keywords = SystemApplicationDeleteKeywords(ssh_connection)
    system_application_apply_keywords = SystemApplicationApplyKeywords(ssh_connection)
    lvs_keywords = LvsKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    alarms_before = _setup_lvm_csi_snapshot()

    def teardown():
        # sysinv self-heals the managed app; apply manually only as a fallback if it did not re-apply.
        get_logger().log_teardown_step(f"Wait for '{LVM_CSI_APP}' to be re-applied (auto-apply, with a manual apply fallback).")
        observed_status = application_list_keywords.validate_app_status_in_list(LVM_CSI_APP, ["applied", "uploaded"], timeout=600, polling_sleep_time=20)
        if observed_status == "uploaded":
            get_logger().log_teardown_step(f"'{LVM_CSI_APP}' did not auto-apply; applying it manually.")
            system_application_apply_keywords.system_application_apply(app_name=LVM_CSI_APP)
            application_list_keywords.validate_app_status(LVM_CSI_APP, "applied", timeout=600, polling_sleep_time=20)

        _verify_no_new_alarms(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Force-remove the '{LVM_CSI_APP}' application and wait for it to reach 'uploaded'.")
    remove_input = SystemApplicationRemoveInput()
    remove_input.set_app_name(LVM_CSI_APP)
    remove_input.set_force_removal(True)
    system_application_remove_keywords.system_application_remove(remove_input)
    application_list_keywords.validate_app_status(LVM_CSI_APP, "uploaded", timeout=600, polling_sleep_time=1)

    get_logger().log_test_case_step(f"Delete the '{LVM_CSI_APP}' application.")
    delete_input = SystemApplicationDeleteInput()
    delete_input.set_app_name(LVM_CSI_APP)
    delete_input.set_force_deletion(False)
    delete_msg = system_application_delete_keywords.get_system_application_delete(delete_input)
    validate_equals(delete_msg, f"Application {LVM_CSI_APP} deleted.\n", "Application deletion message validation")

    # lvm-csi is platform-managed with desired_state 'applied', so the sysinv audit re-uploads the
    # missing app (~40s) and re-applies it automatically; no manual upload/apply is issued here.
    get_logger().log_test_case_step(f"Verify sysinv automatically re-uploads the deleted '{LVM_CSI_APP}' application (it reappears in the list).")
    validate_equals_with_retry(lambda: application_list_keywords.is_app_present(LVM_CSI_APP), True, f"'{LVM_CSI_APP}' should be re-uploaded automatically by sysinv", timeout=600, polling_sleep_time=10)

    get_logger().log_test_case_step(f"Verify sysinv automatically re-applies '{LVM_CSI_APP}' (status back to 'applied').")
    application_list_keywords.validate_app_status(LVM_CSI_APP, "applied", timeout=600, polling_sleep_time=20)

    get_logger().log_test_case_step(f"Verify the '{LVM_CSI_POOL}' thin pool exists after the automatic re-apply on {active_controller}.")
    lvmcsi_pool = lvs_keywords.get_lvs().get_logical_volume(LVM_CSI_POOL)
    validate_equals(lvmcsi_pool.is_thin_pool(), True, f"'{LVM_CSI_POOL}' should be a thin pool after the automatic re-apply.")


@mark.p2
@mark.lab_has_lvm_thin_cgts_vg
def test_lvm_csi_abort_apply(request):
    """
    Validate aborting an in-progress lvm-csi apply.

    This scenario requires lvm-csi thin on the shared cgts-vg (lab_has_lvm_thin_cgts_vg capability).
    It re-applies the already-applied lvm-csi application and immediately aborts it while the apply
    is in progress ('applying'), then verifies the abort is honored: the application ends in
    'apply-failed' with progress 'operation aborted by user'. sysinv only auto-recovers after a
    300s interval, so the aborted state is stable long enough to validate. The teardown recovers the
    application (manual apply) so the lab ends in its original 'applied' state.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the 'lvmcsi-pool' thin pool exists on the active controller
        - Capture a snapshot of the active alarms

    Test Steps:
        - Re-apply the 'lvm-csi' application and immediately abort it (apply && abort)
        - Verify the application ends in 'apply-failed' (the apply was aborted)
        - Verify the apply progress reports the operation was aborted by the user

    Teardown:
        - Recover the 'lvm-csi' application (manual apply) back to 'applied'
        - Verify no new alarms remain (the lvm-csi setup is left applied, as it was before the test)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    application_list_keywords = SystemApplicationListKeywords(ssh_connection)
    system_application_abort_keywords = SystemApplicationAbortKeywords(ssh_connection)
    system_application_apply_keywords = SystemApplicationApplyKeywords(ssh_connection)

    alarms_before = _setup_lvm_csi_snapshot()

    def teardown():
        # Recover the aborted app back to its original 'applied' state (sysinv would eventually
        # auto-recover after 300s, but apply it manually so the lab is restored promptly).
        get_logger().log_teardown_step(f"Recover '{LVM_CSI_APP}' back to 'applied' (manual apply).")
        if application_list_keywords.get_system_application_list().get_application(LVM_CSI_APP).get_status() != "applied":
            system_application_apply_keywords.system_application_apply(app_name=LVM_CSI_APP)
        application_list_keywords.validate_app_status(LVM_CSI_APP, "applied", timeout=600, polling_sleep_time=20)

        _verify_no_new_alarms(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    # Run 'application-apply && application-abort' back to back so the abort lands while the apply is
    # in progress ('applying'); the apply can complete quickly, so they must be issued closely.
    get_logger().log_test_case_step(f"Re-apply the '{LVM_CSI_APP}' application and immediately abort it.")
    system_application_abort_keywords.system_application_apply_and_abort(LVM_CSI_APP)

    get_logger().log_test_case_step(f"Verify the '{LVM_CSI_APP}' apply was aborted (status 'apply-failed').")
    application_list_keywords.validate_app_status(LVM_CSI_APP, "apply-failed", timeout=600, polling_sleep_time=5)

    get_logger().log_test_case_step(f"Verify the '{LVM_CSI_APP}' apply progress reports the operation was aborted by the user.")
    apply_progress = application_show_keywords.get_system_application_show(LVM_CSI_APP).get_system_application_object().get_progress()
    validate_equals(apply_progress, "operation aborted by user", f"'{LVM_CSI_APP}' apply should report it was aborted by the user.")


@mark.p2
@mark.lab_has_lvm_thin_cgts_vg
def test_lvm_csi_resize_thin_pool_cgts_vg(request):
    """
    Validate growing the lvm-csi thin pool size on the cgts-vg.

    This scenario requires lvm-csi thin on the shared cgts-vg (lab_has_lvm_thin_cgts_vg capability).
    The thin pool size is set with 'system host-lvg-modify -s <size>'. A thin pool can only be
    grown, never shrunk, so the test increases the pool by a small fixed amount and validates the
    new size. The change is not reversible: the teardown cannot restore the original (smaller) pool
    size, so the lab keeps the grown pool.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the 'lvmcsi-pool' thin pool exists on the active controller
        - Capture a snapshot of the active alarms

    Test Steps:
        - Capture the current cgts-vg lvm_pool_size and the pool's actual size (lvs)
        - Verify the cgts-vg has enough available space to grow the pool
        - Grow the thin pool size by GROW_STEP GiB (system host-lvg-modify -s)
        - Verify the cgts-vg lvm_pool_size reflects the new (larger) value
        - Verify the 'lvmcsi-pool' actual size (lvs) grew accordingly

    Teardown:
        - Verify no new alarms remain (a thin pool cannot be shrunk, so the grown pool is left as is)
    """
    grow_step_gib = 1

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    lvs_keywords = LvsKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    alarms_before = _setup_lvm_csi_snapshot()

    def teardown():
        # A thin pool cannot be shrunk, so there is nothing to restore; just confirm no new alarms.
        _verify_no_new_alarms(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Capture the current '{LVM_VG}' thin pool size on {active_controller}.")
    lvg_before = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg()
    pool_size_before = int(lvg_before.get_lvm_pool_size())
    avail_before = float(lvg_before.get_avail_size())
    pool_lsize_before = lvs_keywords.get_lvs().get_logical_volume(LVM_CSI_POOL).get_lsize_gib()
    new_pool_size = pool_size_before + grow_step_gib

    get_logger().log_test_case_step(f"Verify '{LVM_VG}' has at least {grow_step_gib} GiB available to grow the pool (available {avail_before} GiB).")
    validate_equals(avail_before >= grow_step_gib, True, f"'{LVM_VG}' should have at least {grow_step_gib} GiB available, got {avail_before} GiB.")

    get_logger().log_test_case_step(f"Grow the '{LVM_VG}' thin pool size from {pool_size_before} to {new_pool_size} GiB on {active_controller}.")
    system_host_lvg_keywords.system_host_lvg_modify(host_id=active_controller, lvg_name=LVM_VG, lvm_pool_size=new_pool_size)

    get_logger().log_test_case_step(f"Verify the '{LVM_VG}' lvm_pool_size reflects the new value ({new_pool_size} GiB).")

    def is_pool_size_updated() -> bool:
        # sysinv updates the pool size asynchronously, so poll until it reports the new value.
        current_pool_size = int(system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg().get_lvm_pool_size())
        get_logger().log_info(f"'{LVM_VG}' lvm_pool_size is {current_pool_size} GiB (target {new_pool_size} GiB).")
        return current_pool_size == new_pool_size

    validate_equals_with_retry(is_pool_size_updated, True, f"'{LVM_VG}' lvm_pool_size to reach {new_pool_size} GiB", timeout=300, polling_sleep_time=10)

    get_logger().log_test_case_step(f"Verify the '{LVM_CSI_POOL}' actual size grew by ~{grow_step_gib} GiB (lvs).")

    def is_pool_lsize_grown() -> bool:
        # The physical thin pool is grown asynchronously, so poll until lvs reports the larger size.
        current_lsize = lvs_keywords.get_lvs().get_logical_volume(LVM_CSI_POOL).get_lsize_gib()
        get_logger().log_info(f"'{LVM_CSI_POOL}' actual size is {current_lsize} GiB (was {pool_lsize_before} GiB).")
        return current_lsize > pool_lsize_before

    validate_equals_with_retry(is_pool_lsize_grown, True, f"'{LVM_CSI_POOL}' actual size to grow above {pool_lsize_before} GiB", timeout=300, polling_sleep_time=10)


@mark.p3
@mark.lab_has_lvm_thin_cgts_vg
def test_lvm_csi_shrink_thin_pool_rejected_cgts_vg(request):
    """
    Validate that shrinking the lvm-csi thin pool size on the cgts-vg is rejected.

    This scenario requires lvm-csi thin on the shared cgts-vg (lab_has_lvm_thin_cgts_vg capability).
    A thin pool can only be grown, never shrunk. This negative test attempts to set a smaller pool
    size with 'system host-lvg-modify -s <smaller>' and verifies the command is rejected with the
    'It's not possible to reduce the size of a thin pool' message, and that the pool size is
    unchanged. Nothing is modified, so no teardown restore is needed.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is already 'applied'
        - Validate the 'lvmcsi-pool' thin pool exists on the active controller
        - Capture a snapshot of the active alarms

    Test Steps:
        - Capture the current cgts-vg lvm_pool_size
        - Attempt to shrink the thin pool to a smaller size (system host-lvg-modify -s)
        - Verify the command is rejected with the 'not possible to reduce' message
        - Verify the cgts-vg lvm_pool_size is unchanged

    Teardown:
        - Verify no new alarms remain (nothing was modified)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    alarms_before = _setup_lvm_csi_snapshot()

    def teardown():
        # Nothing was modified (the shrink is rejected), so just confirm no new alarms.
        _verify_no_new_alarms(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Capture the current '{LVM_VG}' thin pool size on {active_controller}.")
    pool_size_before = int(system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg().get_lvm_pool_size())
    smaller_pool_size = pool_size_before - 1

    get_logger().log_test_case_step(f"Attempt to shrink the '{LVM_VG}' thin pool from {pool_size_before} to {smaller_pool_size} GiB on {active_controller}.")
    output = system_host_lvg_keywords.system_host_lvg_modify_with_error(host_id=active_controller, lvg_name=LVM_VG, lvm_pool_size=smaller_pool_size)

    get_logger().log_test_case_step("Verify the shrink attempt was rejected with the expected message.")
    validate_str_contains(output, "not possible to reduce the size of a thin pool", "thin pool shrink should be rejected")

    get_logger().log_test_case_step(f"Verify the '{LVM_VG}' lvm_pool_size is unchanged ({pool_size_before} GiB).")
    pool_size_after = int(system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg().get_lvm_pool_size())
    validate_equals(pool_size_after, pool_size_before, f"'{LVM_VG}' lvm_pool_size should be unchanged after the rejected shrink.")


@mark.p2
@mark.lab_has_min_2_free_disk
def test_lvm_csi_add_two_pvs_dedicated_thin_vg(request):
    """
    Validate adding two physical volumes (two dedicated disks) to a dedicated lvm-csi thin volume group.

    This scenario needs at least two free disks (lab_has_min_2_free_disk). The lab has no dedicated
    disk provisioned, so the test creates an empty dedicated 'lvm-provisioner' thin volume group,
    adds a first spare disk as a physical volume, then adds a second spare disk, and verifies the
    volume group grew: it reports two physical volumes and its total size increased after the second.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Create the empty 'lvm-provisioner' dedicated thin volume group (no physical volume yet)
        - Add a first spare disk as a physical volume and verify the VG reports one physical volume
        - Add a second spare disk as a physical volume
        - Verify the VG now reports two physical volumes
        - Verify the VG total size increased after adding the second physical volume
        - Wait for the 'lvm-csi' application to be applied
        - Create an LVM PVC on the lvm-provisioner storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify a logical volume was provisioned on the dedicated VG (current LVs > 0)

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Delete the dedicated volume group (frees both disks)
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _add_two_pvs_to_dedicated_vg(ssh_connection, lvm_type="thin")
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_dedicated_vg_lv_provisioned(ssh_connection)


@mark.p2
@mark.lab_has_min_2_free_disk
def test_lvm_csi_add_two_pvs_dedicated_thick_vg(request):
    """
    Validate adding two physical volumes (two dedicated disks) to a dedicated lvm-csi thick volume group.

    This scenario needs at least two free disks (lab_has_min_2_free_disk). The lab has no dedicated
    disk provisioned, so the test creates an empty dedicated 'lvm-provisioner' thick volume group,
    adds a first spare disk as a physical volume, then adds a second spare disk, and verifies the
    volume group grew: it reports two physical volumes and its total size increased after the second.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Create the empty 'lvm-provisioner' dedicated thick volume group (no physical volume yet)
        - Add a first spare disk as a physical volume and verify the VG reports one physical volume
        - Add a second spare disk as a physical volume
        - Verify the VG now reports two physical volumes
        - Verify the VG total size increased after adding the second physical volume
        - Wait for the 'lvm-csi' application to be applied
        - Create an LVM PVC on the lvm-provisioner storage class and a Pod that writes to it
        - Verify the Pod is Running and the PVC is Bound
        - Verify a logical volume was provisioned on the dedicated VG (current LVs > 0)

    Teardown:
        - Delete the Pod, PVC and manifest files
        - Delete the dedicated volume group (frees both disks)
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_dedicated_vg(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _add_two_pvs_to_dedicated_vg(ssh_connection, lvm_type="thick")
    _create_and_verify_pvc_and_pod(ssh_connection, DEDICATED_WORKLOAD)
    _verify_dedicated_vg_lv_provisioned(ssh_connection)


@mark.p2
@mark.lab_is_simplex
@mark.lab_has_free_disk
def test_lvm_csi_thin_cgts_vg_and_thick_dedicated_coexistence_sx(request):
    """
    Validate thin cgts-vg and thick dedicated lvm-csi provisioning coexisting on AIO-SX.

    This scenario needs one free disk (lab_has_free_disk) for the dedicated thick volume group. It
    provisions the shared cgts-vg as thin and the dedicated 'lvm-provisioner' VG as thick at the same
    time, then runs a Pod with two PVCs (one per storage class) writing to both concurrently.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Assign the lvm-csi function to the shared cgts-vg (thin) and verify its thin pool
        - Create the dedicated 'lvm-provisioner' thick volume group on a free disk
        - Wait for the 'lvm-csi' application to be applied
        - Verify both the cgts-vg (thin) and the dedicated (thick) volume group attributes
        - Create a Pod with two PVCs (cgts-vg thin + lvm-provisioner thick) and verify both are Bound
        - Verify the cgts-vg thin pool has been used (Data% > 0) and the dedicated VG has a logical volume
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, both PVCs and the manifest file
        - Reset the cgts-vg function to 'none' and delete the dedicated volume group
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_coexistence(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    # Provision the shared cgts-vg (thin) first, then the dedicated lvm-provisioner (thick); the
    # 'lvm' backend-add is idempotent, so running both back to back is safe.
    _apply_lvm_csi_cgts_vg()
    _apply_lvm_csi_dedicated_thick_vg()
    _create_and_verify_coexistence_workload(ssh_connection)
    _verify_lvmcsi_pool_used(ssh_connection)
    _verify_dedicated_vg_lv_provisioned(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_is_duplex
@mark.lab_has_free_disk
def test_lvm_csi_thin_cgts_vg_and_thick_dedicated_coexistence_dx(request):
    """
    Validate thin cgts-vg and thick dedicated lvm-csi provisioning coexisting on AIO-DX.

    This scenario needs one free disk (lab_has_free_disk) for the dedicated thick volume group. It
    provisions the shared cgts-vg as thin and the dedicated 'lvm-provisioner' VG as thick at the same
    time, then runs a Pod with two PVCs (one per storage class) writing to both concurrently.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Assign the lvm-csi function to the shared cgts-vg (thin) and verify its thin pool
        - Create the dedicated 'lvm-provisioner' thick volume group on a free disk
        - Wait for the 'lvm-csi' application to be applied
        - Verify both the cgts-vg (thin) and the dedicated (thick) volume group attributes
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create a Pod with two PVCs (cgts-vg thin + lvm-provisioner thick) and verify both are Bound
        - Verify the cgts-vg thin pool has been used (Data% > 0) and the dedicated VG has a logical volume
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, both PVCs and the manifest file
        - Reset the cgts-vg function to 'none' and delete the dedicated volume group
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_coexistence(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    # Provision the shared cgts-vg (thin) first, then the dedicated lvm-provisioner (thick); the
    # 'lvm' backend-add is idempotent, so running both back to back is safe.
    _apply_lvm_csi_cgts_vg()
    _apply_lvm_csi_dedicated_thick_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_coexistence_workload(ssh_connection)
    _verify_lvmcsi_pool_used(ssh_connection)
    _verify_dedicated_vg_lv_provisioned(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)


@mark.p2
@mark.lab_has_compute
@mark.lab_has_free_disk
def test_lvm_csi_thin_cgts_vg_and_thick_dedicated_coexistence_compute(request):
    """
    Validate thin cgts-vg and thick dedicated lvm-csi provisioning coexisting on a lab with compute.

    This scenario needs one free disk (lab_has_free_disk) for the dedicated thick volume group. It
    provisions the shared cgts-vg as thin and the dedicated 'lvm-provisioner' VG as thick at the same
    time, then runs a Pod with two PVCs (one per storage class) writing to both concurrently.

    Setup:
        - Validate that all hosts are healthy
        - Validate the 'lvm-csi' application is in the initial 'uploaded' state
        - Validate the 'lvm' storage backend is not already configured
        - Capture a snapshot of the active alarms

    Test Steps:
        - Add the 'lvm' storage backend
        - Assign the lvm-csi function to the shared cgts-vg (thin) and verify its thin pool
        - Create the dedicated 'lvm-provisioner' thick volume group on a free disk
        - Wait for the 'lvm-csi' application to be applied
        - Verify both the cgts-vg (thin) and the dedicated (thick) volume group attributes
        - Verify the topolvm-system pods are Running (including topolvm-scheduler)
        - Create a Pod with two PVCs (cgts-vg thin + lvm-provisioner thick) and verify both are Bound
        - Verify the cgts-vg thin pool has been used (Data% > 0) and the dedicated VG has a logical volume
        - Verify no new alarms appeared during the test

    Teardown:
        - Delete the Pod, both PVCs and the manifest file
        - Reset the cgts-vg function to 'none' and delete the dedicated volume group
        - Delete the 'lvm' storage backend
        - Remove the 'lvm-csi' application (back to 'uploaded')
        - Verify no new alarms remain after the revert
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    alarms_before = _setup_lvm()

    # Register the teardown only after setup passed (setup is validation-only, nothing to revert if it fails).
    def teardown():
        _teardown_lvm_csi_coexistence(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    # Provision the shared cgts-vg (thin) first, then the dedicated lvm-provisioner (thick); the
    # 'lvm' backend-add is idempotent, so running both back to back is safe.
    _apply_lvm_csi_cgts_vg()
    _apply_lvm_csi_dedicated_thick_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_coexistence_workload(ssh_connection)
    _verify_lvmcsi_pool_used(ssh_connection)
    _verify_dedicated_vg_lv_provisioned(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)
