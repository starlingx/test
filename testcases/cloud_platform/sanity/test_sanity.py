import time
from typing import Any

from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.node import Node
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.secure_transfer_file.secure_transfer_file import SecureTransferFile
from framework.ssh.secure_transfer_file.secure_transfer_file_enum import TransferDirection
from framework.ssh.secure_transfer_file.secure_transfer_file_input_object import SecureTransferFileInputObject
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from framework.web.webdriver_core import WebDriverCore
from keywords.cloud_platform.dcmanager.dcmanager_alarm_summary_keywords import DcManagerAlarmSummaryKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object_filter import DcManagerSubcloudListObjectFilter
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.fm_client_cli_keywords import FaultManagementClientCLIKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.object.fm_client_cli_object import FaultManagementClientCLIObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.modify.system_modify_keywords import SystemModifyKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.deployments.kubectl_delete_deployments_keywords import KubectlDeleteDeploymentsKeywords
from keywords.k8s.deployments.kubectl_expose_deployment_keywords import KubectlExposeDeploymentKeywords
from keywords.k8s.pods.kubectl_create_pods_keywords import KubectlCreatePodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.object.kubectl_get_pods_output import KubectlGetPodsOutput
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.service.kubectl_delete_service_keywords import KubectlDeleteServiceKeywords
from keywords.k8s.service.kubectl_get_service_keywords import KubectlGetServiceKeywords
from keywords.linux.date.date_keywords import DateKeywords
from keywords.linux.tar.tar_keywords import TarKeywords
from web_pages.horizon.admin.platform.horizon_host_inventory_page import HorizonHostInventoryPage
from web_pages.horizon.login.horizon_login_page import HorizonLoginPage


@mark.p0
def test_check_alarms():
    """
    Testcase to verify there are no alarms on the system
    Test Steps:
        - connect to active controller
        - run command fm alarm-list
        - verify that no alarms exist

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    alarms = AlarmListKeywords(ssh_connection).alarm_list()
    assert not alarms, "There were alarms found on the system"


@mark.p0
def test_check_all_pods_healthy():
    """
    Testcase to verify that all pods are healthy
    Test Steps:
        - connect to active controller
        - run kubectl -o wide get pods --all-namespaces
        - validate that all pods are in 'Running, 'Succeeded' or 'Completed' state

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    healthy_status = ["Running", "Succeeded", "Completed"]
    is_healthy = KubectlGetPodsKeywords(ssh_connection).wait_for_all_pods_status(healthy_status, timeout=300)
    assert is_healthy


@mark.p0
def test_platform_integ_apps_applied():
    """
    Test to validate platform integ apps have been applied

    Test Steps:
        - connect to active controller
        - run system cmd - system application-list
        - validate that platform integ apps are in applied state

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    platform_integ_apps_status = system_applications.get_application("platform-integ-apps").get_status()
    assert platform_integ_apps_status == "applied", f"platform-integ-apps was not applied. Status was {platform_integ_apps_status}"


@mark.p0
def test_cert_manager_applied():
    """
    Test to validate cert manager app has been applied

    Test Steps:
        - connect to active controller
        - run system cmd - system application-list
        - validate that cert manager is in applied state

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    application_status = system_applications.get_application("cert-manager").get_status()
    assert application_status == "applied", f"cert-manager was not applied. Status was {application_status}"


@mark.p0
def test_nginx_ingress_controller_applied():
    """
    Test to validate nginx ingress controller has been applied

    Test Steps:
        - connect to active controller
        - run system cmd - system application-list
        - validate that nginx ingress controller is in applied state

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_applications = SystemApplicationListKeywords(ssh_connection)
    system_applications.validate_app_status("nginx-ingress-controller", "applied")


@mark.p0
@mark.lab_is_simplex
def test_lock_unlock_simplex():
    """
    Test case to validate a simplex can be locked and unlocked successfully

    Test Steps:
        - connect to simplex controller
        - run 'system host-lock' and wait for lock to complete
        - run 'system host-unlock' and wait for unlock to complete successfully

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host("controller-0")
    assert lock_success, "Controller was not locked successfully."
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host("controller-0")
    assert unlock_success, "Controller was not unlocked successfully."


@mark.p0
@mark.lab_has_standby_controller
def test_lock_unlock_standby_controller():
    """
    Test case that lock/unlocks a standby controller

    Test Steps:
        - connect to active controller ssh
        - get the standby controller name
        - run 'system host-lock <standby-controller>' and wait for lock to complete
        - run 'system host-unlock <standby-controller>' and wait for unlock to complete

    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    standby_controller = SystemHostListKeywords(ssh_connection).get_standby_controller()
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(standby_controller.get_host_name())
    assert lock_success, "Controller was not locked successfully."
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(standby_controller.get_host_name())
    assert unlock_success, "Controller was not unlocked successfully."


@mark.p0
@mark.lab_has_worker
def test_lock_unlock_compute():
    """
    Test case that lock/unlocks a compute

    Test Steps:
        - connect to active controller ssh
        - get the compute name
        - run 'system host-lock <compute>' and wait for lock to complete
        - run 'system host-unlock <compute>' and wait for unlock to complete

    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    computes = SystemHostListKeywords(ssh_connection).get_computes()

    assert len(computes) > 0, "No computes were found"

    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(computes[0].get_host_name())
    assert lock_success, "Compute was not locked successfully."
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(computes[0].get_host_name())
    assert unlock_success, "Compute was not unlocked successfully."


@mark.p0
@mark.lab_has_standby_controller
def test_swact():
    """
    Test to validate swact action

    Test Steps:
        - connect to active controller ssh
        - run 'system host-swact <controller-name>'
        - validate that swact complete successfully and that active controller is now standby and standby is now active

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    swact_success = SystemHostSwactKeywords(ssh_connection).host_swact()
    assert swact_success, "Swact was not completed successfully"


@mark.p0
@mark.lab_has_standby_controller
def test_reboot():
    """
    Test for reboot of host from system command

    Test Steps:
        - get active controller ssh
        - get name of standby controller
        - lock standby controller
        - run 'system host-reboot <standby-controller>
        - validate reboot comes back successfully
        - unlock standby controller
        - validate unlock is successful
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    standby_controller = SystemHostListKeywords(ssh_connection).get_standby_controller()
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(standby_controller.get_host_name())
    assert lock_success, "Controller was not locked successfully."
    reboot_success = SystemHostRebootKeywords(ssh_connection).host_reboot(standby_controller.get_host_name())
    assert reboot_success, "Controller was not rebooted successfully."
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(standby_controller.get_host_name())
    assert unlock_success, "Controller was not unlocked successfully."


