import re
from time import sleep

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_not_equals
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_update_input import SystemApplicationUpdateInput
from keywords.cloud_platform.system.application.system_application_abort_keywords import SystemApplicationAbortKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.application.system_application_update_keywords import SystemApplicationUpdateKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_stor_keywords import SystemHostStorageKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_create_pods_keywords import KubectlCreatePodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords
from keywords.k8s.volumesnapshots.kubectl_get_volumesnapshots_keywords import KubectlGetVolumesnapshotsKeywords
from keywords.linux.ip.ip_keywords import IPKeywords
from keywords.linux.mount.mount_keywords import MountKeywords
from keywords.ostree.ostree_keywords import OstreeKeywords
from keywords.server.power_keywords import PowerKeywords


def delete_dell_storage_test_pod_resources(ssh_connection: SSHConnection, remote_yaml_path: str) -> None:
    """
    Delete the resources defined by a dell-storage test pod manifest, if the manifest is on the controller.

    'kubectl delete -f' fails when the manifest file itself is missing, and --ignore-not-found only
    suppresses missing Kubernetes resources. The manifest is absent whenever cleanup runs before the
    test has uploaded it, for example on a freshly installed lab.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        remote_yaml_path (str): Path to the manifest on the controller.

    Returns:
        None:
    """
    if not FileKeywords(ssh_connection).file_exists(remote_yaml_path):
        get_logger().log_info(f"{remote_yaml_path} is not on the controller, nothing to delete.")
        return

    KubectlFileDeleteKeywords(ssh_connection).delete_resources(remote_yaml_path, ignore_not_found=True)


def common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name):
    """
    To make sure dell-storage application is uploaded before starting the tests. Function for NFS protocol

    Test Steps:
        - Verify status of dell-storage application
        - If it's not uploaded, Remove dell-storage application.
        - When it gets Uploaded, Set dell-storage app helm override attributes is true
        - Set up the storage network from DM
        - Update user-overrides for CSI-Powerstore chart
        - Create powerstoreOverrides.yaml file to use as user-overrides (NFS)
        - Apply dell-storage.

    """
    get_logger().log_test_case_step(f"Verify the status of {dell_storage_app_name} application.")

    if dell_storage_app_status != SystemApplicationStatusEnum.UPLOADED.value:
        delete_dell_storage_test_pod_resources(ssh_connection, "/home/sysadmin/dell-storage-test-nfs-pod.yaml")

        get_logger().log_test_case_step(f"Remove {dell_storage_app_name} application.")
        dell_storage_remove_input = SystemApplicationRemoveInput()
        dell_storage_remove_input.set_app_name(dell_storage_app_name)
        dell_storage_remove_input.set_force_removal(False)
        dell_app_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(dell_storage_remove_input)
        dell_storage_app_status = dell_app_output.get_system_application_object().get_status()
        validate_equals(dell_storage_app_status, SystemApplicationStatusEnum.UPLOADED.value, "dell-storage removal status validation")
        get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    if dell_storage_app_status == SystemApplicationStatusEnum.UPLOADED.value:
        helm_chart_attribute_modify_keywords = SystemHelmChartAttributeModifyKeywords(ssh_connection)
        get_logger().log_test_case_step(f"Set {dell_storage_app_name} helm override attributes is true")
        helm_chart_attribute_modify_keywords.helm_chart_attribute_modify_enabled("true", dell_storage_app_name, chart_name, namespace)

        get_logger().log_test_case_step("Set up the storage network from DM")
        storage_config = ConfigurationManager.get_storage_config()
        storage_ip = storage_config.get_storage_network_ip_address()
        storage_interface = storage_config.get_storage_network_interface_name()

        ipkeyword = IPKeywords(ssh_connection)
        ipkeyword.set_ip_addr(storage_ip, storage_interface)
        ipkeyword.set_ip_port_state(storage_interface, "up")

        get_logger().log_test_case_step("Update user-overrides for CSI-Powerstore chart")
        yaml_file = "dell-storage-powerstoreNfsOverrides.yaml"
        username = storage_config.get_credentials().get_user_name()
        password = storage_config.get_credentials().get_password()
        array_id = storage_config.get_storage_array_id()
        endpoint = storage_config.get_storage_array_endpoint()
        nas_name = storage_config.get_storage_array_nas_name()
        template_file = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{yaml_file}")
        replacement_dictionary = {"username": username, "password": password, "array_id": array_id, "endpoint": endpoint, "nas_name": nas_name}
        remote_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, yaml_file, "/home/sysadmin")
        get_logger().log_test_case_step("Create powerstoreOverrides.yaml file to use as user-overrides (NFS)")
        SystemHelmOverrideKeywords(ssh_connection).update_helm_override(remote_yaml, dell_storage_app_name, chart_name, namespace)

        get_logger().log_test_case_step(f"Apply {dell_storage_app_name}.")
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply(dell_storage_app_name)


def ensure_ceph_storage_backend_configured(ssh_connection: SSHConnection, timeout: int = 1800) -> None:
    """Ensure the ceph storage backend is configured; add it and wait if it isn't.

    Test Steps:
        - Check whether the ceph storage backend is already present.
        - If not, add it with 'system storage-backend-add ceph'.
        - Wait for the backend to reach the 'configured' state.
        - Wait for ceph to report healthy.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        timeout (int): Max seconds to wait for the backend to configure. Defaults to 1800.
    """
    backend = "ceph"
    storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)

    backends = storage_backend_keywords.get_system_storage_backend_list()

    if backends.is_backend_configured(backend):
        get_logger().log_info("ceph storage backend is already present.")
    else:
        get_logger().log_test_case_step("Add ceph storage backend")
        storage_backend_keywords.system_storage_backend_add(backend, confirmed=True)

        get_logger().log_test_case_step("Wait for ceph storage backend to reach configured state")
        is_configured = storage_backend_keywords.wait_for_backend_configured(backend, timeout=timeout)
        validate_equals(is_configured, True, "ceph storage backend reached configured state")

        host_stor = SystemHostStorageKeywords(ssh_connection)
        hostname, osd_uuid = host_stor.find_and_add_osd(["controller-0"])

    get_logger().log_test_case_step("Wait for ceph storage backend to reach configured state")
    is_configured = storage_backend_keywords.wait_for_backend_configured(backend, timeout=timeout)
    validate_equals(is_configured, True, "ceph storage backend reached configured state")

    get_logger().log_test_case_step("Wait for ceph to be healthy")
    CephStatusKeywords(ssh_connection).wait_for_ceph_health_status(expect_health_status=True, timeout=timeout)

    app_config = ConfigurationManager.get_app_config()
    platform_integ_apps_name = app_config.get_platform_integ_apps_app_name()
    get_logger().log_test_case_step("Validate platform-integ-apps app is present and applied, and the version matches.")
    SystemApplicationListKeywords(ssh_connection).validate_app_status(platform_integ_apps_name, "applied")

def common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name):
    """
    To make sure dell-storage application is uploaded before starting the tests. Function for ISCSI protocol

    Test Steps:
        - Verify status of dell-storage application
        - If it's not uploaded, Remove dell-storage application.
        - When it gets Uploaded, Set dell-storage app helm override attributes is true
        - Set up the storage network from DM
        - Update user-overrides for CSI-Powerstore chart
        - Create powerstoreOverrides.yaml file to use as user-overrides (ISCSI)
        - Apply dell-storage.

    """
    get_logger().log_test_case_step(f"Verify the status of {dell_storage_app_name} application.")

    if dell_storage_app_status != SystemApplicationStatusEnum.UPLOADED.value:

        delete_dell_storage_test_pod_resources(ssh_connection, "/home/sysadmin/dell-storage-test-pod.yaml")
        get_logger().log_test_case_step(f"Remove {dell_storage_app_name} application.")
        dell_storage_remove_input = SystemApplicationRemoveInput()
        dell_storage_remove_input.set_app_name(dell_storage_app_name)
        dell_storage_remove_input.set_force_removal(False)
        dell_app_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(dell_storage_remove_input)
        dell_storage_app_status = dell_app_output.get_system_application_object().get_status()
        validate_equals(dell_storage_app_status, SystemApplicationStatusEnum.UPLOADED.value, "dell-storage removal status validation")
        get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    if dell_storage_app_status == SystemApplicationStatusEnum.UPLOADED.value:
        helm_chart_attribute_modify_keywords = SystemHelmChartAttributeModifyKeywords(ssh_connection)
        get_logger().log_test_case_step(f"Set {dell_storage_app_name} helm override attributes is true")
        helm_chart_attribute_modify_keywords.helm_chart_attribute_modify_enabled("true", dell_storage_app_name, chart_name, namespace)

        get_logger().log_test_case_step("Set up the storage network from DM")
        storage_config = ConfigurationManager.get_storage_config()
        storage_ip = storage_config.get_storage_network_ip_address()
        storage_interface = storage_config.get_storage_network_interface_name()

        ipkeyword = IPKeywords(ssh_connection)
        ipkeyword.set_ip_addr(storage_ip, storage_interface)
        ipkeyword.set_ip_port_state(storage_interface, "up")

        get_logger().log_test_case_step("Update user-overrides for CSI-Powerstore chart")
        yaml_file = "dell-storage-powerstoreOverrides.yaml"
        username = storage_config.get_credentials().get_user_name()
        password = storage_config.get_credentials().get_password()
        array_id = storage_config.get_storage_array_id()
        endpoint = storage_config.get_storage_array_endpoint()
        template_file = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{yaml_file}")
        replacement_dictionary = {"username": username, "password": password, "array_id": array_id, "endpoint": endpoint}
        remote_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, yaml_file, "/home/sysadmin")
        get_logger().log_test_case_step("Create powerstoreOverrides.yaml file to use as user-overrides (ISCSI)")
        SystemHelmOverrideKeywords(ssh_connection).update_helm_override(remote_yaml, dell_storage_app_name, chart_name, namespace)

        get_logger().log_test_case_step(f"Apply {dell_storage_app_name}.")
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply(dell_storage_app_name)


