from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_create_pods_keywords import KubectlCreatePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.volumesnapshots.kubectl_get_volumesnapshots_keywords import KubectlGetVolumesnapshotsKeywords


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
        rest_credentials = ConfigurationManager.get_lab_config().get_rest_credentials()
        username = rest_credentials.get_user_name()
        password = rest_credentials.get_password()
        template_file = get_stx_resource_path(f"resources/cloud_platform/storage/dell_storage/{yaml_file}")
        replacement_dictionary = {"username": username, "password": password}
        remote_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, yaml_file, "/home/sysadmin")
        SystemHelmOverrideKeywords(ssh_connection).update_helm_override(remote_yaml, dell_storage_app_name, chart_name, namespace)

        get_logger().log_test_case_step(f"Apply {dell_storage_app_name}.")
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply(dell_storage_app_name)

    app_status_list = ["applied"]
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(dell_storage_app_name, app_status_list, timeout=360, polling_sleep_time=10)
    get_logger().log_info(f"{dell_storage_app_name} application is: applied")


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
        get_logger().log_info(f"Check if test snapshot pod {snapshot_pod_name} is running")
        snapshot_pod_status = KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(snapshot_pod_name, "Running", namespace)
        if snapshot_pod_status is True:
            get_logger().log_teardown_step(f"Clean up the snapshot pod {snapshot_pod_name}.")
            kubectl_delete_keywords.delete_resources(f"/home/sysadmin/{snapshot_pod_yaml}")

        snapshot_name = "csi-powerstore-pvc-snapshot"
        get_logger().log_info(f"Check whether {snapshot_name} is ready to use")
        snapshot_status = KubectlGetVolumesnapshotsKeywords(ssh_connection).wait_for_volumesnapshot_status(snapshot_name, "true", namespace)
        if snapshot_status is True:
            get_logger().log_teardown_step(f"Clean up the snapshot {snapshot_name}.")
            kubectl_delete_keywords.delete_resources(f"/home/sysadmin/{snapshot_yaml}")

        test_pod_name = "powerstoretest-0"
        get_logger().log_info(f"Check if test {test_pod_name} pod is running")
        pod_status = KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(test_pod_name, "Running", namespace)
        if pod_status is True:
            get_logger().log_teardown_step(f"Clean up the test pod {test_pod_name}.")
            kubectl_delete_keywords.delete_resources(f"/home/sysadmin/{test_pod_yaml}")

        get_logger().log_teardown_step("Remove test yaml files")
        for file_name in dell_storage_files:
            FileKeywords(ssh_connection).delete_file(f"/home/sysadmin/{file_name}")

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
def test_remove_dell_storage_app():
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


@mark.p2
@mark.lab_dell_storage
def test_delete_dell_storage_app():
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
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name=dell_storage_app_name)