@mark.p1
def test_horizon_host_inventory_display_active_controller(request):
    """
    This test case validates that we can see the correct information regarding the active controller
    in the Horizon Host Inventory page.

    Test Steps:
        - Login to Horizon
        - Navigate to the Admin -> Platform -> Host Inventory page
        - Validate that the Controller Hosts table has the correct headers.
        - Validate that the active controller is in the Controller Hosts table.
        - Validate that each column entry for the active controller is as expected. This is done
          by comparing the values with the output of the 'system host-list' command line.
    """

    driver = WebDriverCore()
    request.addfinalizer(lambda: driver.close())

    login_page = HorizonLoginPage(driver)
    login_page.navigate_to_login_page()
    login_page.login_as_admin()

    host_inventory = HorizonHostInventoryPage(driver)
    host_inventory.navigate_to_host_inventory_page()

    # Validate the Headers of the Controller Table
    all_controller_headers = host_inventory.get_controller_hosts_table_headers()
    validate_equals(len(all_controller_headers), 8, "There should be exactly 8 table headers")
    assert all_controller_headers[0], "Host Name header is missing."
    assert all_controller_headers[1], "Personality header is missing."
    assert all_controller_headers[2], "Admin State header is missing."
    assert all_controller_headers[3], "Operational State header is missing."
    assert all_controller_headers[4], "Availability State header is missing."
    assert all_controller_headers[5], "Uptime header is missing."
    assert all_controller_headers[6], "Status header is missing."
    assert all_controller_headers[7], "Actions header is missing."
    get_logger().log_info("Validated the headers of the Controllers Table.")

    # Get the active Controller information from the command line.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    active_controller_output = system_host_list_keywords.get_active_controller()
    active_host_name = active_controller_output.get_host_name()

    # Compare the values in the active controller in the Host Inventory table with the output of system host-list.
    horizon_host_information = host_inventory.get_controller_host_information(active_host_name)
    validate_equals(horizon_host_information.get_host_name().lower(), active_controller_output.get_host_name().lower(), "Host Name of active controller")
    validate_equals(horizon_host_information.get_personality(), "Controller-Active", "Personality of active controller")
    validate_equals(horizon_host_information.get_admin_state().lower(), active_controller_output.get_administrative().lower(), "Admin State of active controller")
    validate_equals(horizon_host_information.get_operational_state().lower(), active_controller_output.get_operational().lower(), "Operational State of active controller")
    validate_equals(horizon_host_information.get_availability_state().lower(), active_controller_output.get_availability().lower(), "Availability State of active controller")

    assert "minute" in horizon_host_information.get_uptime() or "hour" in horizon_host_information.get_uptime() or "day" in horizon_host_information.get_uptime() or "week" in horizon_host_information.get_uptime(), f"Uptime doesn't follow the expected format '* weeks, * days, * hours, * minutes'. Observed: {horizon_host_information.get_uptime()}"

    validate_equals(horizon_host_information.get_status(), None, "Status Column of active controller")
    validate_equals(host_inventory.get_controller_edit_host_button_text(active_host_name), "Edit Host", "Label of Edit Host button")
    get_logger().log_info("Validated the the table entries for the Active Controller")


def deploy_pods(request: Any, ssh_connection: SSHConnection) -> KubectlGetPodsOutput:
    """
    Deploys pods needed by some suites in this suite

    Args:
        request (Any): request needed for adding teardown
        ssh_connection (SSHConnection): the ssh connection

    Returns:
        KubectlGetPodsOutput: the pods output

    """
    file_keywords = FileKeywords(ssh_connection)

    # Cleanup any old pods
    KubectlDeleteDeploymentsKeywords(ssh_connection).cleanup_deployment("server-pod-dep")
    KubectlDeletePodsKeywords(ssh_connection).cleanup_pod("client-pod1")
    KubectlDeletePodsKeywords(ssh_connection).cleanup_pod("client-pod2")

    file_keywords.upload_file(get_stx_resource_path("resources/cloud_platform/sanity/pods/client-pod1.yaml"), "/home/sysadmin/client-pod1.yaml")
    file_keywords.upload_file(get_stx_resource_path("resources/cloud_platform/sanity/pods/client-pod2.yaml"), "/home/sysadmin/client-pod2.yaml")
    file_keywords.upload_file(get_stx_resource_path("resources/cloud_platform/sanity/pods/server_pod.yaml"), "/home/sysadmin/server_pod.yaml")
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml("/home/sysadmin/server_pod.yaml")
    kubectl_create_pods_keyword.create_from_yaml("/home/sysadmin/client-pod1.yaml")
    kubectl_create_pods_keyword.create_from_yaml("/home/sysadmin/client-pod2.yaml")

    # Create teardown to remove pods
    def remove_deployments_and_pods() -> KubectlGetPodsOutput:
        """
        Finalizer to remove deployments and pods

        Returns:
            KubectlGetPodsOutput: the pods output
        """

        rc = KubectlDeleteDeploymentsKeywords(ssh_connection).cleanup_deployment("server-pod-dep")
        rc += KubectlDeletePodsKeywords(ssh_connection).cleanup_pod("client-pod1")
        rc += KubectlDeletePodsKeywords(ssh_connection).cleanup_pod("client-pod2")

        assert rc == 0

    request.addfinalizer(remove_deployments_and_pods)
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()

    # get the server pod names
    server_pods = pods.get_pods_start_with("server-pod-dep")
    assert len(server_pods) == 2, "Incorrect number of server pods were created"
    server_pod1_name = server_pods[0].get_name()
    server_pod2_name = server_pods[1].get_name()

    # wait for all pods to be running
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    client_pod1_running = kubectl_get_pods_keywords.wait_for_pod_status("client-pod1", "Running")
    assert client_pod1_running, "Client pod1 did not reach running status in expected time"
    client_pod2_running = kubectl_get_pods_keywords.wait_for_pod_status("client-pod2", "Running")
    assert client_pod2_running, "Client pod2 did not reach running status in expected time"
    server_pod1_running = kubectl_get_pods_keywords.wait_for_pod_status(server_pod1_name, "Running")
    assert server_pod1_running, "Server pod1 did not reach running status in expected time"
    server_pod2_running = kubectl_get_pods_keywords.wait_for_pod_status(server_pod2_name, "Running")
    assert server_pod2_running, "Server pod2 did not reach running status in expected time"

    # return the pods with the latest status
    return kubectl_get_pods_keywords.get_pods()