def refresh_os_tree_keywords(ssh_connection: SSHConnection):
    """Toggle the ostree lock so the new tarball version is picked up in the database.

    Runs 'sudo touch /ostree/lock' followed by 'sudo rm -f /ostree/lock'.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    ostree_keywords = OstreeKeywords(ssh_connection)
    ostree_keywords.ostree_update()


def verify_file_created_on_pod_exists(ssh_connection: SSHConnection, namespace: str, pod_name: str, timeout: int = 600, poll_interval: int = 15):
    """
    Verify that the test.txt file previously created still exists inside the pod.

    After a power-off/on cycle the StatefulSet pod is torn down and recreated. There is a
    window where the pod name is reported Running but 'kubectl exec' still fails transiently
    with "pod does not exist" (the sandbox is not ready to be exec'd into yet). A single exec
    races against that window, so the exec is polled: any transient exec failure is retried,
    and the file is considered present only once the exec succeeds with return code 0.

    Test Steps:
        - Wait for the pod to be Running so it can be exec'd into.
        - Poll 'test -f /data0/test.txt' inside the pod until it succeeds or the timeout elapses.

    Args:
        ssh_connection (SSHConnection): the ssh connection to the active controller.
        namespace (str): the namespace the pod runs in.
        pod_name (str): the name of the pod to check.
        timeout (int): maximum time in seconds to wait for the file check to succeed.
        poll_interval (int): time in seconds between exec attempts.
    """
    get_logger().log_test_case_step(f"Wait for pod {pod_name} to be Running before exec")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running", namespace, timeout=timeout)

    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'test -f /data0/test.txt'"

    get_logger().log_test_case_step(f"Verify if the test.txt file created on the dell-storage test pod is present on the pvc. {pod_name}")
    validate_equals_with_retry(
        function_to_execute=lambda: (kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options, ignore_error=True), ssh_connection.get_return_code())[1],
        expected_value=0,
        validation_description=f"test.txt is on {pod_name} pod.",
        timeout=timeout,
        polling_sleep_time=poll_interval,
    )


def verify_file_created_on_ceph_rbd_pod_exists(ssh_connection: SSHConnection, namespace: str, pod_name: str, timeout: int = 600, poll_interval: int = 15):
    """
    Verify that the test.txt file previously created still exists inside the pod.

    After a power-off/on cycle the StatefulSet pod is torn down and recreated. There is a
    window where the pod name is reported Running but 'kubectl exec' still fails transiently
    with "pod does not exist" (the sandbox is not ready to be exec'd into yet). A single exec
    races against that window, so the exec is polled: any transient exec failure is retried,
    and the file is considered present only once the exec succeeds with return code 0.

    Test Steps:
        - Wait for the pod to be Running so it can be exec'd into.
        - Poll 'test -f /data0/test.txt' inside the pod until it succeeds or the timeout elapses.

    Args:
        ssh_connection (SSHConnection): the ssh connection to the active controller.
        namespace (str): the namespace the pod runs in.
        pod_name (str): the name of the pod to check.
        timeout (int): maximum time in seconds to wait for the file check to succeed.
        poll_interval (int): time in seconds between exec attempts.
    """
    get_logger().log_test_case_step(f"Wait for pod {pod_name} to be Running before exec")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running", namespace, timeout=timeout)

    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'test -f /data/test.txt'"

    get_logger().log_test_case_step(f"Verify if the test.txt file created on the dell-storage test pod is present on the pvc. {pod_name}")
    validate_equals_with_retry(
        function_to_execute=lambda: (kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options, ignore_error=True), ssh_connection.get_return_code())[1],
        expected_value=0,
        validation_description=f"test.txt is on {pod_name} pod.",
        timeout=timeout,
        polling_sleep_time=poll_interval,
    )


def make_sure_dell_storage_application_applied():
    """
    To make sure dell-storage application is applied before testing start

    Test Steps:
        - Check if dell-storage was upload. Uploading dell-storage app.
        - Check if only CSI-Powerstore is activated.
        - Create powerstoreOverrides.yaml file to use as user-overrides (ISCSI)
        - Update user-overrides for CSI-Powerstore chart.
        - Apply dell-storage.

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dell_storage_app_name = "dell-storage"
    namespace = "dell-storage"

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    if dell_storage_app_status == SystemApplicationStatusEnum.APPLY_FAILED:
        get_logger().log_test_case_step(f"Remove {dell_storage_app_name} application.")
        dell_storage_remove_input = SystemApplicationRemoveInput()
        dell_storage_remove_input.set_app_name(dell_storage_app_name)
        dell_storage_remove_input.set_force_removal(False)
        dell_app_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(dell_storage_remove_input)
        dell_storage_app_status = dell_app_output.get_system_application_object().get_status()
        validate_equals(dell_storage_app_status, SystemApplicationStatusEnum.UPLOADED.value, "dell-storage removal status validation")
        get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    if dell_storage_app_status == SystemApplicationStatusEnum.UPLOADED.value:
        chart_name = "csi-powerstore"
        helm_chart_attribute_modify_keywords = SystemHelmChartAttributeModifyKeywords(ssh_connection)
        get_logger().log_test_case_step(f"Set {dell_storage_app_name} helm override attributes is true")
        helm_chart_attribute_modify_keywords.helm_chart_attribute_modify_enabled("true", dell_storage_app_name, chart_name, namespace)

        get_logger().log_test_case_step("Update user-overrides for CSI-Powerstore chart")
        yaml_file = "dell-storage-powerstoreOverrides.yaml"
        storage_config = ConfigurationManager.get_storage_config()
        username = storage_config.get_credentials().get_user_name()
        password = storage_config.get_credentials().get_password()
        array_id = storage_config.get_storage_array_id()
        endpoint = storage_config.get_storage_array_endpoint()
        template_file = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{yaml_file}")
        replacement_dictionary = {"username": username, "password": password, "array_id": array_id, "endpoint": endpoint}
        remote_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, yaml_file, "/home/sysadmin")
        SystemHelmOverrideKeywords(ssh_connection).update_helm_override(remote_yaml, dell_storage_app_name, chart_name, namespace)

        get_logger().log_test_case_step(f"Apply {dell_storage_app_name}.")
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply(dell_storage_app_name)

    app_status_list = ["applied"]
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, app_status_list, timeout=600, polling_sleep_time=20)
    get_logger().log_info(f"{dell_storage_app_name} application is: applied")


def common_dell_storage_teardown():
    """
    Common teardown function for dell-storage tests.

    Teardown Steps:
        - Remove dell-storage application if not in uploaded state
        - Delete helm overrides for csi-powerstore chart

    """
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"
    namespace = "dell-storage"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_application_remove_input = SystemApplicationRemoveInput()

    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()

    if dell_storage_app_status != SystemApplicationStatusEnum.UPLOADED.value:
        get_logger().log_teardown_step("Remove dell-storage application")
        system_application_remove_input.set_app_name(dell_storage_app_name)
        # Removing dell-storage (unmounting PVCs and terminating csi-powerstore pods)
        # takes well over the 60s default, so use a generous timeout to avoid a
        # spurious teardown TimeoutError while the removal is still in progress.
        system_application_remove_input.set_timeout_in_seconds(1800)
        SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)
    else:
        get_logger().log_info(f"Dell-storage already in uploaded state: {dell_storage_app_status}")

    get_logger().log_teardown_step("Remove helm-override")
    SystemHelmOverrideKeywords(ssh_connection).delete_system_helm_override(dell_storage_app_name, chart_name, namespace)


@mark.p2
@mark.lab_dell_storage
def test_dell_storage_powerstore_procedure(request):
    """
    Test case: This Test case is to test dell storage PowerStore procedure

    Test Steps:
        - Check if dell-storage was upload. Uploading dell-storage app.
        - Check if only CSI-Powerstore is activated.
        - Create powerstoreOverrides.yaml file to use as user-overrides (ISCSI)
        - Set up the storage network from DM
        - Update user-overrides for CSI-Powerstore chart.
        - Apply dell-storage.
        - Check if all pods are running.
        - Create dell storage PVC and pod
        - Write a test.txt file on test pod
        - pod sync
        - Create volumesnapshot
        - Create snapshot pod
        - Check whether test.txt is in snapshot pod

    Teardown:
        - Remove test stuff.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"

    get_logger().log_test_case_step("Copy dell-storage test files to target.")
    snapshot_pod_yaml = "dell-storage-powerstoretest-snapshot.yaml"
    snapshot_yaml = "dell-storage-csi-powerstore-snapshot.yaml"
    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [snapshot_pod_yaml, snapshot_yaml, test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    def teardown():
        kubectl_delete_keywords = KubectlFileDeleteKeywords(ssh_connection)

        snapshot_pod_name = "powerstoretest-snapshot-restore-0"
        get_logger().log_teardown_step(f"Clean up the snapshot pod {snapshot_pod_name}.")
        kubectl_delete_keywords.delete_resources(f"/home/sysadmin/{snapshot_pod_yaml}", True)

        teardown_snapshot_name = "csi-powerstore-pvc-snapshot"
        get_logger().log_teardown_step(f"Clean up the snapshot {teardown_snapshot_name}.")
        kubectl_delete_keywords.delete_resources(f"/home/sysadmin/{snapshot_yaml}", True)

        test_pod_name = "powerstoretest-0"
        get_logger().log_teardown_step(f"Clean up the test pod {test_pod_name}.")
        kubectl_delete_keywords.delete_resources(f"/home/sysadmin/{test_pod_yaml}", True)

        get_logger().log_teardown_step("Remove test yaml files")
        for teardown_file_name in dell_storage_files:
            FileKeywords(ssh_connection).delete_file(f"/home/sysadmin/{teardown_file_name}")

    request.addfinalizer(common_dell_storage_teardown)
    request.addfinalizer(teardown)

    make_sure_dell_storage_application_applied()

    get_logger().log_test_case_step("Check if all dell-storage pods are running")
    pod_prefix = "csi-powerstore"
    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
    pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
    validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
    validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt is exist")
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Access to {pod_name} pod success")

    get_logger().log_test_case_step("Creating volumesnapshot via yaml")
    yaml_path = "/home/sysadmin/dell-storage-csi-powerstore-snapshot.yaml"
    KubectlFileApplyKeywords(ssh_connection=ssh_connection).apply_resource_from_yaml(yaml_path)

    snapshot_name = "csi-powerstore-pvc-snapshot"
    get_logger().log_test_case_step(f"Waiting for {snapshot_name} is ready to use")
    expect_status = "true"
    snapshot_status = KubectlGetVolumesnapshotsKeywords(ssh_connection).wait_for_volumesnapshot_status(snapshot_name, expect_status, namespace)
    validate_equals(snapshot_status, True, "Verify snapshot is readt to use")

    get_logger().log_test_case_step("Creating volume snapshot pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-powerstoretest-snapshot.yaml"
    KubectlFileApplyKeywords(ssh_connection=ssh_connection).apply_resource_from_yaml(yaml_path)

    pod_name = "powerstoretest-snapshot-restore-0"
    get_logger().log_test_case_step(f"Check if test snapshot {pod_name} pod is running")
    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
    validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    get_logger().log_test_case_step(f"Check whether volumesnapshot {pod_name} pod has test.txt file")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"test.txt is on {pod_name} pod.")


@mark.p2
@mark.lab_dell_storage
def test_remove_dell_storage_app(request):
    """
    Remove and apply the dell-storage application.

    Test Steps:
        - Run this command "system application-remove dell-storage"
        - The status of the application should change to uploaded
        - Run this command "system application-apply"
        - The dell-storage application was applied

    Args: None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dell_storage_app_name = "dell-storage"

    make_sure_dell_storage_application_applied()

    get_logger().log_test_case_step("Remove dell-storage application")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(dell_storage_app_name)
    SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Re-Apply dell-storage")
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name=dell_storage_app_name)

    request.addfinalizer(common_dell_storage_teardown)


@mark.p2
@mark.lab_dell_storage
def test_delete_dell_storage_app(request):
    """
    Testing remove, delete, upload and apply the dell-storage application.

    Test Steps:
        - make sure dell-storage is applied
        - Run command "system application-remove dell-storage"
        - The status of the application should change to uploaded
        - Run command "system application-delete dell-storage"
        - make sure dell-storage is deleted
        - run command "system application-upload dell-storage*.tgz"
        - make sure the status of the application should change to uploaded
        - Run this command "system application-apply"
        - The dell-storage application was applied

    Args: None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dell_storage_app_name = "dell-storage"

    make_sure_dell_storage_application_applied()

    get_logger().log_test_case_step("Remove dell-storage application")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(dell_storage_app_name)
    SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Delete dell-storage application")
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(dell_storage_app_name)
    system_application_delete_input.set_force_deletion(False)
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(delete_msg, f"Application {dell_storage_app_name} deleted.\n", "Application deletion message validation")

    get_logger().log_test_case_step("Make sure that dell-storage was deleted")
    validate_equals_with_retry(lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name), False, f"Validate {dell_storage_app_name} was properly deleted", timeout=60)
    get_logger().log_info("Application dell-storage was properly deleted")

    get_logger().log_test_case_step("Upload dell-storage application")
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    system_application_upload_input = SystemApplicationUploadInput()
    system_application_upload_input.set_app_name(dell_storage_app_name)
    system_application_upload_input.set_tar_file_path(f"{base_path}{dell_storage_app_name}*.tgz")
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    oidc_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    validate_equals(oidc_app_status, "uploaded", f"{dell_storage_app_name} upload status validation")

    get_logger().log_test_case_step("Re-Apply dell-storage")
    make_sure_dell_storage_application_applied()

    request.addfinalizer(common_dell_storage_teardown)


@mark.p2
@mark.lab_dell_storage
def test_abort_dell_storage_app(request):
    """
    Testing apply, abort, remove and apply the dell-storage application.

    Test Steps:
        - make sure dell-storage is applied
        - Run command "system application-apply dell-storage && system application-abort dell-storage"
        - make sure dell-storage status is apply-failed and the progess is "operation aborted by user"
        - run command "system application-remove dell-storage"
        - make sure the status of the application should change to uploaded
        - Run this command "system application-apply"
        - The dell-storage application was applied

    Args: None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dell_storage_app_name = "dell-storage"

    make_sure_dell_storage_application_applied()

    get_logger().log_test_case_step("Abort dell-storage application")
    SystemApplicationAbortKeywords(ssh_connection).system_application_apply_and_abort(dell_storage_app_name, False)

    get_logger().log_test_case_step(f"Check if {dell_storage_app_name} abort is success")
    validate_equals_with_retry(lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(), "apply-failed", f"{dell_storage_app_name} abort status validation", timeout=60)

    expected_progress_msg = "operation aborted by user"
    validate_equals_with_retry(lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_progress(), expected_progress_msg, f"{dell_storage_app_name} abort progress validation", timeout=60)

    get_logger().log_test_case_step("Remove dell-storage application")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(dell_storage_app_name)
    SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Re-Apply dell-storage")
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name=dell_storage_app_name)

    request.addfinalizer(common_dell_storage_teardown)


