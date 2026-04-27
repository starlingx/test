from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pod_jsonpath_keywords import KubectlGetPodJsonpathKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.volumesnapshots.kubectl_get_volumesnapshots_keywords import KubectlGetVolumesnapshotsKeywords

# Mapping of k8s version to expected snapshot-controller image tag
VERSION_COMPARISON_LIST = {
    "1.24": "snapshot-controller:v4.0.0",
    "1.25": "snapshot-controller:v4.2.1",
    "1.26": "snapshot-controller:v6.1.0",
    "1.27": "snapshot-controller:v6.1.0",
    "1.28": "snapshot-controller:v6.1.0",
    "1.29": "snapshot-controller:v6.1.0",
    "1.30": "snapshot-controller:v6.3.3",
    "1.31": "snapshot-controller:v8.0.0",
    "1.32": "snapshot-controller:v8.0.0",
    "1.33": "snapshot-controller:v8.1.0",
    "1.34": "snapshot-controller:v8.1.0",
    "1.35": "snapshot-controller:v8.1.0",
}

REMOTE_HOME = "/home/sysadmin"
VOLUME_SNAPSHOT_RESOURCE_TYPE = "volumesnapshots.snapshot.storage.k8s.io"
TEST_FILES_DIR = "resources/cloud_platform/storage/volume_snapshot"


def _upload_yaml_files(ssh_connection: SSHConnection, file_names: list[str]) -> None:
    """Upload test YAML files from local resources to the active controller.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        file_names (list[str]): List of YAML file names to upload.
    """
    file_keywords = FileKeywords(ssh_connection)
    for file_name in file_names:
        local_path = get_stx_resource_path(f"{TEST_FILES_DIR}/{file_name}")
        remote_path = f"{REMOTE_HOME}/{file_name}"
        file_keywords.upload_file(local_path, remote_path, overwrite=True)


def _cleanup_snapshot_test_resources(
    ssh_connection: SSHConnection,
    pod_names: list[str],
    pvc_names: list[str],
    snapshot_names: list[str],
    yaml_file_names: list[str],
) -> None:
    """Clean up all resources created during a volume snapshot test.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pod_names (list[str]): Pod names to delete.
        pvc_names (list[str]): PVC names to delete.
        snapshot_names (list[str]): VolumeSnapshot names to delete.
        yaml_file_names (list[str]): YAML file names to remove from the controller.
    """
    delete_resource_keywords = KubectlDeleteResourceKeywords(ssh_connection)

    for pod_name in pod_names:
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod_name)

    for pvc_name in pvc_names:
        delete_resource_keywords.delete_resource("pvc", pvc_name)

    for snapshot_name in snapshot_names:
        delete_resource_keywords.delete_resource(VOLUME_SNAPSHOT_RESOURCE_TYPE, snapshot_name)

    file_keywords = FileKeywords(ssh_connection)
    for file_name in yaml_file_names:
        file_keywords.delete_file(f"{REMOTE_HOME}/{file_name}")


def _ensure_volumesnapshotclass_exists(ssh_connection: SSHConnection, storage_type: str) -> None:
    """Ensure the volumesnapshotclass for the given storage type exists.

    If it does not exist, enable it via helm override and re-apply platform-integ-apps.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        storage_type (str): Either 'rbd' or 'cephfs'.
    """
    snapshot_class_name = f"{storage_type}-snapshot"
    k8s_config = K8sConfigExporter()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)

    get_logger().log_info(f"Check whether volumesnapshotclass '{snapshot_class_name}' exists")
    ssh_connection.send(k8s_config.export(f"kubectl get volumesnapshotclasses.snapshot.storage.k8s.io " f"{snapshot_class_name} --no-headers 2>/dev/null"))
    rc = ssh_connection.get_return_code()

    if rc == 0:
        get_logger().log_info(f"VolumeSnapshotClass '{snapshot_class_name}' already exists.")
        return
    elif system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("ceph-rook"):
        raise ValueError(f"For rook-ceph, {snapshot_class_name} should be applied by default")

    get_logger().log_test_case_step(f"Create {storage_type} volume snapshot class via helm override")
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override_via_set(
        override_values="snapshotClass.create=True",
        app_name="platform-integ-apps",
        chart_name=f"{storage_type}-provisioner",
        namespace="kube-system",
    )

    get_logger().log_info("Re-apply platform-integ-apps to apply overrides")
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name="platform-integ-apps")

    get_logger().log_info(f"Verify volumesnapshotclass '{snapshot_class_name}' is available")
    ssh_connection.send(k8s_config.export(f"kubectl get volumesnapshotclasses.snapshot.storage.k8s.io " f"{snapshot_class_name} --no-headers"))
    rc = ssh_connection.get_return_code()
    validate_equals(rc, 0, f"{snapshot_class_name} resource isn't available after helm override")