@mark.p0
def test_dc_alarm_aggregation_managed():
    """
    Test Alarm Aggregation on Distributed Cloud

    Setups:
        - Make sure there is consistency between alarm summary on
        Central Cloud and on subclouds.

    Test Steps (for each subcloud in the central cloud):
        - Ensure an alarm with the sama alarm id does not exist in the subcloud.
        - Get the numbers of summarized alarms for a subcloud in the central cloud.
        - Raise an alarm at subcloud;
        - Ensure relative alarm raised on subcloud
        - Ensure system alarm-summary on subcloud matches dcmanager alarm summary on system
        - Clean alarm at subcloud
        - Ensure relative alarm cleared on subcloud
        - Ensure system alarm-summary on subcloud matches dcmanager alarm summary on system
    """
    subclouds_names = ConfigurationManager.get_lab_config().get_subcloud_names()

    for subcloud_name in subclouds_names:
        ssh_subcloud_connection = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        fm_client_cli_keywords = FaultManagementClientCLIKeywords(ssh_subcloud_connection)

        # Gets the list of alarms in the subcloud. Maybe some alarms are present in the subcloud.
        alarm_list_keywords = AlarmListKeywords(ssh_subcloud_connection)
        subcloud_alarms = alarm_list_keywords.alarm_list()

        # Asserts that an alarm with the same 'Alarm ID' used in this test case is not present in the subcloud.
        subcloud_alarm = next((alarm for alarm in subcloud_alarms if alarm.alarm_id == FaultManagementClientCLIObject.DEFAULT_ALARM_ID), None)
        assert subcloud_alarm is None

        # Gets the summarized list of alarms in the dc cloud. Maybe there is some alarm for the subclouds there.
        dc_manager_alarm_summary_keywords = DcManagerAlarmSummaryKeywords(LabConnectionKeywords().get_active_controller_ssh())
        alarm_summary_list = dc_manager_alarm_summary_keywords.get_alarm_summary_list()
        alarm_summary = next((alarm for alarm in alarm_summary_list if alarm.subcloud_name == subcloud_name), None)
        num_previous_alarm = alarm_summary.get_major_alarms()

        # Raises the alarm on subcloud.
        fm_client_cli_object = FaultManagementClientCLIObject()
        fm_client_cli_object.set_entity_id(f"name={subcloud_name}")
        get_logger().log_info(f"Raise alarm on subcloud: {subcloud_name}")
        fm_client_cli_keywords.raise_alarm(fm_client_cli_object)

        # Asserts that the alarm present in the subcloud is the same as the one generated above.
        subcloud_alarms = alarm_list_keywords.alarm_list()
        subcloud_alarm = next((alarm for alarm in subcloud_alarms if alarm.alarm_id == fm_client_cli_object.get_alarm_id()), None)
        assert subcloud_alarm is not None
        assert subcloud_alarm.get_entity_id() == f"name={subcloud_name}"

        # Asserts that the alarm generated above was summarized in the dc cloud ('dcmanager alarm summary' command).
        # The alarm takes some time to be summarized. Experimentally, 60 seconds is considered a maximum safe period for
        # the alarm to be summarized.
        check_interval = 3
        timeout_seconds = 60
        end_time = time.time() + timeout_seconds
        while time.time() < end_time:
            alarm_summary_list = dc_manager_alarm_summary_keywords.get_alarm_summary_list()
            alarm_summary = next((alarm for alarm in alarm_summary_list if alarm.subcloud_name == subcloud_name), None)
            if alarm_summary is not None and alarm_summary.get_major_alarms() - num_previous_alarm == 1:
                break
            time.sleep(check_interval)
        assert alarm_summary is not None
        assert alarm_summary.get_major_alarms() - num_previous_alarm == 1

        # Delete the alarm from the subcloud.
        get_logger().log_info(f"Delete the alarm from subcloud: {subcloud_name}")
        fm_client_cli_keywords.delete_alarm(fm_client_cli_object)

        # Asserts the alarm is not present in the subcloud anymore.
        subcloud_alarms = alarm_list_keywords.alarm_list()
        subcloud_alarm = next((alarm for alarm in subcloud_alarms if alarm.alarm_id == fm_client_cli_object.get_alarm_id()), None)
        assert subcloud_alarm is None

        # Asserts that the alarm generated above is not summarized in the dc cloud ('dcmanager alarm summary' command).
        # The summarized alarms list takes some time to be updated. Experimentally, 60 seconds is considered a maximum
        # safe period for that list to be updated.
        end_time = time.time() + timeout_seconds
        while time.time() < end_time:
            alarm_summary_list = dc_manager_alarm_summary_keywords.get_alarm_summary_list()
            alarm_summary = next((alarm for alarm in alarm_summary_list if alarm.subcloud_name == subcloud_name), None)
            if alarm_summary is not None and alarm_summary.get_major_alarms() == num_previous_alarm:
                break
            time.sleep(check_interval)
        assert alarm_summary is not None
        assert alarm_summary.get_major_alarms() == num_previous_alarm


@mark.p0
@mark.lab_has_subcloud
def test_dc_install_custom_app():
    """
    Test upload, apply, remove, delete custom app via system cmd
    on Distributed Cloud

    Test Steps:
        Step 1: Transfer the app file to the active controller (setup)
            - Copy test files from local to the SystemController.
            - Check the copies on the SystemController.

        Step 2: Upload the app file to the active controller
            - Upload the custom app on the SystemController.
            - Check the upload on the SystemController.

        Step 3: Apply the custom app on the active controller
            - Apply the custom app on the SystemController.
            - Check the application on the SystemController.
            - Check the Docker image stored in the SystemController registry.local.

        Step 4: Clean the active controller
            - Remove the custom app from the active controller.
            - Check the custom app uninstallation.
            - Delete the custom app from the active controller.
            - Check the custom app deletion.

        Step 5: Transfer the app file to the subclouds (setup)
            - Copy test files from local to the subclouds.
            - Check the copies on the subclouds.

        Step 6: Upload the app file to the subclouds
            - Upload the custom app on the subclouds.
            - Check the upload on the subclouds.

        Step 7: Apply the custom app on the subclouds
            - Apply the custom app on the subclouds.
            - Check the application on the subclouds.
            - Check the Docker image stored in the subclouds registry.local.

        Step 8: Clean the subclouds
            - Remove the custom app from the subclouds.
            - Check the custom app uninstallation.
            - Delete the custom app from the subclouds.
            - Check the custom app deletion.

    """
    # Step 1: Transfer the app file to the active controller

    # Defines application name, application file name, source (local) and destination (remote) file paths.
    app_name = "hello-kitty"
    app_file_name = "hello-kitty-min-k8s-version.tgz"
    local_path = get_stx_resource_path(f"resources/cloud_platform/containers/{app_file_name}")
    remote_path = f"/home/{ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()}/{app_file_name}"

    # Opens an SSH session to active controller.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Opens an SFTP session to active controller.
    sftp_client = ssh_connection.get_sftp_client()

    # Sets the parameters for the app file transfer through a new instance of SecureTransferFileInputObject.
    secure_transfer_file_input_object = SecureTransferFileInputObject()
    secure_transfer_file_input_object.set_sftp_client(sftp_client)
    secure_transfer_file_input_object.set_origin_path(local_path)
    secure_transfer_file_input_object.set_destination_path(remote_path)
    secure_transfer_file_input_object.set_transfer_direction(TransferDirection.FROM_LOCAL_TO_REMOTE)
    secure_transfer_file_input_object.set_force(True)

    # Transfers the app file from local path to remote path.
    secure_transfer_file = SecureTransferFile(secure_transfer_file_input_object)
    secure_transfer_file.transfer_file()

    # Step 2: Upload the app file to the active controller

    # Setups the upload input object.
    system_application_upload_input = SystemApplicationUploadInput()
    system_application_upload_input.set_app_name(app_name)
    system_application_upload_input.set_app_version("0.1.0")
    system_application_upload_input.set_automatic_installation(False)
    system_application_upload_input.set_tar_file_path(remote_path)
    system_application_upload_input.set_force(True)

    # Uploads the app file to the active controller.
    system_application_upload_output = SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)

    # Asserts that the uploading process concluded successfully
    system_application_object = system_application_upload_output.get_system_application_object()
    assert system_application_object is not None, f"Expecting 'system_application_object' as not None, Observed: {system_application_object}."
    assert system_application_object.get_name() == app_name, f"Expecting 'app_name' = {app_name}, Observed: {system_application_object.get_name()}."
    assert system_application_object.get_status() == SystemApplicationStatusEnum.UPLOADED.value, f"Expecting 'system_application_object.get_status()' = {SystemApplicationStatusEnum.UPLOADED.value}, Observed: {system_application_object.get_status()}."

    # Step 3: Apply the custom app on the active controller

    # Executes the application installation
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)

    # Asserts that the applying process concluded successfully
    system_application_object = system_application_apply_output.get_system_application_object()
    assert system_application_object is not None, f"Expecting 'system_application_object' as not None, Observed: {system_application_object}."
    assert system_application_object.get_name() == app_name, f"Expecting 'app_name' = {app_name}, Observed: {system_application_object.get_name()}."
    assert system_application_object.get_status() == SystemApplicationStatusEnum.APPLIED.value, f"Expecting 'system_application_object.get_status()' = {SystemApplicationStatusEnum.APPLIED.value}, Observed: {system_application_object.get_status()}."

    # Step 4: Clean the active controller

    # Remove (uninstall) the application
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(app_name)
    system_application_remove_input.set_force_removal(True)
    system_application_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)
    assert system_application_output.get_system_application_object().get_status() == SystemApplicationStatusEnum.UPLOADED.value, f"Expecting 'system_application_output.get_system_application_object().get_status()' = {SystemApplicationStatusEnum.UPLOADED.value}, Observed: {system_application_output.get_system_application_object().get_status()}."

    # Deletes the application
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(app_name)
    system_application_delete_input.set_force_deletion(True)
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
    assert delete_msg == f"Application {app_name} deleted.\n", f"Expecting delete_msg = 'Application {app_name} deleted.\n', Observed: {delete_msg}."

    # Executes similar tests on the subclouds.

    # Retrieves the subclouds. Considers only subclouds that are online, managed, and synced.
    dcmanager_subcloud_list_input = DcManagerSubcloudListObjectFilter.get_healthy_subcloud_filter()
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    dcmanager_subcloud_list_objects_filtered = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_input)

    if not dcmanager_subcloud_list_objects_filtered:
        get_logger().log_info(f"Currently, there are no subclouds that are online, managed, sync-in, and deploy completed on {ssh_connection}.")
        return

    # Tests each filtered subcloud.
    for subcloud_list_object in dcmanager_subcloud_list_objects_filtered:
        # Step 5: Transfers the app file to the current subcloud.

        # Opens an SSH connection to the current subcloud.
        subcloud_name = subcloud_list_object.get_name()
        ssh_subcloud_connection = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        get_logger().log_info(f"Opened connection to subcloud {ssh_subcloud_connection.get_name()}.")

        # Opens an SFTP session to the current subcloud.
        sftp_client = ssh_subcloud_connection.get_sftp_client()

        # Changes only the 'sftp_client' property value; other properties can remain as previously configured.
        secure_transfer_file_input_object.set_sftp_client(sftp_client)

        # Transfer the app file to the current subcloud.
        secure_transfer_file = SecureTransferFile(secure_transfer_file_input_object)
        secure_transfer_file.transfer_file()

        # Step 6: Uploads the app file to the current subcloud.

        # There is no need to change anything in the upload input object 'system_application_upload_input'.
        system_application_upload_output = SystemApplicationUploadKeywords(ssh_subcloud_connection).system_application_upload(system_application_upload_input)

        # Asserts that the uploading process concluded successfully.
        system_application_object = system_application_upload_output.get_system_application_object()
        assert system_application_object is not None, f"Expecting 'system_application_object' as not None, Observed: {system_application_object}"
        assert system_application_object.get_name() == app_name, f"Expecting 'app_name' = {app_name}, Observed: {system_application_object.get_name()}"
        assert system_application_object.get_status() == SystemApplicationStatusEnum.UPLOADED.value, f"Expecting 'system_application_object.get_status()' = {SystemApplicationStatusEnum.UPLOADED.value}, Observed: {system_application_object.get_status()}"

        # Step 7: Apply the custom app on the current subcloud.

        # Executes the application installation. There is no need to change anything in the apply input object 'system_application_apply_input'.
        system_application_apply_output = SystemApplicationApplyKeywords(ssh_subcloud_connection).system_application_apply(app_name)

        # Asserts that the applying process concluded successfully on the current subcloud.
        system_application_object = system_application_apply_output.get_system_application_object()
        assert system_application_object is not None, f"Expecting 'system_application_object' as not None, Observed: {system_application_object}."
        assert system_application_object.get_name() == app_name, f"Expecting app_name = {app_name}, Observed: {system_application_object.get_name()}."
        assert system_application_object.get_status() == SystemApplicationStatusEnum.APPLIED.value, f"Expecting 'system_application_object.get_status()' = {SystemApplicationStatusEnum.APPLIED.value}, Observed: {system_application_object.get_status()}."

        # Step 8: Clean the current subcloud.

        # Remove (uninstall) the application on the current subcloud.
        system_application_remove_input = SystemApplicationRemoveInput()
        system_application_remove_input.set_app_name(app_name)
        system_application_remove_input.set_force_removal(True)
        system_application_output = SystemApplicationRemoveKeywords(ssh_subcloud_connection).system_application_remove(system_application_remove_input)
        assert system_application_output.get_system_application_object().get_status() == SystemApplicationStatusEnum.UPLOADED.value, f"Expecting 'system_application_output.get_system_application_object().get_status()' = {SystemApplicationStatusEnum.UPLOADED.value}, Observed: {system_application_output.get_system_application_object().get_status()}."

        # Deletes the application
        system_application_delete_input = SystemApplicationDeleteInput()
        system_application_delete_input.set_app_name(app_name)
        system_application_delete_input.set_force_deletion(True)
        delete_msg = SystemApplicationDeleteKeywords(ssh_subcloud_connection).get_system_application_delete(system_application_delete_input)
        assert delete_msg == f"Application {app_name} deleted.\n", f"Expecting delete_msg = 'Application {app_name} deleted.\n', Observed: {delete_msg}."