@mark.p2
@mark.lab_is_simplex
@mark.lab_dell_storage
def test_node_reboot_with_pvc_pod_dell_storage_iscsi(request):
    """
    Test case: This Test case is to test dell storage resiliency after rebooting

    Test Steps:
        - Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.
        - Check current dell-storage app status.
        - Create powerstoreOverrides.yaml file to use as user-overrides (ISCSI)
        - Set up the storage network from DM
        - Update user-overrides for CSI-Powerstore chart.
        - Apply dell-storage.
        - Check if all pods are running.
        - Create dell storage PVC and pod
        - Write a test.txt file on test pod
        - pod sync
        - Reboot the controller-0 node through the sudo reboot command
        - Make sure that the node comes up again
        - Connect to the LAB and make sure that the dell-storage pods are up and running
        - Make sure that the test PVC and POD are still running.
        - Make sure that the file created before the reboot is still saved in the test pod.

    Teardown:
        - Remove test stuff.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-pod.yaml", ignore_not_found=True)

    get_logger().log_test_case_step("Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.")

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status. ")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)
    request.addfinalizer(common_dell_storage_teardown)
    request.addfinalizer(teardown)

    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    make_sure_dell_storage_application_applied()
    get_logger().log_test_case_step("Check if all dell-storage pods are running")

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)

    get_logger().log_test_case_step("Reboot the controller-0 node through the sudo reboot command")
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    pre_uptime = host_list_keywords.get_uptime("controller-0")
    SystemHostRebootKeywords(ssh_connection).host_force_reboot()

    get_logger().log_test_case_step("Make sure that the node comes up again")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    host_back = host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)
    validate_equals(host_back, True, "controller-0 did not come back online after reboot")
    reboot_keywords = SystemHostRebootKeywords(ssh_connection)
    reboot_success = reboot_keywords.wait_for_force_reboot("controller-0", pre_uptime)
    validate_equals(reboot_success, True, "controller-0 reboot was not confirmed via uptime check")

    get_logger().log_test_case_step("Connect to the LAB and make sure that the dell-storage pods are up and running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step("Make sure that the test PVC and POD are still running.")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Make sure that the file created before the reboot is still saved in the test pod.")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)


@mark.p2
@mark.lab_is_simplex
@mark.lab_dell_storage
def test_node_reboot_with_pvc_pod_dell_storage_nfs(request):
    """
    Test case: This Test case is to test dell storage resiliency after rebooting

    Test Steps:
        - Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.
        - Check current dell-storage app status.
        - Create powerstoreOverrides.yaml file to use as user-overrides (NFS)
        - Set up the storage network from DM
        - Update user-overrides for CSI-Powerstore chart.
        - Apply dell-storage.
        - Check if all pods are running.
        - Create dell storage PVC and pod
        - Write a test.txt file on test pod
        - pod sync
        - Reboot the controller-0 node through the sudo reboot command
        - Make sure that the node comes up again
        - Connect to the LAB and make sure that the dell-storage pods are up and running
        - Make sure that the test PVC and POD are still running.
        - Make sure that the file created before the reboot is still saved in the test pod.

    Teardown:
        - Remove test stuff.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-nfs-pod.yaml", ignore_not_found=True)

    get_logger().log_test_case_step("Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.")

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status. ")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)
    request.addfinalizer(common_dell_storage_teardown)
    request.addfinalizer(teardown)

    test_pod_yaml = "dell-storage-test-nfs-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    make_sure_dell_storage_application_applied()
    get_logger().log_test_case_step("Check if all dell-storage pods are running")

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-nfs-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)

    get_logger().log_test_case_step("Reboot the controller-0 node through the sudo reboot command")
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    pre_uptime = host_list_keywords.get_uptime("controller-0")
    SystemHostRebootKeywords(ssh_connection).host_force_reboot()

    get_logger().log_test_case_step("Make sure that the node comes up again")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    host_back = host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)
    validate_equals(host_back, True, "controller-0 did not come back online after reboot")
    reboot_keywords = SystemHostRebootKeywords(ssh_connection)
    reboot_success = reboot_keywords.wait_for_force_reboot("controller-0", pre_uptime)
    validate_equals(reboot_success, True, "controller-0 reboot was not confirmed via uptime check")

    get_logger().log_test_case_step("Connect to the LAB and make sure that the dell-storage pods are up and running")
    verify_dell_storage_pods_are_running(ssh_connection)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Make sure that the test PVC and POD are still running.")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Make sure that the file created before the reboot is still saved in the test pod.")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)


@mark.p2
@mark.lab_is_simplex
@mark.lab_dell_storage
def test_lock_unlock_node_with_pvc_pod_dell_storage_iscsi(request):
    """
    Test case: This Test case is to test dell storage resiliency after rebooting

    Test Steps:
        - Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.
        - Check current dell-storage app status.
        - Create powerstoreOverrides.yaml file to use as user-overrides (ISCSI)
        - Set up the storage network from DM
        - Update user-overrides for CSI-Powerstore chart.
        - Apply dell-storage.
        - Check if all pods are running.
        - Create dell storage PVC and pod
        - Write a test.txt file on test pod
        - pod sync
        - Lock controller-0 node
        - Unlock controller-0 node
        - Make sure that the node comes up again
        - Connect to the LAB and make sure that the dell-storage pods are up and running
        - Make sure that the test PVC and POD are still running.
        - Make sure that the file created before the reboot is still saved in the test pod.

    Teardown:
        - Remove test stuff.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-pod.yaml", ignore_not_found=True)

    get_logger().log_test_case_step("Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.")

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status. ")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)
    request.addfinalizer(common_dell_storage_teardown)
    request.addfinalizer(teardown)

    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    make_sure_dell_storage_application_applied()
    get_logger().log_test_case_step("Check if all dell-storage pods are running")

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Access to {pod_name} pod success")

    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    get_logger().log_test_case_step("Lock controller-0 node")
    lock_success = host_lock_keywords.lock_host("controller-0")
    validate_equals(lock_success, True, "controller-0 was not locked successfully")

    get_logger().log_test_case_step("Unlock controller-0 node")
    unlock_success = host_lock_keywords.unlock_host("controller-0")
    validate_equals(unlock_success, True, "controller-0 was not unlocked successfully")

    get_logger().log_test_case_step("Make sure that the node comes up again")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    host_back = host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)
    validate_equals(host_back, True, "controller-0 did not come back online after reboot")

    get_logger().log_test_case_step("Connect to the LAB and make sure that the dell-storage pods are up and running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step("Make sure that the test PVC and POD are still running.")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Make sure that the file created before the reboot is still saved in the test pod.")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)


@mark.p2
@mark.lab_is_simplex
@mark.lab_dell_storage
def test_lock_unlock_node_with_pvc_pod_dell_storage_nfs(request):
    """
    Test case: This Test case is to test dell storage resiliency after rebooting

    Test Steps:
        - Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.
        - Check current dell-storage app status.
        - Create powerstoreOverrides.yaml file to use as user-overrides (NFS)
        - Set up the storage network from DM
        - Update user-overrides for CSI-Powerstore chart.
        - Apply dell-storage.
        - Check if all pods are running.
        - Create dell storage PVC and pod
        - Write a test.txt file on test pod
        - pod sync
        - Lock controller-0 node
        - Unlock controller-0 node
        - Make sure that the node comes up again
        - Connect to the LAB and make sure that the dell-storage pods are up and running
        - Make sure that the test PVC and POD are still running.
        - Make sure that the file created before the reboot is still saved in the test pod.

    Teardown:
        - Remove test stuff.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-nfs-pod.yaml", ignore_not_found=True)

    request.addfinalizer(common_dell_storage_teardown)
    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.")

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status. ")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    test_pod_yaml = "dell-storage-test-nfs-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    make_sure_dell_storage_application_applied()
    get_logger().log_test_case_step("Check if all dell-storage pods are running")

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-nfs-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)

    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    get_logger().log_test_case_step("Lock controller-0 node")
    lock_success = host_lock_keywords.lock_host("controller-0")
    validate_equals(lock_success, True, "controller-0 was not locked successfully")

    get_logger().log_test_case_step("Unlock controller-0 node")
    unlock_success = host_lock_keywords.unlock_host("controller-0")
    validate_equals(unlock_success, True, "controller-0 was not unlocked successfully")

    get_logger().log_test_case_step("Make sure that the node comes up again")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    host_back = host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)
    validate_equals(host_back, True, "controller-0 did not come back online after reboot")

    get_logger().log_test_case_step("Connect to the LAB and make sure that the dell-storage pods are up and running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step("Make sure that the test PVC and POD are still running.")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Make sure that the test PVC and POD are still running.")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Make sure that the file created before the reboot is still saved in the test pod.")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)