@mark.p1
def test_cephfs_volume_snapshot_create_restore(request):
    """
    CephFS volume snapshot create and restore

    Setup Steps:
        - Delete cephfs test pods if exist
        - Delete cephfs test pvcs if exist
    Test Steps:
        - Upload CephFS test YAML files to active controller
        - Create a PVC
        - Create a pod
        - Write a file on pod
        - Create a volume snapshot class if necessary
        - Create a volume snapshot
        - Create a restored PVC from the VolumeSnapshot created
        - Create a new pod that will use this restored PVC
        - Check if the file created on the original pvc is also present on the restored pvc
    Teardown Steps:
        - Delete cephfs test pods if exist
        - Delete cephfs test pvcs if exist
        - Remove uploaded YAML files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    storage_type = "cephfs"
    pvc_name = f"{storage_type}-pvc"
    pod_name = f"csi-{storage_type}-demo-pod"
    pvc_restore_name = f"restored-pvc-{storage_type}"
    new_pod_name = f"csi-{storage_type}-demo-pod2"
    snapshot_name = f"{storage_type}-pvc-snapshot"

    yaml_files = [
        f"{storage_type}-pvc.yaml",
        f"{storage_type}-pod.yaml",
        f"{storage_type}-snapshot.yaml",
        f"{storage_type}-pvc-restore.yaml",
        f"{storage_type}-new-pod.yaml",
    ]

    # Setup: clean up any leftover resources from previous runs
    get_logger().log_setup_step("Delete test pods, PVCs, and snapshots if they exist before test run")
    _cleanup_snapshot_test_resources(
        ssh_connection,
        pod_names=[pod_name, new_pod_name],
        pvc_names=[pvc_name, pvc_restore_name],
        snapshot_names=[snapshot_name],
        yaml_file_names=[],
    )

    def teardown():
        get_logger().log_teardown_step("Delete test pods, PVCs, snapshots, and YAML files after test run")
        _cleanup_snapshot_test_resources(
            ssh_connection,
            pod_names=[pod_name, new_pod_name],
            pvc_names=[pvc_name, pvc_restore_name],
            snapshot_names=[snapshot_name],
            yaml_file_names=yaml_files,
        )

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Upload CephFS test YAML files to active controller")
    _upload_yaml_files(ssh_connection, yaml_files)

    pvc_yaml = f"{REMOTE_HOME}/{storage_type}-pvc.yaml"
    pod_yaml = f"{REMOTE_HOME}/{storage_type}-pod.yaml"
    snapshot_yaml = f"{REMOTE_HOME}/{storage_type}-snapshot.yaml"
    pvc_restore_yaml = f"{REMOTE_HOME}/{storage_type}-pvc-restore.yaml"
    new_pod_yaml = f"{REMOTE_HOME}/{storage_type}-new-pod.yaml"

    get_logger().log_test_case_step(f"Create a {storage_type} PVC and make sure it is in Bound status")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pvc_yaml)

    get_logger().log_test_case_step(f"Create a {storage_type} pod")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pod_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running")

    get_logger().log_test_case_step("Write a test file on Pod")
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(pod_name, "bash -c 'touch /data/test.txt'", options="-i")

    _ensure_volumesnapshotclass_exists(ssh_connection, storage_type)

    get_logger().log_test_case_step("Create a volume snapshot")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(snapshot_yaml)

    get_logger().log_test_case_step(f"Wait for {snapshot_name} readyToUse is true")
    snapshot_ready = KubectlGetVolumesnapshotsKeywords(ssh_connection).wait_for_volumesnapshot_status(snapshot_name, "true", timeout=120)
    validate_equals(snapshot_ready, True, f"Verify {snapshot_name} is ready to use")

    get_logger().log_test_case_step("Create a restored PVC from the VolumeSnapshot created")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pvc_restore_yaml)

    get_logger().log_test_case_step("Create a new pod that will use this restored PVC")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(new_pod_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(new_pod_name, "Running")

    get_logger().log_test_case_step("Check if the test file present on the restored pod")
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(new_pod_name, "bash -c 'test -f /data/test.txt'", options="-i")


@mark.p1
def test_rbd_volume_snapshot_create_restore(request):
    """
    RBD provisioner volume snapshot create and restore

    Setup Steps:
        - Delete rbd test pods if exist
        - Delete rbd test pvcs if exist
    Test Steps:
        - Upload RBD test YAML files to active controller
        - Create a PVC
        - Create a pod
        - Write a file on pod
        - Create a volume snapshot class if necessary
        - Create a volume snapshot
        - Create a restored PVC from the VolumeSnapshot created
        - Create a new pod that will use this restored PVC
        - Check if the file created on the original pvc is also present on the restored pvc
    Teardown Steps:
        - Delete rbd test pods if exist
        - Delete rbd test pvcs if exist
        - Remove uploaded YAML files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    storage_type = "rbd"
    pvc_name = f"{storage_type}-pvc"
    pod_name = f"csi-{storage_type}-demo-pod"
    pvc_restore_name = f"restored-pvc-{storage_type}2"
    new_pod_name = f"csi-{storage_type}-demo-pod2"
    snapshot_name = f"{storage_type}-pvc-snapshot2"

    yaml_files = [
        f"{storage_type}-pvc.yaml",
        f"{storage_type}-pod.yaml",
        f"{storage_type}-snapshot.yaml",
        f"{storage_type}-pvc-restore.yaml",
        f"{storage_type}-new-pod.yaml",
    ]

    # Setup: clean up any leftover resources from previous runs
    get_logger().log_setup_step("Delete test pods, PVCs, and snapshots if they exist before test run")
    _cleanup_snapshot_test_resources(
        ssh_connection,
        pod_names=[pod_name, new_pod_name],
        pvc_names=[pvc_name, pvc_restore_name],
        snapshot_names=[snapshot_name],
        yaml_file_names=[],
    )

    def teardown():
        get_logger().log_teardown_step("Delete test pods, PVCs, snapshots, and YAML files after test run")
        _cleanup_snapshot_test_resources(
            ssh_connection,
            pod_names=[pod_name, new_pod_name],
            pvc_names=[pvc_name, pvc_restore_name],
            snapshot_names=[snapshot_name],
            yaml_file_names=yaml_files,
        )

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Upload RBD test YAML files to active controller")
    _upload_yaml_files(ssh_connection, yaml_files)

    pvc_yaml = f"{REMOTE_HOME}/{storage_type}-pvc.yaml"
    pod_yaml = f"{REMOTE_HOME}/{storage_type}-pod.yaml"
    snapshot_yaml = f"{REMOTE_HOME}/{storage_type}-snapshot.yaml"
    pvc_restore_yaml = f"{REMOTE_HOME}/{storage_type}-pvc-restore.yaml"
    new_pod_yaml = f"{REMOTE_HOME}/{storage_type}-new-pod.yaml"

    get_logger().log_test_case_step(f"Create a {storage_type} PVC and make sure it is in Bound status")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pvc_yaml)

    get_logger().log_test_case_step(f"Create a {storage_type} pod")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pod_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running")

    get_logger().log_test_case_step("Write a test file on Pod")
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(pod_name, "bash -c 'touch /data/test.txt'", options="-i")

    _ensure_volumesnapshotclass_exists(ssh_connection, storage_type)

    get_logger().log_test_case_step("Create a volume snapshot")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(snapshot_yaml)

    get_logger().log_test_case_step(f"Wait for {snapshot_name} readyToUse is true")
    snapshot_ready = KubectlGetVolumesnapshotsKeywords(ssh_connection).wait_for_volumesnapshot_status(snapshot_name, "true", timeout=120)
    validate_equals(snapshot_ready, True, f"Verify {snapshot_name} is ready to use")

    get_logger().log_test_case_step("Create a restored PVC from the VolumeSnapshot created")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pvc_restore_yaml)

    get_logger().log_test_case_step("Create a new pod that will use this restored PVC")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(new_pod_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(new_pod_name, "Running")

    get_logger().log_test_case_step("Check if the test file present on the restored pod")
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(new_pod_name, "bash -c 'test -f /data/test.txt'", options="-i")


@mark.p3
def test_check_kube_version_comparing_with_snapshot_controller():
    """
    Test to check if the kube version matches the proper volume snapshot controller

    Test Steps:
        - Grab Kube version
        - Grab volume snapshot controller version
        - Compare them and return if they match
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Get kube version")
    kube_version_list = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list()
    k8s_version = kube_version_list.get_active_kubernetes_version()
    get_logger().log_info(f"Active Kubernetes version: {k8s_version}")

    get_logger().log_test_case_step("Get Volume Snapshot controller version")
    pods_output = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace="kube-system", label="app=volume-snapshot-controller")
    volume_snapshot_pod = pods_output.get_pods()[0].get_name()

    # Get the container image using jsonpath
    jsonpath_keywords = KubectlGetPodJsonpathKeywords(ssh_connection)
    image_value = jsonpath_keywords.get_pod_jsonpath_value(
        pod_name=volume_snapshot_pod,
        jsonpath="{.spec.containers[0].image}",
        namespace="kube-system",
    )
    # Extract the image tag after the last '/' (e.g. "snapshot-controller:v8.0.0")
    volume_snapshot_pod_version = image_value[image_value.rindex("/") + 1 :].strip()
    get_logger().log_info(f"Volume snapshot controller version: {volume_snapshot_pod_version}")

    get_logger().log_test_case_step(f"Check whether k8s version:{k8s_version} matching with " f"volume_snapshot version:{volume_snapshot_pod_version}")
    for k8s_ver, expected_snapshot_ver in VERSION_COMPARISON_LIST.items():
        if k8s_ver in k8s_version:
            validate_equals(volume_snapshot_pod_version, expected_snapshot_ver, "Comparing the versions.")
            return

    raise ValueError(f"k8s version:{k8s_version} is not in the list. The TC needs to be updated.")