@mark.p0
@mark.lab_has_subcloud
def test_dc_swact_host(request):
    """
    Test host swact to verify if the subclouds remain in the 'managed' state even after a 'swact' occurs.

    Setup:
        _ Gets the managed, online, and synchronized subcloud with the lowest id (the lowest subcloud).
        _ Unmanages the lowest subcloud.
        _ Check the other subclouds are managed and online.

    Test Steps:
        _ Swact the host.
        _ Verify that the lowest subcloud are still unmanaged.
        _ Verify that the other subclouds are still managed.

    Teardown:
        _ Reestablishes the 'managed' status on the lowest subcloud.
        _ Reestablishes the active/standby host configuration.

    """
    get_logger().log_info("Starting 'test_dc_swact_host' test case.")

    # Time in seconds for a subcloud to change its state from 'managed' to 'unmanaged' and vice versa.
    change_state_timeout = 60

    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    get_logger().log_info("Obtaining subcloud with the lowest ID.")
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    get_logger().log_info(f"Subcloud with the lowest ID obtained: ID={lowest_subcloud.get_id()}, Name={lowest_subcloud.get_name()}, Management state={lowest_subcloud.get_management()}")

    # Unmanages the lowest subcloud.
    get_logger().log_info(f"Changing the management state of the subcloud {lowest_subcloud.get_name()}, which is the subcloud with the lowest ID, to 'unmanaged'.")
    dcmanager_subcloud_unmanage_keywords = DcManagerSubcloudManagerKeywords(ssh_connection)
    # Changes the state of lowest_subcloud to 'unmanaged' within a period of 'change_state_timeout'
    dcmanager_subcloud_manage_output = dcmanager_subcloud_unmanage_keywords.get_dcmanager_subcloud_unmanage(lowest_subcloud.get_name(), change_state_timeout)
    get_logger().log_info(f"The management state of the subcloud {lowest_subcloud.get_name()} was changed to {dcmanager_subcloud_manage_output.get_dcmanager_subcloud_manage_object().get_management()}.")

    # Refreshes the variable representing 'lowest_subcloud'.
    subcloud_id_filter = DcManagerSubcloudListObjectFilter()
    subcloud_id_filter.set_id(lowest_subcloud.get_id())
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects_filtered(subcloud_id_filter)[0]
    get_logger().log_info(f"The management state of the subcloud {lowest_subcloud.get_name()} was changed to '{lowest_subcloud.get_management()}'.")

    # Tear Down function: reestablishes the 'managed' status on lowest subcloud.
    def teardown_manage():
        dcmanager_subcloud_manage_keywords = DcManagerSubcloudManagerKeywords(ssh_connection)
        dcmanager_subcloud_manage_output = dcmanager_subcloud_manage_keywords.get_dcmanager_subcloud_manage(lowest_subcloud.get_name(), change_state_timeout)
        get_logger().log_info(f"The management state has been reestablished as {dcmanager_subcloud_manage_output.get_dcmanager_subcloud_manage_object().get_management()} on {lowest_subcloud.get_name()}")

    # The teardown_manage function must be added at this point because the lowest_subcloud has just had its state changed to 'unmanaged'.
    request.addfinalizer(teardown_manage)

    # Retrieves the managed subclouds before swact.
    dcmanager_subcloud_list_filter = DcManagerSubcloudListObjectFilter.get_healthy_subcloud_filter()
    managed_subclouds_before_swact = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_filter)

    # Registers the healthy subclouds in the log file.
    for managed_subcloud_before_swact in managed_subclouds_before_swact:
        get_logger().log_info(f"Management state of the subcloud {managed_subcloud_before_swact.get_name()} before swact operation: {managed_subcloud_before_swact.get_management()}.")

    # Swact the host
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list_keywords.get_active_controller()
    standby_controller = system_host_list_keywords.get_standby_controller()
    get_logger().log_info(f"A 'swact' operation is about to be executed in {ssh_connection}. Current controllers' configuration before this operation: Active controller = {active_controller.get_host_name()}, Standby controller = {standby_controller.get_host_name()}.")
    system_host_swact_keywords = SystemHostSwactKeywords(ssh_connection)
    system_host_swact_keywords.host_swact()
    swact_successfull = system_host_swact_keywords.wait_for_swact(active_controller, standby_controller)
    validate_equals(swact_successfull, True, "Validate that swact was successful")

    # Gets the controllers after the execution of the swact operation.
    active_controller_after_swact = system_host_list_keywords.get_active_controller()
    standby_controller_after_swact = system_host_list_keywords.get_standby_controller()

    validate_equals(active_controller.get_id(), standby_controller_after_swact.get_id(), "Validate that active controller is now standby")
    validate_equals(standby_controller.get_id(), active_controller_after_swact.get_id(), "Validate that standby controller is now active")

    # Tear Down function: reestablishes the active/standby host configuration.
    def teardown_swact():
        get_logger().log_info("Starting teardown_swact(). Reestablishing the previous active/standby configuration of the controllers.")
        system_host_list_keyword = SystemHostListKeywords(ssh_connection)
        active_controller_teardown_before_swact = system_host_list_keyword.get_active_controller()
        standby_controller_teardown_before_swact = system_host_list_keyword.get_standby_controller()
        get_logger().log_info(f"Current controller's configuration: Active controller = {active_controller_teardown_before_swact.get_host_name()}, Standby controller = {standby_controller_teardown_before_swact.get_host_name()}.")
        system_host_swact_keywords_teardown = SystemHostSwactKeywords(ssh_connection)
        system_host_swact_keywords_teardown.host_swact()
        swact_successfull = system_host_swact_keywords_teardown.wait_for_swact(active_controller_teardown_before_swact, standby_controller_teardown_before_swact)
        active_controller_teardown_after_swact = system_host_list_keyword.get_active_controller()
        standby_controller_teardown_after_swact = system_host_list_keyword.get_standby_controller()
        current_conf_message = f"Current controllers' active/standby configuration after swact in teardown: Previous active controller = {active_controller_teardown_before_swact.get_host_name()}, Current active controller = {active_controller_teardown_after_swact}, Previous standby controller = {standby_controller_teardown_before_swact.get_host_name()}, Current standby controller = {standby_controller_teardown_after_swact.get_host_name()}."
        if swact_successfull:
            message = f"The reestablishment of the active/standby controllers' configuration was successful. {current_conf_message}"
            get_logger().log_info(message)
        else:
            error_message = f"The reestablishment of the active/standby controllers' configuration failed. If it is desired to reestablish that configuration, the 'system host-swact <active host name>' command will need to be executed manually. {current_conf_message}"
            get_logger().log_info(error_message)

    # The teardown_manage function must be added at this point because the 'swact' operation has just been executed.
    request.addfinalizer(teardown_swact)

    # Asserts that the lowest subcloud is unmanaged.
    dcmanager_subcloud_list_filter = DcManagerSubcloudListObjectFilter()
    dcmanager_subcloud_list_filter.set_id(lowest_subcloud.get_id())
    lowest_subcloud_after_swact = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_filter)[0]
    validate_equals(lowest_subcloud_after_swact.get_management(), "unmanaged", "Validate subcloud is still unmanaged")

    # Retrieves the managed subclouds after swact.
    managed_subclouds_after_swact = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects_filtered(DcManagerSubcloudListObjectFilter.get_healthy_subcloud_filter())
    validate_equals(len(managed_subclouds_before_swact), len(managed_subclouds_after_swact), "Validate the number of managed subclouds is the same")

    # Asserts that the subclouds in subcloud_before_swact are the same as the subclouds in subcloud_after_swact, and
    # that all these subclouds are in 'managed' status.
    for subcloud_before_swact in managed_subclouds_before_swact:
        subcloud_after_swact = next((subcloud for subcloud in managed_subclouds_after_swact if subcloud.get_id() == subcloud_before_swact.get_id()), None)
        assert subcloud_after_swact is not None
        assert subcloud_after_swact.get_management() == "managed"
        get_logger().log_info(f"Management state of subcloud {subcloud_before_swact.get_name()} before 'swact' operation: {subcloud_before_swact.get_management()}. Management state of subcloud {subcloud_after_swact.get_name()} after 'swact' operation: {subcloud_after_swact.get_management()}.")

    get_logger().log_info("Completed the 'test_dc_swact_host' test case.")