@mark.p2
@mark.lab_is_simplex
@mark.lab_dell_storage
def test_power_off_node_with_pvc_pod_dell_storage_iscsi(request):
    """
    Test case: This Test case is to test dell storage resiliency after rebooting

    Test Steps:
        - Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.
        - Check current dell-storage app status.
        - Create powerstoreOverrides.yaml file to use as user-overrides (ISCSI)
        - Set up the storage network from DM
        - Update user-overrides for CSI-Powerstore chart.
        - Apply dell-storage.
        - Check if all pods are running.
        - Create dell storage PVC and pod
        - Write a test.txt file on test pod
        - pod sync
        - Power Off controller-0 through IPMITOOLS
        - Wait for some time (2 minutes)
        - Power On controller-0 through IPMITOOLS
        - Wait for the controller-0 to be up and running again
        - Connect to the LAB and make sure that the dell-storage pods are up and running
        - Make sure that the test PVC and POD are still running.
        - Make sure that the file created before powering off is still saved in the test pod.

    Teardown:
        - Remove test stuff.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    # IPMI commands are executed locally (on the machine running the
    # automation) rather than over an SSH connection. On a simplex lab the
    # controller's own SSH session dies with the node, so a power-on issued
    # over it never reaches the BMC.
    power_chassis = PowerKeywords(None)

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        """Power controller-0 back on, wait for it to recover, and remove the test pod resources."""
        power_chassis.power_on_from_localhost("controller-0", ignore_error=True)

        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-pod.yaml", ignore_not_found=True)

    request.addfinalizer(common_dell_storage_teardown)
    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    make_sure_dell_storage_application_applied()
    get_logger().log_test_case_step("Check if all dell-storage pods are running")

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)

    get_logger().log_test_case_step("sync pod")
    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Power Off controller-0 through IPMITOOLS ")
    power_off_rc = power_chassis.power_off_from_localhost("controller-0", ignore_error=True)
    validate_equals(power_off_rc, 0, "controller-0 IPMI power off command was not accepted by the BMC")

    get_logger().log_test_case_step("Wait for some time (2 minutes)")
    sleep(120)

    get_logger().log_test_case_step("Power on controller-0 through IPMITOOLS ")
    power_on_rc = power_chassis.power_on_from_localhost("controller-0", ignore_error=True)
    validate_equals(power_on_rc, 0, "controller-0 IPMI power on command was not accepted by the BMC")

    get_logger().log_test_case_step("Make sure that the node comes up again")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    host_back = host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)
    validate_equals(host_back, True, "controller-0 did not come back online after Powering Off and then Powering On")

    get_logger().log_test_case_step("Connect to the LAB and make sure that the dell-storage pods are up and running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step("Make sure that the file created before powering off is still saved in the test pod.")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)


@mark.p2
@mark.lab_is_simplex
@mark.lab_dell_storage
def test_power_off_node_with_pvc_pod_dell_storage_nfs(request):
    """
    Test case: This Test case is to test dell storage resiliency after rebooting

    Test Steps:
        - Check if dell-storage was uploaded. Uploading dell-storage app. If it's already applied, remove it.
        - Check current dell-storage app status.
        - Create powerstoreOverrides.yaml file to use as user-overrides (NFS)
        - Set up the storage network from DM
        - Update user-overrides for CSI-Powerstore chart.
        - Apply dell-storage.
        - Check if all pods are running.
        - Create dell storage PVC and pod
        - Write a test.txt file on test pod
        - pod sync
        - Power Off controller-0 through IPMITOOLS
        - Wait for some time (2 minutes)
        - Power On controller-0 through IPMITOOLS
        - Wait for the controller-0 to be up and running again
        - Connect to the LAB and make sure that the dell-storage pods are up and running
        - Make sure that the test PVC and POD are still running.
        - Make sure that the file created before powering off is still saved in the test pod.

    Teardown:
        - Remove test stuff.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    # IPMI commands are executed locally (on the machine running the
    # automation) rather than over an SSH connection. On a simplex lab the
    # controller's own SSH session dies with the node, so a power-on issued
    # over it never reaches the BMC.
    power_chassis = PowerKeywords(None)

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        """Power controller-0 back on, wait for it to recover, and remove the test pod resources."""
        power_chassis.power_on_from_localhost("controller-0", ignore_error=True)

        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-nfs-pod.yaml", ignore_not_found=True)

    request.addfinalizer(common_dell_storage_teardown)
    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    test_pod_yaml = "dell-storage-test-nfs-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    make_sure_dell_storage_application_applied()
    get_logger().log_test_case_step("Check if all dell-storage pods are running")

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-nfs-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)

    get_logger().log_test_case_step("sync pod")
    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Power Off controller-0 through IPMITOOLS ")
    power_off_rc = power_chassis.power_off_from_localhost("controller-0", ignore_error=True)
    validate_equals(power_off_rc, 0, "controller-0 IPMI power off command was not accepted by the BMC")

    get_logger().log_test_case_step("Wait for some time (2 minutes)")
    sleep(120)

    get_logger().log_test_case_step("Power on controller-0 through IPMITOOLS ")
    power_on_rc = power_chassis.power_on_from_localhost("controller-0", ignore_error=True)
    validate_equals(power_on_rc, 0, "controller-0 IPMI power on command was not accepted by the BMC")

    get_logger().log_test_case_step("Make sure that the node comes up again")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    host_back = host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)
    validate_equals(host_back, True, "controller-0 did not come back online after Powering Off and then Powering On")

    get_logger().log_test_case_step("Connect to the LAB and make sure that the dell-storage pods are up and running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step("Make sure that the file created before powering off is still saved in the test pod.")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)


@mark.p2
@mark.lab_dell_storage
def test_auto_downgrade_dell_storage_iscsi(request: FixtureRequest):
    """
    Update dell-storage application.

    Test Steps:
        - Check dell-storage app status.
        - Remove tarball from application base path
        - Copy tarball from /home/sysadmin to application base path
        - Create resources test pod via yaml
        - Check if test powerstoretest-0 pod is running
        - Creating text.txt file inside of powerstoretest-0 pod
        - Check if test.txt exists
        - Execute the command sudo touch /ostree/lock && sudo rm -f /ostree/lock to make sure the new tarball version is updated in the database
        - Verify dell-storage app version has changed after rollback

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-pod.yaml", ignore_not_found=True)

        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        # An update/rollback that is interrupted (e.g. aborted) leaves the app in the
        # transient 'recovering' state, and sysinv rejects abort/remove/apply while
        # recovering. Wait for the app to settle into a terminal state before acting.
        get_logger().log_teardown_step("Wait for dell-storage to leave transient state")
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original dell-storage version")

            base_application_path = app_config.get_base_application_path()

            # Capture the rolled-back version before wiping the app so its tarball can be cleaned up.
            rollback_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
            rollback_version = rollback_app_info.get_system_application_object().get_version()

            # Wipe dell-storage completely: remove the release (if applied) and delete the
            # app entry. Force both so a failed/transient state can't block the cleanup.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            # 'system application-delete' returns as soon as the CLI is accepted, but
            # sysinv removes the app entry asynchronously, so poll until it is gone
            # instead of checking once (which races the delete and fails spuriously).
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove the rolled-back version tarball from the application base path.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{rollback_version}.tgz")

            # Restore the original dell-storage version (e.g. 26.10) that was moved
            # to /home/sysadmin before the rollback. Reference the exact tarball by
            # the recorded original version so the correct file is restored.
            original_tarball = f"dell-storage-{current_version}.tgz"

            # Move the original version tarball from /home/sysadmin back to base_application_path
            get_logger().log_teardown_step("Move original tarball to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/{original_tarball}", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            # Upload original version. 'system application-upload' expects a single
            # concrete file path, not a glob.

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}{original_tarball}")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
            system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
            dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply original version
            common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")
            # Copy original tarball from /home/sysadmin to base_application_path
            get_logger().log_teardown_step("Move original tarball to base application path")
            FileKeywords(ssh_connection).move_file("/home/sysadmin/dell-storage*.tgz", app_config.get_base_application_path(), sudo=True)

            # Move rollback tarball from base_application_path to /home/sysadmin
            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

        refresh_os_tree_keywords(ssh_connection)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current dell-storage app version")
    current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    current_version = current_app_info.get_system_application_object().get_version()

    # Validate rollback tarball version differs from installed version. This is a
    # downgrade test, so the target is the rollback (older) tarball, not the latest one.
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    tarball_version = re.search(r"dell-storage-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Rollback tarball version must differ from installed version")

    # Transfer rollback tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball_rollback(), temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(ssh_connection).remount_read_write("/usr")

    # Copy dell-storage*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to application base path")
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ostree_keywords = OstreeKeywords(ssh_connection)

    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)

    get_logger().log_test_case_step("Execute the command sudo touch /ostree/lock && sudo rm -f /ostree/lock to make sure the new tarball version is updated in the database")
    ostree_keywords.ostree_update()

    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "updating",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )

    get_logger().log_test_case_step("Make sure that the dell-storage application is applied after the downgrade")
    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "applied",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )
    rollback_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    rollback_app_status = rollback_app_info.get_system_application_object().get_status()
    validate_equals(rollback_app_status, SystemApplicationStatusEnum.APPLIED.value, "dell-storage application should be applied after downgrade")

    get_logger().log_test_case_step("Verify dell-storage app version has changed after rollback")
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)


@mark.p2
@mark.lab_dell_storage
def test_auto_upgrade_dell_storage_iscsi(request: FixtureRequest):
    """
    Upgrade dell-storage application.

    The lab starts with the rollback tarball (dell_storage_app_tarball_rollback) applied and is
    upgraded to the newer version defined by dell_storage_app_tarball.

    Test Steps:
        - Check dell-storage app status.
        - Make sure the rollback (older) version is the applied version before upgrading.
        - Transfer upgrade tarball from local machine to /home/sysadmin
        - Remove tarball from application base path
        - Copy upgrade tarball from /home/sysadmin to application base path
        - Execute the command sudo touch /ostree/lock && sudo rm -f /ostree/lock to make sure the new tarball version is updated in the database
        - Verify dell-storage app version has changed after upgrade

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def teardown():
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-pod.yaml", ignore_not_found=True)

        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        get_logger().log_teardown_step("Wait for dell-storage to leave transient state")
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original dell-storage version")

            base_application_path = app_config.get_base_application_path()

            upgraded_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
            upgraded_version = upgraded_app_info.get_system_application_object().get_version()

            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)

            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{upgraded_version}.tgz")
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{rollback_version}.tgz")

            # Move the latest version tarball from /home/sysadmin/test_upgrade back to base_application_path
            get_logger().log_teardown_step("Move latest tarball from test_upgrade folder to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/test_upgrade/dell-storage-{original_version}.tgz", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}dell-storage-{original_version}.tgz")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply original version
            common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        else:
            # The system is still on the rollback version (e.g. the test failed mid-run before
            # the upgrade completed). The lab baseline is the latest version, so upgrade the
            # system to the latest tarball that was stashed in /home/sysadmin/test_upgrade.
            get_logger().log_teardown_step("System still on rollback version - restoring latest version")

            base_application_path = app_config.get_base_application_path()

            # Wipe dell-storage completely so the latest tarball can be uploaded/applied cleanly.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove the rollback version tarball from the application base path so only the
            # latest tarball remains.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{current_version}.tgz")

            # Restore the latest version tarball that was stashed in /home/sysadmin/test_upgrade.

            get_logger().log_teardown_step("Move latest tarball from test_upgrade folder to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/test_upgrade/dell-storage-{original_version}.tgz", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            # Upload latest version. 'system application-upload' expects a single concrete file path.
            # try:
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}dell-storage-{original_version}.tgz")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)

            # except Exception as e:
            #    get_logger.log_info(f"dell-storage is already uploaded {e}")

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply latest version
            common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        refresh_os_tree_keywords(ssh_connection)

    request.addfinalizer(teardown)

    app_config = ConfigurationManager.get_app_config()

    # The upgrade starts from the rollback (older) tarball and upgrades to dell_storage_app_tarball.
    rollback_tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    rollback_version = re.search(r"dell-storage-(.+)\.tgz", rollback_tarball_filename).group(1)
    tarball_filename = app_config.get_dell_storage_app_tarball().split("/")[-1]

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(ssh_connection).remount_read_write("/usr")
    MountKeywords(ssh_connection).remount_read_write("/home/sysadmin/")

    # Record the dell-storage version installed before testing (the lab baseline / latest version).
    get_logger().log_test_case_step("Record original dell-storage app version before testing")
    original_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    original_version = original_app_info.get_system_application_object().get_version()
    get_logger().log_info(f"Original {dell_storage_app_name} version before testing: {original_version}")

    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    rollback_tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{rollback_tarball_filename}"
    # The move_file above relocates the base-path tarball into /home/sysadmin as root, so a
    # same-named file is now root-owned there. The non-sudo SFTP upload cannot overwrite a
    # root-owned file (Errno 13 Permission denied), so remove any stale copy (with sudo) first.

    FileKeywords(ssh_connection).create_directory("/home/sysadmin/test_upgrade")
    FileKeywords(ssh_connection).move_file("/home/sysadmin/dell-storage*.tgz", "/home/sysadmin/test_upgrade/", sudo=True)

    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball_rollback(), temp_remote_path)
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(dell_storage_app_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{rollback_tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(1800)
    SystemApplicationUpdateKeywords(ssh_connection).system_application_update(system_application_update_input)

    # Record current version before upgrade. This is expected to be the rollback (older) version.
    get_logger().log_test_case_step("Record current dell-storage app version")
    current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    current_version = current_app_info.get_system_application_object().get_version()
    validate_equals(current_version, rollback_version, "Installed version must be the rollback (older) version before upgrade")

    # Validate upgrade tarball version differs from installed version

    tarball_version = re.search(r"dell-storage-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Upgrade tarball version must differ from installed version")

    # Transfer upgrade tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer upgrade tarball from local machine to /home/sysadmin")
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"

    FileKeywords(ssh_connection).delete_file("/home/sysadmin/dell-storage*.tgz")
    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball(), temp_remote_path)

    # Move dell-storage*.tgz (rollback version) from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    # Copy upgrade tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to application base path")
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ostree_keywords = OstreeKeywords(ssh_connection)

    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Execute the command sudo touch /ostree/lock && sudo rm -f /ostree/lock to make sure the new tarball version is updated in the database")
    ostree_keywords.ostree_update()

    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "updating",
        f"{dell_storage_app_name} updating status validation",
        timeout=300,
    )

    get_logger().log_test_case_step("Make sure that the dell-storage application is applied after the upgrade")
    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "applied",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )
    upgraded_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    upgraded_version = upgraded_app_info.get_system_application_object().get_version()
    upgraded_app_status = upgraded_app_info.get_system_application_object().get_status()
    validate_equals(upgraded_app_status, SystemApplicationStatusEnum.APPLIED.value, "dell-storage application should be applied after upgrade")

    get_logger().log_test_case_step("Verify dell-storage app version has changed after upgrade")
    validate_not_equals(current_version, upgraded_version, "Application version should have changed after upgrade")
    validate_equals(upgraded_version, tarball_version, "Application should have been upgraded to the dell_storage_app_tarball version")


