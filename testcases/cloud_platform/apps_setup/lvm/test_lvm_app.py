from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lvg_keywords import SystemHostLvgKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords

LVM_CSI_APP = "lvm-csi"
LVM_VG = "cgts-vg"
WRITER_RESOURCE = "resources/cloud_platform/storage/lvm_csi/lvm-writer-cgts-vg.yaml"
WRITER_YAML_PATH = "/home/sysadmin/lvm-writer-cgts-vg.yaml"
WRITER_APP_LABEL = "app=lvm-writer-cgts-vg"
WRITER_POD_PREFIX = "lvm-writer-cgts-vg"
WRITER_PVC = "lvm-writer-pvc-cgts-vg"
ANCHOR_FILE = "/mnt1/anchor"
HEARTBEAT_FILE = "/mnt1/heartbeat"


@mark.p2
def test_pre_upgrade_check_lvm_app():
    """Provision cgts-vg for lvm-csi and start a persistent-writer workload before the upgrade."""
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    kubectl_apply_file_keywords = KubectlFileApplyKeywords(ssh_connection)
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    kubectl_get_pvc_keywords = KubectlGetPvcKeywords(ssh_connection)
    kubectl_exec_keywords = KubectlExecInPodsKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(ssh_connection).wait_for_ceph_health_status(expect_health_status=True)

    get_logger().log_test_case_step("Add 'lvm' as storage backend.")
    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"):
        system_storage_backend_keywords.system_storage_backend_add(backend="lvm", confirmed=True)
    validate_equals(system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("lvm"), True, "'lvm' backend should be configured.")

    get_logger().log_test_case_step(f"Assign the '{LVM_CSI_APP}' function to '{LVM_VG}' on {active_controller}.")
    current_function = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg().get_lvm_function()
    if current_function != "lvm-csi":
        system_host_lvg_keywords.system_host_lvg_modify(host_id=active_controller, lvg_name=LVM_VG, lvm_function="lvm-csi")

    get_logger().log_test_case_step(f"Wait for the '{LVM_CSI_APP}' application to be applied.")
    application_show_keywords.validate_app_progress_contains(LVM_CSI_APP, "completed")
    application_show_keywords.validate_app_status(LVM_CSI_APP, "applied")

    get_logger().log_test_case_step(f"Verify the '{LVM_VG}' local volume group attributes on {active_controller}.")
    lvg = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg()
    validate_equals(lvg.get_state(), "provisioned", f"'{LVM_VG}' state should be 'provisioned'.")
    validate_equals(lvg.get_lvm_function(), "lvm-csi", f"'{LVM_VG}' function should be 'lvm-csi'.")
    validate_equals(lvg.get_lvm_type(), "thin", f"'{LVM_VG}' type should be 'thin'.")

    get_logger().log_test_case_step("Create the writer PVC and Pod on the cgts-vg storage class.")
    file_keywords.upload_file(get_stx_resource_path(WRITER_RESOURCE), WRITER_YAML_PATH, overwrite=True)
    kubectl_apply_file_keywords.apply_resource_from_yaml(WRITER_YAML_PATH)

    get_logger().log_test_case_step("Verify the writer Pod is Running and the writer PVC is Bound.")
    kubectl_get_pvc_keywords.wait_for_pvcs_to_reach_status("Bound", pvc_names=[WRITER_PVC], namespace="default", timeout=300)
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[WRITER_POD_PREFIX], namespace="default", timeout=300)
    writer_pod = kubectl_get_pods_keywords.get_pods("default", label=WRITER_APP_LABEL).get_pods()[0].get_name()

    get_logger().log_test_case_step("Verify the anchor file and its checksum were written to the PVC.")
    validate_equals_with_retry(lambda: "OK" in str(kubectl_exec_keywords.run_pod_exec_cmd(writer_pod, f"sh -c 'md5sum -c {ANCHOR_FILE}.md5 >/dev/null 2>&1 && echo OK'", ignore_error=True)), True, "anchor file to exist and match its stored checksum", timeout=120, polling_sleep_time=5)

    get_logger().log_test_case_step("Verify the writer Pod is actively rewriting the heartbeat file on the PVC.")
    initial_heartbeat = str(kubectl_exec_keywords.run_pod_exec_cmd(writer_pod, f"sh -c 'cat {HEARTBEAT_FILE}'", ignore_error=True))
    validate_equals_with_retry(lambda: str(kubectl_exec_keywords.run_pod_exec_cmd(writer_pod, f"sh -c 'cat {HEARTBEAT_FILE}'", ignore_error=True)) != initial_heartbeat, True, "writer pod to rewrite the heartbeat file", timeout=60, polling_sleep_time=5)


@mark.p2
def test_post_upgrade_check_lvm_app():
    """Verify the cgts-vg provisioning and the persistent-writer workload survived the upgrade."""
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    application_show_keywords = SystemApplicationShowKeywords(ssh_connection)
    system_host_lvg_keywords = SystemHostLvgKeywords(ssh_connection)
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    kubectl_get_pvc_keywords = KubectlGetPvcKeywords(ssh_connection)
    kubectl_exec_keywords = KubectlExecInPodsKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(ssh_connection).wait_for_ceph_health_status(expect_health_status=True)

    get_logger().log_test_case_step(f"Validate the '{LVM_CSI_APP}' application is applied.")
    application_show_keywords.validate_app_status(LVM_CSI_APP, "applied")

    get_logger().log_test_case_step(f"Validate the '{LVM_VG}' is provisioned for lvm-csi thin on {active_controller}.")
    lvg = system_host_lvg_keywords.get_system_host_lvg_show(active_controller, LVM_VG).get_system_host_lvg()
    validate_equals(lvg.get_state(), "provisioned", f"'{LVM_VG}' state should be 'provisioned'.")
    validate_equals(lvg.get_lvm_function(), "lvm-csi", f"'{LVM_VG}' function should be 'lvm-csi'.")
    validate_equals(lvg.get_lvm_type(), "thin", f"'{LVM_VG}' type should be 'thin'.")

    get_logger().log_test_case_step("Validate the writer Pod is Running and the writer PVC is Bound after the upgrade.")
    kubectl_get_pvc_keywords.wait_for_pvcs_to_reach_status("Bound", pvc_names=[WRITER_PVC], namespace="default", timeout=300)
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status("Running", pod_names=[WRITER_POD_PREFIX], namespace="default", timeout=300)
    writer_pod = kubectl_get_pods_keywords.get_pods("default", label=WRITER_APP_LABEL).get_pods()[0].get_name()

    get_logger().log_test_case_step("Validate the anchor file still matches its pre-upgrade checksum (data integrity).")
    checksum_output = str(kubectl_exec_keywords.run_pod_exec_cmd(writer_pod, f"sh -c 'md5sum -c {ANCHOR_FILE}.md5 >/dev/null 2>&1 && echo OK'", ignore_error=True))
    validate_equals("OK" in checksum_output, True, "anchor file should still match its pre-upgrade checksum after the upgrade.")

    get_logger().log_test_case_step("Validate the writer Pod resumed rewriting the heartbeat file after the upgrade.")
    heartbeat_after = str(kubectl_exec_keywords.run_pod_exec_cmd(writer_pod, f"sh -c 'cat {HEARTBEAT_FILE}'", ignore_error=True))
    validate_equals_with_retry(lambda: str(kubectl_exec_keywords.run_pod_exec_cmd(writer_pod, f"sh -c 'cat {HEARTBEAT_FILE}'", ignore_error=True)) != heartbeat_after, True, "writer pod to keep rewriting the heartbeat file after the upgrade", timeout=60, polling_sleep_time=5)