@mark.p0
@mark.lab_has_subcloud
def test_dc_system_health_pre_session():
    """
    Test the health of the DC System to guarantee the following requirements in the central cloud and in the subclouds:
        _ Application 'platform-integ-apps' is in 'applied' status.
        _ No alarms are present.
        _ The health of Kubernetes pods.

    Setup:
        _ Defines a reference to 'platform-integ-apps' app name.
        _ Defines a list of opened SSH connections to the central cloud and to the subclouds.

    Test:
        _ For each SSH connection to a subcloud or to the central cloud in the list:
            _ Asserts the status of the 'platform-integ-apps' application is 'applied'
            _ Asserts that no alarms are present.
            _ Assert the Kubernetes pods are healthy.

    Teardown:
        _ Not required.

    """
    # The application 'platform-integ-apps' is responsible for the installation, management, and integration
    # of essential platform applications running on the underlying infrastructure. It must be in 'applied' status.
    platform_app = "platform-integ-apps"

    # List of DC system SSH connections.
    ssh_connections = []

    # Opens an SSH session to the active controller.
    ssh_connection_active_controller = LabConnectionKeywords().get_active_controller_ssh()

    # Retrieves the subclouds. Considers only subclouds that are online, managed, deploy complete, and synchronized.
    dcmanager_subcloud_list_object_filter = DcManagerSubcloudListObjectFilter().get_healthy_subcloud_filter()
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection_active_controller)
    dcmanager_subcloud_list = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list()
    dcmanager_subcloud_list_objects_filtered = dcmanager_subcloud_list.get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_object_filter)

    # Adds the central subcloud SSH connection to the list of SSH connections.
    ssh_connections.append(ssh_connection_active_controller)

    # Adds the subcloud SSH connection to the list of SSH connections.
    for subcloud in dcmanager_subcloud_list_objects_filtered:
        ssh_connections.append(LabConnectionKeywords().get_subcloud_ssh(subcloud.get_name()))

    for ssh_connection in ssh_connections:

        # Asserts the status of the <platform_app> application in the current SSH connection is 'applied',
        # provided the subcloud or central cloud has storage backends.
        system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
        system_storage_backends = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backends()
        if len(system_storage_backends) != 0:
            system_application_list_keywords = SystemApplicationListKeywords(ssh_connection)
            app_status = system_application_list_keywords.get_system_application_list().get_application(platform_app).get_status()
            assert app_status == "applied", f"The status of application '{platform_app}' is not 'applied'. Current status: {app_status}."

        # Asserts that no alarms are present
        alarm_list_keywords = AlarmListKeywords(ssh_connection)
        alarm_list_keywords.wait_for_all_alarms_cleared()
        # If this test case executed the line above with no exception, all alarms were cleared.

        kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
        kubectl_get_pods_keywords.wait_for_all_pods_status(expected_statuses="Running")
        # If this test case executed the line above with no exception, all the pods are "Running".