@mark.p2
@mark.lab_dell_storage
def test_auto_upgrade_dell_storage_nfs(request: FixtureRequest):
    """
    Upgrade dell-storage application.

    The lab starts with the rollback tarball (dell_storage_app_tarball_rollback) applied and is
    upgraded to the newer version defined by dell_storage_app_tarball.

    Test Steps:
        - Check dell-storage app status.
        - Make sure the rollback (older) version is the applied version before upgrading.
        - Transfer upgrade tarball from local machine to /home/sysadmin
        - Remove tarball from application base path
        - Copy upgrade tarball from /home/sysadmin to application base path
        - Execute the command sudo touch /ostree/lock && sudo rm -f /ostree/lock to make sure the new tarball version is updated in the database
        - Verify dell-storage app version has changed after upgrade

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def teardown():
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-nfs-pod.yaml", ignore_not_found=True)

        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        # An update/upgrade that is interrupted (e.g. aborted) leaves the app in the
        # transient 'recovering' state, and sysinv rejects abort/remove/apply while
        # recovering. Wait for the app to settle into a terminal state before acting.
        get_logger().log_teardown_step("Wait for dell-storage to leave transient state")
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original dell-storage version")

            base_application_path = app_config.get_base_application_path()

            # Capture the upgraded version before wiping the app so its tarball can be cleaned up.
            upgraded_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
            upgraded_version = upgraded_app_info.get_system_application_object().get_version()

            # Wipe dell-storage completely: remove the release (if applied) and delete the
            # app entry. Force both so a failed/transient state can't block the cleanup.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            # 'system application-delete' returns as soon as the CLI is accepted, but
            # sysinv removes the app entry asynchronously, so poll until it is gone
            # instead of checking once (which races the delete and fails spuriously).
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove any leftover tarballs from the application base path so only the
            # tarball we are about to restore (the latest version) remains.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{upgraded_version}.tgz")
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{rollback_version}.tgz")

            # The lab baseline is the latest dell-storage version (dell_storage_app_tarball),
            # not the rollback version used to start the upgrade. Restore the latest tarball
            # that was stashed in /home/sysadmin/test_upgrade during setup so teardown leaves
            # the system on the latest version.

            # Move the latest version tarball from /home/sysadmin/test_upgrade back to base_application_path
            get_logger().log_teardown_step("Move latest tarball from test_upgrade folder to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/test_upgrade/dell-storage-{original_version}.tgz", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            # Upload original version. 'system application-upload' expects a single
            # concrete file path, not a glob.

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}dell-storage-{original_version}.tgz")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
            system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
            dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply original version
            common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        else:
            # The system is still on the rollback version (e.g. the test failed mid-run before
            # the upgrade completed). The lab baseline is the latest version, so upgrade the
            # system to the latest tarball that was stashed in /home/sysadmin/test_upgrade.
            get_logger().log_teardown_step("System still on rollback version - restoring latest version")

            base_application_path = app_config.get_base_application_path()

            # Wipe dell-storage completely so the latest tarball can be uploaded/applied cleanly.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove the rollback version tarball from the application base path so only the
            # latest tarball remains.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{current_version}.tgz")

            # Restore the latest version tarball that was stashed in /home/sysadmin/test_upgrade.

            get_logger().log_teardown_step("Move latest tarball from test_upgrade folder to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/test_upgrade/dell-storage-{original_version}.tgz", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            # Upload latest version. 'system application-upload' expects a single concrete file path.

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}dell-storage-{original_version}.tgz")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)

            # dell_storage_app_status = validate_equals_with_retry(
            #     lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
            #     "uploaded",
            #     f"{dell_storage_app_name} upload status validation",
            #     timeout=300,
            # )

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply latest version
            common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        refresh_os_tree_keywords(ssh_connection)

    request.addfinalizer(teardown)

    app_config = ConfigurationManager.get_app_config()

    # The upgrade starts from the rollback (older) tarball and upgrades to dell_storage_app_tarball.
    rollback_tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    rollback_version = re.search(r"dell-storage-(.+)\.tgz", rollback_tarball_filename).group(1)
    tarball_filename = app_config.get_dell_storage_app_tarball().split("/")[-1]

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(ssh_connection).remount_read_write("/usr")
    MountKeywords(ssh_connection).remount_read_write("/home/sysadmin/")

    # Record the dell-storage version installed before testing (the lab baseline / latest version).
    get_logger().log_test_case_step("Record original dell-storage app version before testing")
    original_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    original_version = original_app_info.get_system_application_object().get_version()
    get_logger().log_info(f"Original {dell_storage_app_name} version before testing: {original_version}")

    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    rollback_tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{rollback_tarball_filename}"
    # The move_file above relocates the base-path tarball into /home/sysadmin as root, so a
    # same-named file is now root-owned there. The non-sudo SFTP upload cannot overwrite a
    # root-owned file (Errno 13 Permission denied), so remove any stale copy (with sudo) first.

    FileKeywords(ssh_connection).create_directory("/home/sysadmin/test_upgrade")
    FileKeywords(ssh_connection).move_file("/home/sysadmin/dell-storage*.tgz", "/home/sysadmin/test_upgrade/", sudo=True)

    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball_rollback(), temp_remote_path)
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(dell_storage_app_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{rollback_tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(1800)
    SystemApplicationUpdateKeywords(ssh_connection).system_application_update(system_application_update_input)

    # Record current version before upgrade. This is expected to be the rollback (older) version.
    get_logger().log_test_case_step("Record current dell-storage app version")
    current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    current_version = current_app_info.get_system_application_object().get_version()
    validate_equals(current_version, rollback_version, "Installed version must be the rollback (older) version before upgrade")

    # Validate upgrade tarball version differs from installed version

    tarball_version = re.search(r"dell-storage-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Upgrade tarball version must differ from installed version")

    # Transfer upgrade tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer upgrade tarball from local machine to /home/sysadmin")
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"

    FileKeywords(ssh_connection).delete_file("/home/sysadmin/dell-storage*.tgz")
    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball(), temp_remote_path)

    # Move dell-storage*.tgz (rollback version) from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    # Copy upgrade tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to application base path")
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ostree_keywords = OstreeKeywords(ssh_connection)

    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Execute the command sudo touch /ostree/lock && sudo rm -f /ostree/lock to make sure the new tarball version is updated in the database")
    ostree_keywords.ostree_update()

    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "updating",
        f"{dell_storage_app_name} updating status validation",
        timeout=300,
    )

    get_logger().log_test_case_step("Make sure that the dell-storage application is applied after the upgrade")
    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "applied",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )
    upgraded_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    upgraded_version = upgraded_app_info.get_system_application_object().get_version()
    upgraded_app_status = upgraded_app_info.get_system_application_object().get_status()
    validate_equals(upgraded_app_status, SystemApplicationStatusEnum.APPLIED.value, "dell-storage application should be applied after upgrade")

    get_logger().log_test_case_step("Verify dell-storage app version has changed after upgrade")
    validate_not_equals(current_version, upgraded_version, "Application version should have changed after upgrade")
    validate_equals(upgraded_version, tarball_version, "Application should have been upgraded to the dell_storage_app_tarball version")


@mark.p2
@mark.lab_dell_storage
def test_auto_downgrade_dell_storage_nfs(request: FixtureRequest):
    """
    Update dell-storage application.

    Test Steps:
        - Check dell-storage app status.
        - Remove tarball from application base path
        - Copy tarball from /home/sysadmin to application base path
        - Execute the command sudo touch /ostree/lock && sudo rm -f /ostree/lock to make sure the new tarball version is updated in the database
        - Verify dell-storage app version has changed after rollback

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-nfs-pod.yaml", ignore_not_found=True)

        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        # An update/rollback that is interrupted (e.g. aborted) leaves the app in the
        # transient 'recovering' state, and sysinv rejects abort/remove/apply while
        # recovering. Wait for the app to settle into a terminal state before acting.
        get_logger().log_teardown_step("Wait for dell-storage to leave transient state")
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original dell-storage version")

            base_application_path = app_config.get_base_application_path()

            # Capture the rolled-back version before wiping the app so its tarball can be cleaned up.
            rollback_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
            rollback_version = rollback_app_info.get_system_application_object().get_version()

            # Wipe dell-storage completely: remove the release (if applied) and delete the
            # app entry. Force both so a failed/transient state can't block the cleanup.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)

            # validate_equals_with_retry(
            #     lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
            #     False,
            #     f"{dell_storage_app_name} fully wiped before restore",
            #     timeout=300,
            # )

            # Remove the rolled-back version tarball from the application base path.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{rollback_version}.tgz")

            # Restore the original dell-storage version (e.g. 26.10) that was moved
            # to /home/sysadmin before the rollback. Reference the exact tarball by
            # the recorded original version so the correct file is restored.
            original_tarball = f"dell-storage-{current_version}.tgz"

            # Move the original version tarball from /home/sysadmin back to base_application_path
            get_logger().log_teardown_step("Move original tarball to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/{original_tarball}", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            # Upload original version. 'system application-upload' expects a single
            # concrete file path, not a glob.
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}{original_tarball}")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply original version
            common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")
            # Copy original tarball from /home/sysadmin to base_application_path
            get_logger().log_teardown_step("Move original tarball to base application path")
            FileKeywords(ssh_connection).move_file("/home/sysadmin/dell-storage*.tgz", app_config.get_base_application_path(), sudo=True)

            # Move rollback tarball from base_application_path to /home/sysadmin
            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

        refresh_os_tree_keywords(ssh_connection)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current dell-storage app version")
    current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    current_version = current_app_info.get_system_application_object().get_version()

    # Validate tarball version differs from installed version
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_dell_storage_app_tarball().split("/")[-1]
    tarball_version = re.search(r"dell-storage-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Tarball version must differ from installed version")

    # Transfer tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_dell_storage_app_tarball().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball(), temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(ssh_connection).remount_read_write("/usr")

    # Copy dell-storage*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to application base path")
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ostree_keywords = OstreeKeywords(ssh_connection)

    test_pod_yaml = "dell-storage-test-nfs-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-nfs-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)

    get_logger().log_test_case_step("Execute the command sudo touch /ostree/lock && sudo rm -f /ostree/lock to make sure the new tarball version is updated in the database")
    ostree_keywords.ostree_update()

    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "updating",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )

    get_logger().log_test_case_step("Make sure that the dell-storage application is applied after the downgrade")
    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "applied",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )

    rollback_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    rollback_app_status = rollback_app_info.get_system_application_object().get_status()
    validate_equals(rollback_app_status, SystemApplicationStatusEnum.APPLIED.value, "dell-storage application should be applied after downgrade")

    get_logger().log_test_case_step("Verify dell-storage app version has changed after rollback")
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)


