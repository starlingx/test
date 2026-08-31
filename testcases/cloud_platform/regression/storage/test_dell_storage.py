from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_abort_keywords import SystemApplicationAbortKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_create_pods_keywords import KubectlCreatePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.volumesnapshots.kubectl_get_volumesnapshots_keywords import KubectlGetVolumesnapshotsKeywords
from keywords.linux.ip.ip_keywords import IPKeywords


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
    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt is exist")
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
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
    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Access to {pod_name} pod success")

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

    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"test.txt is on {pod_name} pod.")


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
    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Access to {pod_name} pod success")

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

    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"test.txt is on {pod_name} pod.")


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
    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
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

    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"test.txt is on {pod_name} pod.")


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
    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'touch /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"Write to {pod_name} pod success")

    get_logger().log_info("sync pod")
    cmd = "bash -c 'sync'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"sync pod {pod_name} success")

    get_logger().log_info("Check if test.txt exists")
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
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

    kubectl_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    options = f"-it -n {namespace}"
    cmd = "bash -c 'test -f /data0/test.txt'"
    kubectl_exec_in_pods.run_pod_exec_cmd(pod_name, cmd, options=options)
    validate_equals(ssh_connection.get_return_code(), 0, f"test.txt is on {pod_name} pod.")