@mark.p0
@mark.lab_has_subcloud
def test_dc_unmanage_manage_subclouds(request):
    """
    Test unmanage/manage the subcloud with the lowest ID.
    Note: It could be any subcloud. In particular, the subcloud with the lowest ID was chosen in this test case.

    Setup:
        _ Ensure the subcloud is managed.
    Test Steps:
        _ Unmanage the subcloud with the lowest ID (it could be any).
        _ Manage the subcloud chosen above.
    Teardown:
        _ Manage the unmanaged subcloud.

    """
    # The maximum time in seconds to wait for the subcloud to change its state from managed to unmanaged and vice versa.
    change_state_timeout = 10
    get_logger().log_info(f"This test case will wait for each subcloud changing its 'management' state for {change_state_timeout} seconds.")

    # Gets the SSH connection to the active controller of the central subcloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_info(f"SSH connection to central subcloud: '{ssh_connection}'")

    # This test case gets the subcloud with the lowest ID to check the unmanage/manage functionality. It could be any.
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    dcmanager_subcloud_list = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list()
    subcloud = dcmanager_subcloud_list.get_healthy_subcloud_with_lowest_id()
    subcloud_name = subcloud.get_name()
    get_logger().log_info(f"The subcloud with the lowest ID will be considered in this test case. There is no special reason for that. It could be any subcloud. Subcloud chosen: name = {subcloud.get_name()}, ID = {subcloud.get_id()}.")

    # Object responsible for set the subclouds to 'managed'/'unmanaged' management state.
    dcmanager_subcloud_manage_keywords = DcManagerSubcloudManagerKeywords(ssh_connection)

    def teardown():
        # Reestablishes the original management state of the subcloud, if necessary.
        teardown_dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
        teardown_dcmanager_subcloud_list = teardown_dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list()
        teardown_subcloud = teardown_dcmanager_subcloud_list.get_subcloud_by_name(subcloud_name)
        if teardown_subcloud.get_management() == "unmanaged":
            dcmanager_subcloud_manage_keywords.get_dcmanager_subcloud_manage(teardown_subcloud.get_name(), change_state_timeout)
            get_logger().log_info(f"Teardown: The original management state of the subcloud '{teardown_subcloud.get_name()}' was reestablished to '{teardown_subcloud.get_management()}'.")
        else:
            get_logger().log_info(f"Teardown: There's no need to reestablish the original management state of the subcloud '{teardown_subcloud.get_name()}', as it is already in the 'managed' state. Current management state: '{teardown_subcloud.get_management()}'")

    request.addfinalizer(teardown)

    get_logger().log_info(f"Starting the first step of this test case: 'Unmanage the subcloud'. Subcloud: {subcloud.get_name()}")

    # Tries to change the state of the subcloud to 'unmanaged' and waits for it for 'change_state_timeout' seconds.
    dcmanager_subcloud_manage_output = dcmanager_subcloud_manage_keywords.get_dcmanager_subcloud_unmanage(subcloud.get_name(), change_state_timeout)

    assert dcmanager_subcloud_manage_output.get_dcmanager_subcloud_manage_object().get_management() == "unmanaged", f"It was not possible to change the management state of the subcloud {subcloud.get_name()} to 'unmanaged'."
    get_logger().log_info(f"Subcloud '{subcloud.get_name()}' had its management state changed to 'unmanaged' successfully.")

    get_logger().log_info("The first step of this test case is concluded.")

    get_logger().log_info(f"Starting the second step of this test case: 'Manage the subcloud'. Subcloud: {subcloud.get_name()}")

    # Tries to change the state of the subcloud to 'managed' and waits for it for 'change_state_timeout' seconds.
    dcmanager_subcloud_manage_output = dcmanager_subcloud_manage_keywords.get_dcmanager_subcloud_manage(subcloud.get_name(), change_state_timeout)

    assert dcmanager_subcloud_manage_output.get_dcmanager_subcloud_manage_object().get_management() == "managed", f"It was not possible to change the management state of the subcloud {subcloud.get_name()} to 'managed'."
    get_logger().log_info(f"Subcloud '{subcloud.get_name()}' had its management state changed to 'managed' successfully.")

    get_logger().log_info("The second and last step of this test case is concluded.")


@mark.p0
@mark.lab_has_subcloud
def test_dc_central_lock_unlock_host(request):
    """
    Verify lock/unlock of hosts (standby and compute hosts).

    Test Steps:
        - Retrieve the standby controller.
        - Lock standby controller and ensure it is successfully locked.
        - Unlock standby controller and ensure it is successfully unlocked.
    """
    # Gets the SSH connection to the active controller.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_info(f"SSH connection to active controller: {ssh_connection}.")

    # Gets the standby controller (represented by a SystemHostObject instance).
    standby_controller = SystemHostListKeywords(ssh_connection).get_standby_controller()
    get_logger().log_info(f"Standby controller retrieved. ID: {standby_controller.get_id()}.")

    # Gets the host name of the standby controller.
    standby_host_name = standby_controller.get_host_name()
    get_logger().log_info(f"Standby controller's name: {standby_host_name}.")

    # Gets the object responsible for lock/unlock the hosts under test.
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)

    def teardown():
        # Unlocks the standby host if it was locked in this test but not unlocked.
        if system_host_lock_keywords.is_host_locked(standby_host_name):
            system_host_lock_keywords.unlock_host(standby_host_name)
            get_logger().log_error(f"Teardown: The host {standby_host_name} was successfully unlocked.")
        else:
            get_logger().log_info(f"Teardown: It was not necessary to unlock the host {standby_host_name}.")

    request.addfinalizer(teardown)

    # Tries to lock the standby host.
    get_logger().log_info(f"The host {standby_host_name} will be set to the 'locked' state.")
    system_host_lock_keywords.lock_host(standby_host_name)
    assert system_host_lock_keywords.is_host_locked(standby_host_name), f"It was not possible to lock the host {standby_host_name}."
    get_logger().log_info(f"The host {standby_host_name} was successfully set to 'locked' state.")

    # Tries to unlock the standby host.
    get_logger().log_info(f"The host {standby_host_name} will be set to 'unlocked' state.")
    system_host_lock_keywords.unlock_host(standby_host_name)
    assert system_host_lock_keywords.is_host_unlocked(standby_host_name), f"It was not possible to unlock the host {standby_host_name}."
    get_logger().log_info(f"The host {standby_host_name} was successfully set to 'unlocked' state.")


