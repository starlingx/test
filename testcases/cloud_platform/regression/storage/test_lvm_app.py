from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lvg_keywords import SystemHostLvgKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords
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
PVC_NAME = "lvm-pvc-cgts-vg"
PVC_RESOURCE = "resources/cloud_platform/storage/lvm_csi/lvm-pvc-cgts-vg.yaml"
PVC_YAML_PATH = f"{REMOTE_DIR}/lvm-pvc-cgts-vg.yaml"
POD_NAME = "lvm-pod-cgts-vg"
POD_RESOURCE = "resources/cloud_platform/storage/lvm_csi/lvm-pod-cgts-vg.yaml"
POD_YAML_PATH = f"{REMOTE_DIR}/lvm-pod-cgts-vg.yaml"


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
    - Add the 'lvm-csi' function to the cgts-vg local volume group
    - Wait for the 'lvm-csi' application to be applied
    - Verify the 'lvmcsi-pool' thin pool exists
    - Verify the cgts-vg attributes (name, state, function, type, pool size)
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


def _verify_topolvm_pods_running(ssh_connection: SSHConnection):
    """
    Verify that the topolvm-system pods (including topolvm-scheduler) are Running.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
    """
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Verify the pods in '{TOPOLVM_NAMESPACE}' are Running.")
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=TOPOLVM_POD_PREFIXES, namespace=TOPOLVM_NAMESPACE, timeout=300)


def _create_and_verify_pvc_and_pod(ssh_connection: SSHConnection):
    """
    Create the PVC and Pod, then verify the Pod is Running and the PVC is Bound.

    Args:
        ssh_connection (SSHConnection): the active controller SSH connection.
    """
    file_keywords = FileKeywords(ssh_connection)
    kubectl_apply_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    kubectl_get_pvc_keywords = KubectlGetPvcKeywords(ssh_connection)

    get_logger().log_test_case_step("Create the LVM PVC.")
    file_keywords.upload_file(get_stx_resource_path(PVC_RESOURCE), PVC_YAML_PATH)
    kubectl_apply_keywords.apply_from_yaml(PVC_YAML_PATH)

    get_logger().log_test_case_step("Create the Pod that writes to the PVC.")
    file_keywords.upload_file(get_stx_resource_path(POD_RESOURCE), POD_YAML_PATH)
    kubectl_apply_keywords.apply_from_yaml(POD_YAML_PATH)

    get_logger().log_test_case_step("Verify the Pod is Running and the PVC is Bound.")
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[POD_NAME], namespace="default", timeout=300)
    kubectl_get_pvc_keywords.wait_for_pvcs_to_reach_status("Bound", pvc_names=[PVC_NAME], namespace="default", timeout=300)


def _verify_cgts_vg_pool_used(ssh_connection: SSHConnection):
    """
    Verify that the cgts-vg 'lvmcsi-pool' thin pool has been used (Data% > 0).

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
    # Only delete the resources/files that were actually uploaded. If the test failed before the
    # upload, the manifest is not on the controller and 'kubectl delete -f' would fail on the
    # missing file path (ignore-not-found only covers a missing k8s resource, not a missing file).
    for yaml_path in (POD_YAML_PATH, PVC_YAML_PATH):
        if file_keywords.file_exists(yaml_path):
            kubectl_file_delete_keywords.delete_resources(yaml_path, ignore_not_found=True)
            file_keywords.delete_file(yaml_path)

    # Confirm the Pod and PVC are actually gone before touching the cgts-vg function, so the reset
    # does not race with a volume that is still being released from the thin pool.
    get_logger().log_teardown_step(f"Confirm the '{POD_NAME}' Pod and '{PVC_NAME}' PVC are deleted.")
    kubectl_get_pods_keywords.wait_for_pods_to_be_deleted(namespace="default", pod_names=[POD_NAME])
    kubectl_get_pvc_keywords.wait_for_pvc_to_be_deleted(PVC_NAME, namespace="default")

    # Deleting the PVC only removes the k8s object; sysinv updates the cgts-vg thin LV count
    # asynchronously (and lags behind the LVM state). 'host-lvg-modify -f none' is rejected while
    # sysinv still counts provisioned thin LVs, so wait for thin_cur_lv to reach 0 before the reset.
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

    # Register the teardown only after setup passed: setup is validation-only and changes nothing
    # on the lab, so there is nothing to revert if it fails.
    def teardown():
        _teardown_lvm_csi_resources(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_cgts_vg()
    _create_and_verify_pvc_and_pod(ssh_connection)
    _verify_cgts_vg_pool_used(ssh_connection)
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

    # Register the teardown only after setup passed: setup is validation-only and changes nothing
    # on the lab, so there is nothing to revert if it fails.
    def teardown():
        _teardown_lvm_csi_resources(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_cgts_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection)
    _verify_cgts_vg_pool_used(ssh_connection)
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

    # Register the teardown only after setup passed: setup is validation-only and changes nothing
    # on the lab, so there is nothing to revert if it fails.
    def teardown():
        _teardown_lvm_csi_resources(ssh_connection, alarms_before)

    request.addfinalizer(teardown)

    _apply_lvm_csi_cgts_vg()
    _verify_topolvm_pods_running(ssh_connection)
    _create_and_verify_pvc_and_pod(ssh_connection)
    _verify_cgts_vg_pool_used(ssh_connection)
    _verify_no_new_alarms(ssh_connection, alarms_before)