@mark.p2
@mark.lab_dell_storage
def test_manual_downgrade_dell_storage_iscsi(request: FixtureRequest):
    """
    Manually downgrade dell-storage application. Function for ISCSI protocol.

    Test Steps:
        - Check dell-storage app status.
        - Remove tarball from application base path
        - Copy tarball from /home/sysadmin to application base path
        - Create resources test pod via yaml
        - Check if test powerstoretest-0 pod is running
        - Creating text.txt file inside of powerstoretest-0 pod
        - Check if test.txt exists
        - Execute system application-update with the tarball filename to update the dell-storage app
        - Make sure that the dell-storage application is applied after the downgrade
        - Verify dell-storage app version has changed after rollback

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-pod.yaml", ignore_not_found=True)

        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        # An update/rollback that is interrupted (e.g. aborted) leaves the app in the
        # transient 'recovering' state, and sysinv rejects abort/remove/apply while
        # recovering. Wait for the app to settle into a terminal state before acting.
        get_logger().log_teardown_step("Wait for dell-storage to leave transient state")
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original dell-storage version")

            base_application_path = app_config.get_base_application_path()

            # Capture the rolled-back version before wiping the app so its tarball can be cleaned up.
            rollback_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
            rollback_version = rollback_app_info.get_system_application_object().get_version()

            # Wipe dell-storage completely: remove the release (if applied) and delete the
            # app entry. Force both so a failed/transient state can't block the cleanup.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            # 'system application-delete' returns as soon as the CLI is accepted, but
            # sysinv removes the app entry asynchronously, so poll until it is gone
            # instead of checking once (which races the delete and fails spuriously).
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove the rolled-back version tarball from the application base path.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{rollback_version}.tgz")

            # Restore the original dell-storage version (e.g. 26.10) that was moved
            # to /home/sysadmin before the rollback. Reference the exact tarball by
            # the recorded original version so the correct file is restored.
            original_tarball = f"dell-storage-{current_version}.tgz"

            # Move the original version tarball from /home/sysadmin back to base_application_path
            get_logger().log_teardown_step("Move original tarball to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/{original_tarball}", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            # Upload original version. 'system application-upload' expects a single
            # concrete file path, not a glob.

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}{original_tarball}")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
            system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
            dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply original version
            common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")
            # Copy original tarball from /home/sysadmin to base_application_path
            get_logger().log_teardown_step("Move original tarball to base application path")
            FileKeywords(ssh_connection).move_file("/home/sysadmin/dell-storage*.tgz", app_config.get_base_application_path(), sudo=True)

            # Move rollback tarball from base_application_path to /home/sysadmin
            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

        refresh_os_tree_keywords(ssh_connection)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current dell-storage app version")
    current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    current_version = current_app_info.get_system_application_object().get_version()

    # Validate rollback tarball version differs from installed version. This is a
    # downgrade test, so the target is the rollback (older) tarball, not the latest one.
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    tarball_version = re.search(r"dell-storage-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Rollback tarball version must differ from installed version")

    # Transfer rollback tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball_rollback(), temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(ssh_connection).remount_read_write("/usr")

    # Copy dell-storage*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to application base path")
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)

    # Manually downgrade dell-storage with the tarball via 'system application-update'
    get_logger().log_test_case_step("Manually update dell-storage with tarball via system application-update")
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(dell_storage_app_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(1800)
    SystemApplicationUpdateKeywords(ssh_connection).system_application_update(system_application_update_input)

    get_logger().log_test_case_step("Make sure that the dell-storage application is applied after the downgrade")
    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "applied",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )

    rollback_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    rollback_app_status = rollback_app_info.get_system_application_object().get_status()
    validate_equals(rollback_app_status, SystemApplicationStatusEnum.APPLIED.value, "dell-storage application should be applied after downgrade")
    verify_dell_storage_pods_are_running(ssh_connection)
    get_logger().log_test_case_step("Verify dell-storage app version has changed after rollback")
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")


@mark.p2
@mark.lab_dell_storage
def test_manual_downgrade_dell_storage_nfs(request: FixtureRequest):
    """
    Manually downgrade dell-storage application. Function for NFS protocol.

    Test Steps:
        - Check dell-storage app status.
        - Remove tarball from application base path
        - Copy tarball from /home/sysadmin to application base path
        - Create resources test pod via yaml
        - Check if test powerstoretest-0 pod is running
        - Creating text.txt file inside of powerstoretest-0 pod
        - Check if test.txt exists
        - Execute system application-update with the tarball filename to update the dell-storage app
        - Make sure that the dell-storage application is applied after the downgrade
        - Verify dell-storage app version has changed after rollback

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-nfs-pod.yaml", ignore_not_found=True)

        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        # An update/rollback that is interrupted (e.g. aborted) leaves the app in the
        # transient 'recovering' state, and sysinv rejects abort/remove/apply while
        # recovering. Wait for the app to settle into a terminal state before acting.
        get_logger().log_teardown_step("Wait for dell-storage to leave transient state")
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original dell-storage version")

            base_application_path = app_config.get_base_application_path()

            # Capture the rolled-back version before wiping the app so its tarball can be cleaned up.
            rollback_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
            rollback_version = rollback_app_info.get_system_application_object().get_version()

            # Wipe dell-storage completely: remove the release (if applied) and delete the
            # app entry. Force both so a failed/transient state can't block the cleanup.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            # 'system application-delete' returns as soon as the CLI is accepted, but
            # sysinv removes the app entry asynchronously, so poll until it is gone
            # instead of checking once (which races the delete and fails spuriously).
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove the rolled-back version tarball from the application base path.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{rollback_version}.tgz")

            # Restore the original dell-storage version (e.g. 26.10) that was moved
            # to /home/sysadmin before the rollback. Reference the exact tarball by
            # the recorded original version so the correct file is restored.
            original_tarball = f"dell-storage-{current_version}.tgz"

            # Move the original version tarball from /home/sysadmin back to base_application_path
            get_logger().log_teardown_step("Move original tarball to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/{original_tarball}", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            # Upload original version. 'system application-upload' expects a single
            # concrete file path, not a glob.

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}{original_tarball}")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
            system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
            dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply original version
            common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")
            # Copy original tarball from /home/sysadmin to base_application_path
            get_logger().log_teardown_step("Move original tarball to base application path")
            FileKeywords(ssh_connection).move_file("/home/sysadmin/dell-storage*.tgz", app_config.get_base_application_path(), sudo=True)

            # Move rollback tarball from base_application_path to /home/sysadmin
            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

        refresh_os_tree_keywords(ssh_connection)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current dell-storage app version")
    current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    current_version = current_app_info.get_system_application_object().get_version()

    # Validate rollback tarball version differs from installed version. This is a
    # downgrade test, so the target is the rollback (older) tarball, not the latest one.
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    tarball_version = re.search(r"dell-storage-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Rollback tarball version must differ from installed version")

    # Transfer rollback tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball_rollback(), temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(ssh_connection).remount_read_write("/usr")

    # Copy dell-storage*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to application base path")
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    test_pod_yaml = "dell-storage-test-nfs-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Create resources test pod via yaml")
    yaml_path = "/home/sysadmin/dell-storage-test-nfs-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)

    # Manually downgrade dell-storage with the tarball via 'system application-update'
    get_logger().log_test_case_step("Manually update dell-storage with tarball via system application-update")
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(dell_storage_app_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(1800)
    SystemApplicationUpdateKeywords(ssh_connection).system_application_update(system_application_update_input)

    get_logger().log_test_case_step("Make sure that the dell-storage application is applied after the downgrade")
    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "applied",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )

    rollback_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    rollback_app_status = rollback_app_info.get_system_application_object().get_status()
    validate_equals(rollback_app_status, SystemApplicationStatusEnum.APPLIED.value, "dell-storage application should be applied after downgrade")
    verify_dell_storage_pods_are_running(ssh_connection)
    get_logger().log_test_case_step("Verify dell-storage app version has changed after rollback")
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")