@mark.p0
@mark.lab_has_compute
def test_dc_central_compute_lock_unlock(request):
    """
    Verify lock/unlock of 'Compute' type node in the Central controller.

    Test Steps:
        - Retrieves 'Compute' type node instance.
        - Locks the node and ensure it is successfully locked.
        - Unlocks the node and ensure it is successfully unlocked.
    """
    # Gets the SSH connection to the active controller.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_info(f"SSH connection to active controller: {ssh_connection}.")

    # Gets the object responsible for lock/unlock the hosts under test.
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)

    # Gets the first 'Compute' node.
    lab_config = ConfigurationManager.get_lab_config()
    computes = lab_config.get_computes()
    assert len(computes) > 0, "This Central Controller has no nodes of type 'Compute'."
    compute: Node = computes[0]
    compute_name = compute.get_name()

    def teardown():
        # Unlocks the  'Compute' Node if it was locked in this test but not unlocked.
        if system_host_lock_keywords.is_host_locked(compute_name):
            system_host_lock_keywords.unlock_host(compute_name)
            get_logger().log_error(f"Teardown: The 'Compute' node {compute_name} was successfully unlocked.")
        else:
            get_logger().log_info(f"Teardown: It was not necessary to unlock the 'Compute' node {compute_name}.")

    request.addfinalizer(teardown)

    # Tries to lock the 'Compute' node.
    get_logger().log_info(f"The 'Compute' node {compute_name} will be set to the 'locked' state.")
    system_host_lock_keywords.lock_host(compute_name)
    assert system_host_lock_keywords.is_host_locked(compute_name), f"It was not possible to lock the 'Compute' node {compute_name}."
    get_logger().log_info(f"The 'Compute' node {compute_name} was successfully set to 'locked' state.")

    # Tries to unlock the 'Compute' node.
    get_logger().log_info(f"The 'Compute' node {compute_name} will be set to 'unlocked' state.")
    system_host_lock_keywords.unlock_host(compute_name)
    assert system_host_lock_keywords.is_host_unlocked(compute_name), f"It was not possible to unlock the 'Compute' node {compute_name}."
    get_logger().log_info(f"The 'Compute' node {compute_name} was successfully set to 'unlocked' state.")


@mark.p0
@mark.lab_has_subcloud
def test_dc_subcloud_update_description(request):
    """
    Verify subcloud update description

    Test Steps:
        - log onto active controller
        - Get original description
        - Run dcmanager subcloud update <subcloud_name> --description <new_description>
        - validate that subcloud has new description
        - Reset description back to old description
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    test_description = "test description"

    lab_config = ConfigurationManager.get_lab_config()
    subclouds = lab_config.get_subclouds()
    assert len(subclouds) != 0, "Failed. No subclouds were found"

    # Get the first subcloud from the list
    subcloud = subclouds[0]
    subcloud_name = subcloud.get_lab_name()

    subcloud_show_object = DcManagerSubcloudShowKeywords(ssh_connection).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object()
    original_description = subcloud_show_object.get_description()

    subcloud_update_output = DcManagerSubcloudUpdateKeywords(ssh_connection).dcmanager_subcloud_update(subcloud_name, "description", test_description)
    new_description = subcloud_update_output.get_dcmanager_subcloud_show_object().get_description()

    def teardown():
        DcManagerSubcloudUpdateKeywords(ssh_connection).dcmanager_subcloud_update(subcloud_name, "description", original_description)

    request.addfinalizer(teardown)

    validate_equals(new_description, test_description, "Validate that the description has been changed")


@mark.p0
@mark.lab_has_subcloud
def test_dc_subcloud_update_location(request):
    """
    Verify subcloud update location

    Test Steps:
        - log onto active controller
        - Get original location
        - Run dcmanager subcloud update <subcloud_name> --location <new_description>
        - validate that subcloud has new location
        - Reset location back to old location
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    test_location = "test location"

    lab_config = ConfigurationManager.get_lab_config()
    subclouds = lab_config.get_subclouds()
    assert len(subclouds) != 0, "Failed. No subclouds were found"

    # Get the first subcloud from the list
    subcloud = subclouds[0]
    subcloud_name = subcloud.get_lab_name()

    subcloud_show_object = DcManagerSubcloudShowKeywords(ssh_connection).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object()
    original_location = subcloud_show_object.get_location()

    subcloud_update_output = DcManagerSubcloudUpdateKeywords(ssh_connection).dcmanager_subcloud_update(subcloud_name, "location", test_location)
    new_location = subcloud_update_output.get_dcmanager_subcloud_show_object().get_location()

    def teardown():
        DcManagerSubcloudUpdateKeywords(ssh_connection).dcmanager_subcloud_update(subcloud_name, "location", original_location)

    request.addfinalizer(teardown)

    validate_equals(new_location, test_location, "Validate that the location has been changed")


@mark.p0
@mark.lab_has_subcloud
def test_dc_central_force_reboot_host_active_controller():
    """
    Verify force reboot of an active controller

    Test Steps:
        - log onto active controller
        - sudo reboot -f
        - validate that system comes back in correct state
    """
    # Opens an SSH session to active controller.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # get the host name of the active controller
    host_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    # get the prev uptime of the host so we can be sure it re-started
    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime(host_name)

    # force reboot the active controller
    ssh_connection.send_as_sudo("sudo reboot -f")

    wait_for_reboot_to_start(host_name, ssh_connection)

    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(host_name, pre_uptime_of_host)

    assert reboot_success, "Host was not rebooted successfully"


@mark.p0
@mark.lab_has_subcloud
def test_dc_central_force_reboot_host_standby_controller():
    """
    Verify force reboot of an standby controller

    Test Steps:
        - log onto standby controller
        - sudo reboot -f
        - validate that system comes back in correct state
    """
    # Opens an SSH session to active controller.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    standby_ssh_connection = LabConnectionKeywords().get_standby_controller_ssh()

    # get the host name of the standby controller
    host_name = SystemHostListKeywords(ssh_connection).get_standby_controller().get_host_name()

    # get the prev uptime of the host so we can be sure it re-started
    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime(host_name)

    # force reboot the standby controller
    standby_ssh_connection.send_as_sudo("sudo reboot -f")

    wait_for_reboot_to_start(host_name, ssh_connection)

    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(host_name, pre_uptime_of_host)

    assert reboot_success, "Host was not rebooted successfully"


@mark.p0
@mark.lab_has_subcloud
@mark.lab_has_worker
def test_dc_central_force_reboot_host_compute():
    """
    Verify force reboot of an compute

    Test Steps:
        - log onto compute
        - sudo reboot -f
        - validate that system comes back in correct state
    """
    # Opens an SSH session to active controller.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    computes = SystemHostListKeywords(ssh_connection).get_computes()

    assert len(computes) > 0, "No computes were found"

    # get the first compute
    compute = computes[0]

    compute_ssh_connection = LabConnectionKeywords().get_compute_ssh(compute.get_host_name())

    # get the prev uptime of the host so we can be sure it re-started
    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime(compute.get_host_name())

    # force reboot the standby controller
    compute_ssh_connection.send_as_sudo("reboot -f")

    wait_for_reboot_to_start(compute.get_host_name(), ssh_connection)

    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(compute.get_host_name(), pre_uptime_of_host)

    assert reboot_success, "Host was not rebooted successfully"


def wait_for_reboot_to_start(host_name: str, ssh_connection: SSHConnection, timeout: int = 60):
    """
    Returns true once we've got availability of offline indicating a reboot has started.
    """
    timeout = time.time() + timeout
    refresh_time = 5

    while time.time() < timeout:
        try:
            host_value = SystemHostListKeywords(ssh_connection).get_system_host_list().get_host(host_name)
            if host_value.get_availability() == "offline":
                return True
        except Exception:
            get_logger().log_info(f"Found an exception when running system host list command. " f"Trying again after {refresh_time} seconds")

        time.sleep(refresh_time)

    return False


@mark.p0
@mark.lab_has_subcloud
def test_dc_modify_timezone(request):
    """
    Verify modifying the timezone and ensure change it not propagated to Subcloud

    Test Steps:
        - log onto system
        - Ensure that lab is already in UTC
        - run system modify --timezone="America/Los_Angeles"
        - Run linux command to ensure that the timezone was changed
        - Check that the subcloud has not changed
        - Reset lab back to UTC
    """
    # Opens an SSH session to active controller.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    system_modify_keywords = SystemModifyKeywords(ssh_connection)
    # ensure we are in UTC to start
    system_show_object = SystemShowKeywords(ssh_connection).system_show().get_system_show_object()
    if system_show_object.get_timezone() != "UTC":
        system_modify_output = system_modify_keywords.system_modify_timezone("UTC")
        validate_equals(system_modify_output.get_system_show_object().get_timezone(), "UTC", "Update the timezone to UTC.")

    def teardown():
        system_modify_output = system_modify_keywords.system_modify_timezone("UTC")
        validate_equals(system_modify_output.get_system_show_object().get_timezone(), "UTC", "Update the timezone to UTC.")

    request.addfinalizer(teardown)

    system_modify_output = system_modify_keywords.system_modify_timezone("America/Los_Angeles")
    validate_equals(system_modify_output.get_system_show_object().get_timezone(), "America/Los_Angeles", "Update the timezone to America/Los_Angeles.")
    validate_equals(DateKeywords(ssh_connection).get_timezone(), "PST", "validate that the system timezone is now PST")

    # check the subcloud to ensure the time zone change does not propagate
    dcmanager_subcloud_list = DcManagerSubcloudListKeywords(ssh_connection).get_dcmanager_subcloud_list()
    subcloud_name = dcmanager_subcloud_list.get_healthy_subcloud_with_lowest_id().get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    system_show_object = SystemShowKeywords(subcloud_ssh).system_show().get_system_show_object()
    validate_equals(system_show_object.get_timezone(), "UTC", "Subcloud timezone is still UTC.")


@mark.p0
def test_pod_to_pod_connection(request):
    """
    Verify connection via ping between pods
    Test Steps:
        - import images node-hello and pv-test to local registry
        - deploy both client and server pods
        - from client1 pod validate successful ping to both server pods
        - from client2 pod validate successful ping to both server pods

    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    deploy_images_to_local_registry(ssh_connection)

    pods = deploy_pods(request, ssh_connection)
    server_pods = pods.get_pods_start_with("server-pod-dep")
    server_pod1_name = server_pods[0].get_name()
    server_pod2_name = server_pods[1].get_name()

    server_pod_1_ip = pods.get_pod(server_pod1_name).get_ip()
    server_pod_2_ip = pods.get_pod(server_pod2_name).get_ip()

    # validate that client pod 1 can ping server pod1
    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    kubeclt_exec_in_pods.run_pod_exec_cmd("client-pod1", f"ping -c 3 {server_pod_1_ip} -w 5")
    assert ssh_connection.get_return_code() == 0, "One or more cleanup items failed."

    # validate that client pod 1 can ping server pod2
    kubeclt_exec_in_pods.run_pod_exec_cmd("client-pod1", f"ping -c 3 {server_pod_2_ip} -w 5")
    assert ssh_connection.get_return_code() == 0

    # validate that client pod 2 can ping server pod1
    kubeclt_exec_in_pods.run_pod_exec_cmd("client-pod2", f"ping -c 3 {server_pod_1_ip} -w 5")
    assert ssh_connection.get_return_code() == 0

    # validate that client pod 2 can ping server pod2
    kubeclt_exec_in_pods.run_pod_exec_cmd("client-pod2", f"ping -c 3 {server_pod_2_ip} -w 5")
    assert ssh_connection.get_return_code() == 0


@mark.p0
def test_pod_to_service_connection(request):
    """
    Testcase to validate client pod to service connection
    Test Steps:
        - import images node-hello and pv-test to local registry
        - deploy both client and server pods
        - from client pod1, test curl to server pods ip's
        - from client pod2, test curl to server pods ip's

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    deploy_images_to_local_registry(ssh_connection)

    pods = deploy_pods(request, ssh_connection)
    server_pods = pods.get_pods_start_with("server-pod-dep")
    server_pod1_name = server_pods[0].get_name()
    server_pod2_name = server_pods[1].get_name()

    server_pod_1_ip = pods.get_pod(server_pod1_name).get_ip()
    server_pod_2_ip = pods.get_pod(server_pod2_name).get_ip()

    if ConfigurationManager.get_lab_config().is_ipv6():
        server_pod_1_ip = f"[{server_pod_1_ip}]"
        server_pod_2_ip = f"[{server_pod_2_ip}]"

    # validate client pod 1 curl with server pod 1
    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    kubeclt_exec_in_pods.run_pod_exec_cmd("client-pod1", f"curl -Is {server_pod_1_ip}:8080")
    assert ssh_connection.get_return_code() == 0

    # validate client pod 1 curl with server pod 2
    kubeclt_exec_in_pods.run_pod_exec_cmd("client-pod1", f"curl -Is {server_pod_2_ip}:8080")
    assert ssh_connection.get_return_code() == 0

    # validate client pod 2 curl with server pod 1
    kubeclt_exec_in_pods.run_pod_exec_cmd("client-pod2", f"curl -Is {server_pod_1_ip}:8080")
    assert ssh_connection.get_return_code() == 0

    # validate client pod 2 curl with server pod 2
    kubeclt_exec_in_pods.run_pod_exec_cmd("client-pod2", f"curl -Is {server_pod_2_ip}:8080")
    assert ssh_connection.get_return_code() == 0


@mark.p0
def test_host_to_service_connection(request):
    """
    Test to validate the service connectivity from external network
    Test Steps:
        - import images node-hello and pv-test to local registry
        - deploy both client and server pods
        - expose the service with node Port
        - from run agent, test service url with curl
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    deploy_images_to_local_registry(ssh_connection)

    deploy_pods(request, ssh_connection)
    KubectlExposeDeploymentKeywords(ssh_connection).expose_deployment("server-pod-dep", "NodePort", "test-service")

    def remove_service():
        KubectlDeleteServiceKeywords(ssh_connection).delete_service("test-service")

    request.addfinalizer(remove_service)

    node_port = KubectlGetServiceKeywords(ssh_connection).get_service_node_port("test-service")

    url = f"http://{ConfigurationManager.get_lab_config().get_floating_ip()}:{node_port}"
    if ConfigurationManager.get_lab_config().is_ipv6():
        url = f"http://[{ConfigurationManager.get_lab_config().get_floating_ip()}]:{node_port}"

    ssh_connection.send(f"curl -Is {url}")

    assert ssh_connection.get_return_code() == 0


def deploy_images_to_local_registry(ssh_connection: SSHConnection):
    """
    Deploys images to the local registry for testcases in this suite.

    Args:
        ssh_connection (SSHConnection): the SSH connection.
    """
    local_registry = ConfigurationManager.get_docker_config().get_registry("local_registry")

    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path("resources/images/pv-test.tar"), "/home/sysadmin/pv-test.tar", overwrite=False)

    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, "local-secret")
    docker_load_image_keywords = DockerLoadImageKeywords(ssh_connection)
    docker_load_image_keywords.load_docker_image_to_host("pv-test.tar")
    docker_load_image_keywords.tag_docker_image_for_registry("registry.local:9001/pv-test", "pv-test", local_registry)
    docker_load_image_keywords.push_docker_image_to_registry("pv-test", local_registry)

    file_keywords.upload_file(get_stx_resource_path("resources/cloud_platform/images/node-hello-alpine/node-hello-alpine.tar.gz"), "/home/sysadmin/node-hello-alpine.tar.gz", overwrite=False)
    TarKeywords(ssh_connection).decompress_tar_gz("/home/sysadmin/node-hello-alpine.tar.gz")
    docker_load_image_keywords.load_docker_image_to_host("node-hello-alpine.tar")
    docker_load_image_keywords.tag_docker_image_for_registry("node-hello:alpine", "node-hello", local_registry)
    docker_load_image_keywords.push_docker_image_to_registry("node-hello", local_registry)