@mark.p2
@mark.lab_dell_storage
def test_manual_upgrade_dell_storage_iscsi(request: FixtureRequest):
    """
    Upgrade dell-storage application.

    The lab starts with the rollback tarball (dell_storage_app_tarball_rollback) applied and is
    upgraded to the newer version defined by dell_storage_app_tarball.

    Test Steps:
        - Check dell-storage app status.
        - Make sure the rollback (older) version is the applied version before upgrading.
        - Transfer upgrade tarball from local machine to /home/sysadmin
        - Remove tarball from application base path
        - Copy upgrade tarball from /home/sysadmin to application base path
        - Execute the Update Command pointing to the upgraded tarball
        - Verify dell-storage app version has changed after upgrade

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"
    pod_name = "powerstoretest-0"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-pod.yaml", ignore_not_found=True)

        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        # An update/upgrade that is interrupted (e.g. aborted) leaves the app in the
        # transient 'recovering' state, and sysinv rejects abort/remove/apply while
        # recovering. Wait for the app to settle into a terminal state before acting.
        get_logger().log_teardown_step("Wait for dell-storage to leave transient state")
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original dell-storage version")

            base_application_path = app_config.get_base_application_path()

            # Capture the upgraded version before wiping the app so its tarball can be cleaned up.
            upgraded_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
            upgraded_version = upgraded_app_info.get_system_application_object().get_version()

            # Wipe dell-storage completely: remove the release (if applied) and delete the
            # app entry. Force both so a failed/transient state can't block the cleanup.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            # 'system application-delete' returns as soon as the CLI is accepted, but
            # sysinv removes the app entry asynchronously, so poll until it is gone
            # instead of checking once (which races the delete and fails spuriously).
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove any leftover tarballs from the application base path so only the
            # tarball we are about to restore (the latest version) remains.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{upgraded_version}.tgz")
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{rollback_version}.tgz")

            # The lab baseline is the latest dell-storage version (dell_storage_app_tarball),
            # not the rollback version used to start the upgrade. Restore the latest tarball
            # that was stashed in /home/sysadmin/test_upgrade during setup so teardown leaves
            # the system on the latest version.

            # Move the latest version tarball from /home/sysadmin/test_upgrade back to base_application_path
            get_logger().log_teardown_step("Move latest tarball from test_upgrade folder to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/test_upgrade/dell-storage-{original_version}.tgz", base_application_path, sudo=True)

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}dell-storage-{original_version}.tgz")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
            system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
            dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply original version
            common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        else:
            # The system is still on the rollback version (e.g. the test failed mid-run before
            # the upgrade completed). The lab baseline is the latest version, so upgrade the
            # system to the latest tarball that was stashed in /home/sysadmin/test_upgrade.
            get_logger().log_teardown_step("System still on rollback version - restoring latest version")

            base_application_path = app_config.get_base_application_path()

            # Wipe dell-storage completely so the latest tarball can be uploaded/applied cleanly.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove the rollback version tarball from the application base path so only the
            # latest tarball remains.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{current_version}.tgz")

            # Restore the latest version tarball that was stashed in /home/sysadmin/test_upgrade.

            get_logger().log_teardown_step("Move latest tarball from test_upgrade folder to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/test_upgrade/dell-storage-{original_version}.tgz", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            # Upload latest version. 'system application-upload' expects a single concrete file path.

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}dell-storage-{original_version}.tgz")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply latest version
            common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        refresh_os_tree_keywords(ssh_connection)

    request.addfinalizer(teardown)

    app_config = ConfigurationManager.get_app_config()

    # The upgrade starts from the rollback (older) tarball and upgrades to dell_storage_app_tarball.
    rollback_tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    rollback_version = re.search(r"dell-storage-(.+)\.tgz", rollback_tarball_filename).group(1)
    tarball_filename = app_config.get_dell_storage_app_tarball().split("/")[-1]

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(ssh_connection).remount_read_write("/usr")
    MountKeywords(ssh_connection).remount_read_write("/home/sysadmin/")

    # Record the dell-storage version installed before testing (the lab baseline / latest version).
    get_logger().log_test_case_step("Record original dell-storage app version before testing")
    original_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    original_version = original_app_info.get_system_application_object().get_version()
    get_logger().log_info(f"Original {dell_storage_app_name} version before testing: {original_version}")

    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    rollback_tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{rollback_tarball_filename}"
    # The move_file above relocates the base-path tarball into /home/sysadmin as root, so a
    # same-named file is now root-owned there. The non-sudo SFTP upload cannot overwrite a
    # root-owned file (Errno 13 Permission denied), so remove any stale copy (with sudo) first.

    FileKeywords(ssh_connection).create_directory("/home/sysadmin/test_upgrade")
    FileKeywords(ssh_connection).move_file("/home/sysadmin/dell-storage*.tgz", "/home/sysadmin/test_upgrade/", sudo=True)

    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball_rollback(), temp_remote_path)
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(dell_storage_app_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{rollback_tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(1800)
    SystemApplicationUpdateKeywords(ssh_connection).system_application_update(system_application_update_input)

    # Record current version before upgrade. This is expected to be the rollback (older) version.
    get_logger().log_test_case_step("Record current dell-storage app version")
    current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    current_version = current_app_info.get_system_application_object().get_version()
    validate_equals(current_version, rollback_version, "Installed version must be the rollback (older) version before upgrade")

    # Validate upgrade tarball version differs from installed version

    tarball_version = re.search(r"dell-storage-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Upgrade tarball version must differ from installed version")

    # Transfer upgrade tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer upgrade tarball from local machine to /home/sysadmin")
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"

    FileKeywords(ssh_connection).delete_file("/home/sysadmin/dell-storage*.tgz")
    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball(), temp_remote_path)

    # Move dell-storage*.tgz (rollback version) from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    # Copy upgrade tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to application base path")
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Execute Upload command poitning to the upgrade tarball")

    system_application_update_input.set_app_name(dell_storage_app_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}dell-storage-{tarball_version}*.tgz")
    system_application_update_input.set_timeout_in_seconds(1800)
    SystemApplicationUpdateKeywords(ssh_connection).system_application_update(system_application_update_input)

    get_logger().log_test_case_step("Make sure that the dell-storage application is applied after the upgrade")
    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "applied",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )
    upgraded_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    upgraded_version = upgraded_app_info.get_system_application_object().get_version()
    upgraded_app_status = upgraded_app_info.get_system_application_object().get_status()
    validate_equals(upgraded_app_status, SystemApplicationStatusEnum.APPLIED.value, "dell-storage application should be applied after upgrade")

    get_logger().log_test_case_step("Verify dell-storage app version has changed after upgrade")
    validate_not_equals(current_version, upgraded_version, "Application version should have changed after upgrade")
    validate_equals(upgraded_version, tarball_version, "Application should have been upgraded to the dell_storage_app_tarball version")


@mark.p2
@mark.lab_dell_storage
def test_manual_upgrade_dell_storage_nfs(request: FixtureRequest):
    """
    Upgrade dell-storage application.

    The lab starts with the rollback tarball (dell_storage_app_tarball_rollback) applied and is
    upgraded to the newer version defined by dell_storage_app_tarball.

    Test Steps:
        - Check dell-storage app status.
        - Make sure the rollback (older) version is the applied version before upgrading.
        - Transfer upgrade tarball from local machine to /home/sysadmin
        - Remove tarball from application base path
        - Copy upgrade tarball from /home/sysadmin to application base path
        - Execute the Update Command pointing to the upgraded tarball
        - Verify dell-storage app version has changed after upgrade

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"
    pod_name = "powerstoretest-0"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def teardown():
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        host_lock_keywords.wait_for_host_unlocked("controller-0", unlock_wait_timeout=3200)

        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-nfs-pod.yaml", ignore_not_found=True)

        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")

        # An update/upgrade that is interrupted (e.g. aborted) leaves the app in the
        # transient 'recovering' state, and sysinv rejects abort/remove/apply while
        # recovering. Wait for the app to settle into a terminal state before acting.
        get_logger().log_teardown_step("Wait for dell-storage to leave transient state")
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, ["applied", "apply-failed", "uploaded"], timeout=3600, polling_sleep_time=30)

        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original dell-storage version")

            base_application_path = app_config.get_base_application_path()

            # Capture the upgraded version before wiping the app so its tarball can be cleaned up.
            upgraded_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
            upgraded_version = upgraded_app_info.get_system_application_object().get_version()

            # Wipe dell-storage completely: remove the release (if applied) and delete the
            # app entry. Force both so a failed/transient state can't block the cleanup.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            # 'system application-delete' returns as soon as the CLI is accepted, but
            # sysinv removes the app entry asynchronously, so poll until it is gone
            # instead of checking once (which races the delete and fails spuriously).
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove any leftover tarballs from the application base path so only the
            # tarball we are about to restore (the latest version) remains.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{upgraded_version}.tgz")
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{rollback_version}.tgz")

            # The lab baseline is the latest dell-storage version (dell_storage_app_tarball),
            # not the rollback version used to start the upgrade. Restore the latest tarball
            # that was stashed in /home/sysadmin/test_upgrade during setup so teardown leaves
            # the system on the latest version.

            # Move the latest version tarball from /home/sysadmin/test_upgrade back to base_application_path
            get_logger().log_teardown_step("Move latest tarball from test_upgrade folder to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/test_upgrade/dell-storage-{original_version}.tgz", base_application_path, sudo=True)

            # Upload original version. 'system application-upload' expects a single

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}dell-storage-{original_version}.tgz")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
            system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
            dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply original version
            common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        else:
            # The system is still on the rollback version (e.g. the test failed mid-run before
            # the upgrade completed). The lab baseline is the latest version, so upgrade the
            # system to the latest tarball that was stashed in /home/sysadmin/test_upgrade.
            get_logger().log_teardown_step("System still on rollback version - restoring latest version")

            base_application_path = app_config.get_base_application_path()

            # Wipe dell-storage completely so the latest tarball can be uploaded/applied cleanly.
            get_logger().log_teardown_step("Wipe dell-storage application (remove + delete)")
            SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(dell_storage_app_name, force_removal=True, force_deletion=True, timeout_in_seconds=300)
            validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).is_app_present(dell_storage_app_name),
                False,
                f"{dell_storage_app_name} fully wiped before restore",
                timeout=300,
            )

            # Remove the rollback version tarball from the application base path so only the
            # latest tarball remains.
            FileKeywords(ssh_connection).delete_file(f"{base_application_path}dell-storage-{current_version}.tgz")

            # Restore the latest version tarball that was stashed in /home/sysadmin/test_upgrade.

            get_logger().log_teardown_step("Move latest tarball from test_upgrade folder to base application path")
            FileKeywords(ssh_connection).move_file(f"/home/sysadmin/test_upgrade/dell-storage-{original_version}.tgz", base_application_path, sudo=True)

            refresh_os_tree_keywords(ssh_connection)

            # Upload latest version. 'system application-upload' expects a single concrete file path.

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(dell_storage_app_name)
            system_application_upload_input.set_tar_file_path(f"{base_application_path}dell-storage-{original_version}.tgz")
            SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)

            dell_storage_app_status = validate_equals_with_retry(
                lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
                "uploaded",
                f"{dell_storage_app_name} upload status validation",
                timeout=300,
            )

            # Apply latest version
            common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

        refresh_os_tree_keywords(ssh_connection)

    request.addfinalizer(teardown)

    app_config = ConfigurationManager.get_app_config()

    # The upgrade starts from the rollback (older) tarball and upgrades to dell_storage_app_tarball.
    rollback_tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    rollback_version = re.search(r"dell-storage-(.+)\.tgz", rollback_tarball_filename).group(1)
    tarball_filename = app_config.get_dell_storage_app_tarball().split("/")[-1]

    get_logger().log_test_case_step(f"Check {dell_storage_app_name} app status.")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)

    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(ssh_connection).remount_read_write("/usr")
    MountKeywords(ssh_connection).remount_read_write("/home/sysadmin/")

    # Record the dell-storage version installed before testing (the lab baseline / latest version).
    get_logger().log_test_case_step("Record original dell-storage app version before testing")
    original_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    original_version = original_app_info.get_system_application_object().get_version()
    get_logger().log_info(f"Original {dell_storage_app_name} version before testing: {original_version}")

    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    rollback_tarball_filename = app_config.get_dell_storage_app_tarball_rollback().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{rollback_tarball_filename}"
    # The move_file above relocates the base-path tarball into /home/sysadmin as root, so a
    # same-named file is now root-owned there. The non-sudo SFTP upload cannot overwrite a
    # root-owned file (Errno 13 Permission denied), so remove any stale copy (with sudo) first.

    FileKeywords(ssh_connection).create_directory("/home/sysadmin/test_upgrade")
    FileKeywords(ssh_connection).move_file("/home/sysadmin/dell-storage*.tgz", "/home/sysadmin/test_upgrade/", sudo=True)

    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball_rollback(), temp_remote_path)
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(dell_storage_app_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{rollback_tarball_filename}")
    system_application_update_input.set_timeout_in_seconds(1800)
    SystemApplicationUpdateKeywords(ssh_connection).system_application_update(system_application_update_input)

    # Record current version before upgrade. This is expected to be the rollback (older) version.
    get_logger().log_test_case_step("Record current dell-storage app version")
    current_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    current_version = current_app_info.get_system_application_object().get_version()
    validate_equals(current_version, rollback_version, "Installed version must be the rollback (older) version before upgrade")

    # Validate upgrade tarball version differs from installed version

    tarball_version = re.search(r"dell-storage-(.+)\.tgz", tarball_filename).group(1)
    validate_not_equals(current_version, tarball_version, "Upgrade tarball version must differ from installed version")

    # Transfer upgrade tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer upgrade tarball from local machine to /home/sysadmin")
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"

    FileKeywords(ssh_connection).delete_file("/home/sysadmin/dell-storage*.tgz")
    FileKeywords(ssh_connection).upload_file(app_config.get_dell_storage_app_tarball(), temp_remote_path)

    # Move dell-storage*.tgz (rollback version) from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(ssh_connection).move_file(f"{app_config.get_base_application_path()}dell-storage*.tgz", "/home/sysadmin/", sudo=True)

    # Copy upgrade tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to application base path")
    FileKeywords(ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Execute Upload command poitning to the upgrade tarball")

    system_application_update_input.set_app_name(dell_storage_app_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}dell-storage-{tarball_version}*.tgz")
    system_application_update_input.set_timeout_in_seconds(1800)
    SystemApplicationUpdateKeywords(ssh_connection).system_application_update(system_application_update_input)

    get_logger().log_test_case_step("Make sure that the dell-storage application is applied after the upgrade")
    validate_equals_with_retry(
        lambda: SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(dell_storage_app_name).get_status(),
        "applied",
        f"{dell_storage_app_name} applied status validation",
        timeout=300,
    )
    upgraded_app_info = SystemApplicationShowKeywords(ssh_connection).get_system_application_show(dell_storage_app_name)
    upgraded_version = upgraded_app_info.get_system_application_object().get_version()
    upgraded_app_status = upgraded_app_info.get_system_application_object().get_status()
    validate_equals(upgraded_app_status, SystemApplicationStatusEnum.APPLIED.value, "dell-storage application should be applied after upgrade")

    get_logger().log_test_case_step("Verify dell-storage app version has changed after upgrade")
    validate_not_equals(current_version, upgraded_version, "Application version should have changed after upgrade")
    validate_equals(upgraded_version, tarball_version, "Application should have been upgraded to the dell_storage_app_tarball version")


@mark.p2
@mark.lab_dell_storage
@mark.lab_is_simplex
def test_dell_storage_iscsi_lifecycle_coexistence_ceph_sx(request: FixtureRequest):
    """
    Test Dell Storage coexistence with Ceph backend

    The lab should have dell-storage app installed with the dell storageClass and the ceph backend also installed.


    Test Steps:
        - Check dell-storage app status.
        - Make sure that dell-storage is applied (ISCSI)
        - Make sure that ceph backend is configured
        - Create and apply PVC/Pod using RBD storageClass
        - Write a test file on this RBD pod
        - Create and apply PVC/Pod using CEPH storageClass
        - Write a test file on this CEPH pod
        - Create and apply PVC/Pod using dell-storage storageClass
        - Write a test file on this dell-storage pod
        - Verify data integrity


    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    TEST_FILES_DIR = "resources/cloud_platform/storage/volume_snapshot"
    REMOTE_HOME = "/home/sysadmin"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def upload_yaml_files(ssh_connection: SSHConnection, file_names: list[str]) -> None:
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

    def cleanup_test_resources(
        ssh_connection: SSHConnection,
        pod_names: list[str],
        pvc_names: list[str],
        yaml_file_names: list[str],
    ) -> None:
        """Clean up all resources created during a volume snapshot test.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
            pod_names (list[str]): Pod names to delete.
            pvc_names (list[str]): PVC names to delete.
            yaml_file_names (list[str]): YAML file names to remove from the controller.
        """
        delete_resource_keywords = KubectlDeleteResourceKeywords(ssh_connection)

        for pod_name in pod_names:
            KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod_name)

        for pvc_name in pvc_names:
            delete_resource_keywords.delete_resource("pvc", pvc_name)
            KubectlGetPvcKeywords(ssh_connection).wait_for_pvc_to_be_deleted(pvc_name)

        file_keywords = FileKeywords(ssh_connection)
        for file_name in yaml_file_names:
            file_keywords.delete_file(f"{REMOTE_HOME}/{file_name}")

    def teardown():
        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-pod.yaml", ignore_not_found=True)
        cleanup_test_resources(
            ssh_connection,
            pod_names=["csi-cephfs-demo-pod", "csi-rbd-demo-pod"],
            pvc_names=["cephfs-pvc", "rbd-pvc"],
            yaml_file_names=[],
        )

    get_logger().log_test_case_step(f"Make sure that {dell_storage_app_name} is applied (ISCSI) ")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_iscsi_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)
    request.addfinalizer(common_dell_storage_teardown)
    request.addfinalizer(teardown)

    test_pod_yaml = "dell-storage-test-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Make sure that ceph backend is configured")
    ensure_ceph_storage_backend_configured(ssh_connection)

    get_logger().log_test_case_step("Create and apply PVC/Pod using CEPH storageClass")
    storage_type = "cephfs"
    pvc_name = f"{storage_type}-pvc"
    pod_name = f"csi-{storage_type}-demo-pod"

    yaml_files = [f"{storage_type}-pvc.yaml", f"{storage_type}-pod.yaml"]

    # Setup: clean up any leftover resources from previous runs
    get_logger().log_setup_step("Delete test pods, PVCs, and snapshots if they exist before test run")
    cleanup_test_resources(
        ssh_connection,
        pod_names=[pod_name],
        pvc_names=[pvc_name],
        yaml_file_names=[],
    )

    get_logger().log_test_case_step("Upload CephFS test YAML files to active controller")
    upload_yaml_files(ssh_connection, yaml_files)
    pvc_yaml = f"{REMOTE_HOME}/{storage_type}-pvc.yaml"
    pod_yaml = f"{REMOTE_HOME}/{storage_type}-pod.yaml"

    get_logger().log_test_case_step(f"Create a {storage_type} PVC and make sure it is in Bound status")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pvc_yaml)
    KubectlGetPvcKeywords(ssh_connection).wait_for_pvcs_to_reach_status(expected_status="Bound", pvc_names=pvc_name)

    get_logger().log_test_case_step(f"Create a {storage_type} pod")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pod_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running")

    get_logger().log_test_case_step("Write a test file on Pod")
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(pod_name, "bash -c 'touch /data/test.txt'", options="-i")

    storage_type = "rbd"
    pvc_name = f"{storage_type}-pvc"
    pod_name = f"csi-{storage_type}-demo-pod"

    yaml_files = [f"{storage_type}-pvc.yaml", f"{storage_type}-pod.yaml"]

    get_logger().log_setup_step("Delete test pods, PVCs, and snapshots if they exist before test run")
    cleanup_test_resources(
        ssh_connection,
        pod_names=[pod_name],
        pvc_names=[pvc_name],
        yaml_file_names=[],
    )

    get_logger().log_test_case_step("Upload RBD test YAML files to active controller")
    upload_yaml_files(ssh_connection, yaml_files)
    pvc_yaml = f"{REMOTE_HOME}/{storage_type}-pvc.yaml"
    pod_yaml = f"{REMOTE_HOME}/{storage_type}-pod.yaml"

    get_logger().log_test_case_step(f"Create a {storage_type} PVC and make sure it is in Bound status")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pvc_yaml)
    KubectlGetPvcKeywords(ssh_connection).wait_for_pvcs_to_reach_status(expected_status="Bound", pvc_names=pvc_name)

    get_logger().log_test_case_step(f"Create a {storage_type} pod")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pod_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running")

    get_logger().log_test_case_step("Write a test file on Pod")
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(pod_name, "bash -c 'touch /data/test.txt'", options="-i")

    get_logger().log_test_case_step("Create and apply PVC/Pod using dell-storage storageClass")
    yaml_path = "/home/sysadmin/dell-storage-test-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Verify data integrity")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd("csi-cephfs-demo-pod", "bash -c 'test -f /data/test.txt'", options="-i")
    validate_equals(ssh_connection.get_return_code(), 0, "test.txt exists on csi-cephfs-demo-pod")

    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd("csi-rbd-demo-pod", "bash -c 'test -f /data/test.txt'", options="-i")
    validate_equals(ssh_connection.get_return_code(), 0, "test.txt exists on csi-rbd-demo-pod")

@mark.p2
@mark.lab_dell_storage
@mark.lab_is_simplex
def test_dell_storage_nfs_lifecycle_coexistence_ceph_sx(request: FixtureRequest):
    """
    Test Dell Storage coexistence with Ceph backend

    The lab should have dell-storage app installed with the dell storageClass and the ceph backend also installed.


    Test Steps:
        - Check dell-storage app status.
        - Make sure that dell-storage is applied (NFS)
        - Make sure that ceph backend is configured
        - Create and apply PVC/Pod using RBD storageClass
        - Write a test file on this RBD pod
        - Create and apply PVC/Pod using CEPH storageClass
        - Write a test file on this CEPH pod
        - Create and apply PVC/Pod using dell-storage storageClass
        - Write a test file on this dell-storage pod
        - Verify data integrity


    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """

    TEST_FILES_DIR = "resources/cloud_platform/storage/volume_snapshot"
    REMOTE_HOME = "/home/sysadmin"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "dell-storage"
    dell_storage_app_name = "dell-storage"
    chart_name = "csi-powerstore"

    def verify_dell_storage_pods_are_running(ssh_connection):
        pod_prefix = "csi-powerstore"
        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_names = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_prefix)
        pod_status = get_pod_obj.wait_for_pod_status(pod_names, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_prefix} pods are running")

        get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
        pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, f"Verify {pod_name} pod is running")

    def upload_yaml_files(ssh_connection: SSHConnection, file_names: list[str]) -> None:
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

    def cleanup_test_resources(
        ssh_connection: SSHConnection,
        pod_names: list[str],
        pvc_names: list[str],
        yaml_file_names: list[str],
    ) -> None:
        """Clean up all resources created during a volume snapshot test.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
            pod_names (list[str]): Pod names to delete.
            pvc_names (list[str]): PVC names to delete.
            yaml_file_names (list[str]): YAML file names to remove from the controller.
        """
        delete_resource_keywords = KubectlDeleteResourceKeywords(ssh_connection)

        for pod_name in pod_names:
            KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(pod_name)

        for pvc_name in pvc_names:
            delete_resource_keywords.delete_resource("pvc", pvc_name)
            KubectlGetPvcKeywords(ssh_connection).wait_for_pvc_to_be_deleted(pvc_name)

        file_keywords = FileKeywords(ssh_connection)
        for file_name in yaml_file_names:
            file_keywords.delete_file(f"{REMOTE_HOME}/{file_name}")

    def teardown():
        get_logger().log_teardown_step("Clean up the test pod resources.")
        KubectlFileDeleteKeywords(ssh_connection).delete_resources("/home/sysadmin/dell-storage-test-nfs-pod.yaml", ignore_not_found=True)
        cleanup_test_resources(
            ssh_connection,
            pod_names=["csi-cephfs-demo-pod", "csi-rbd-demo-pod"],
            pvc_names=["cephfs-pvc", "rbd-pvc"],
            yaml_file_names=[],
        )

    get_logger().log_test_case_step(f"Make sure that {dell_storage_app_name} is applied (NFS) ")
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    dell_storage_app_status = system_applications.get_application(dell_storage_app_name).get_status()
    get_logger().log_info(f"{dell_storage_app_name} application is: {dell_storage_app_status}")

    common_verify_dell_app_status_nfs_sx(ssh_connection, dell_storage_app_status, namespace, dell_storage_app_name, chart_name)
    request.addfinalizer(common_dell_storage_teardown)
    request.addfinalizer(teardown)

    test_pod_yaml = "dell-storage-test-nfs-pod.yaml"
    dell_storage_files = [test_pod_yaml]
    for file_name in dell_storage_files:
        local_path = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{file_name}")
        remote_yaml_path = f"/home/sysadmin/{file_name}"
        FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)

    get_logger().log_test_case_step("Make sure that ceph backend is configured")
    ensure_ceph_storage_backend_configured(ssh_connection)

    get_logger().log_test_case_step("Create and apply PVC/Pod using CEPH storageClass")
    storage_type = "cephfs"
    pvc_name = f"{storage_type}-pvc"
    pod_name = f"csi-{storage_type}-demo-pod"

    yaml_files = [f"{storage_type}-pvc.yaml", f"{storage_type}-pod.yaml"]

    # Setup: clean up any leftover resources from previous runs
    get_logger().log_setup_step("Delete test pods, PVCs, and snapshots if they exist before test run")
    cleanup_test_resources(
        ssh_connection,
        pod_names=[pod_name],
        pvc_names=[pvc_name],
        yaml_file_names=[],
    )

    get_logger().log_test_case_step("Upload CephFS test YAML files to active controller")
    upload_yaml_files(ssh_connection, yaml_files)
    pvc_yaml = f"{REMOTE_HOME}/{storage_type}-pvc.yaml"
    pod_yaml = f"{REMOTE_HOME}/{storage_type}-pod.yaml"

    get_logger().log_test_case_step(f"Create a {storage_type} PVC and make sure it is in Bound status")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pvc_yaml)
    KubectlGetPvcKeywords(ssh_connection).wait_for_pvcs_to_reach_status(expected_status="Bound", pvc_names=pvc_name)

    get_logger().log_test_case_step(f"Create a {storage_type} pod")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pod_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running")

    get_logger().log_test_case_step("Write a test file on Pod")
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(pod_name, "bash -c 'touch /data/test.txt'", options="-i")

    storage_type = "rbd"
    pvc_name = f"{storage_type}-pvc"
    pod_name = f"csi-{storage_type}-demo-pod"

    yaml_files = [f"{storage_type}-pvc.yaml", f"{storage_type}-pod.yaml"]

    get_logger().log_setup_step("Delete test pods, PVCs, and snapshots if they exist before test run")
    cleanup_test_resources(
        ssh_connection,
        pod_names=[pod_name],
        pvc_names=[pvc_name],
        yaml_file_names=[],
    )

    get_logger().log_test_case_step("Upload RBD test YAML files to active controller")
    upload_yaml_files(ssh_connection, yaml_files)
    pvc_yaml = f"{REMOTE_HOME}/{storage_type}-pvc.yaml"
    pod_yaml = f"{REMOTE_HOME}/{storage_type}-pod.yaml"

    get_logger().log_test_case_step(f"Create a {storage_type} PVC and make sure it is in Bound status")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pvc_yaml)
    KubectlGetPvcKeywords(ssh_connection).wait_for_pvcs_to_reach_status(expected_status="Bound", pvc_names=pvc_name)

    get_logger().log_test_case_step(f"Create a {storage_type} pod")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(pod_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running")

    get_logger().log_test_case_step("Write a test file on Pod")
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(pod_name, "bash -c 'touch /data/test.txt'", options="-i")

    get_logger().log_test_case_step("Create and apply PVC/Pod using dell-storage storageClass")
    yaml_path = "/home/sysadmin/dell-storage-test-nfs-pod.yaml"
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml(yaml_path)

    pod_name = "powerstoretest-0"
    get_logger().log_test_case_step(f"Check if test {pod_name} pod is running")
    verify_dell_storage_pods_are_running(ssh_connection)

    get_logger().log_test_case_step(f"Creating text.txt file inside of {pod_name} pod")
    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_test_case_step("Verify data integrity")
    verify_file_created_on_pod_exists(ssh_connection, namespace, pod_name)
    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd("csi-cephfs-demo-pod", "bash -c 'test -f /data/test.txt'", options="-i")
    validate_equals(ssh_connection.get_return_code(), 0, "test.txt exists on csi-cephfs-demo-pod")

    KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd("csi-rbd-demo-pod", "bash -c 'test -f /data/test.txt'", options="-i")
    validate_equals(ssh_connection.get_return_code(), 0, "test.txt exists on csi-rbd-demo-pod")