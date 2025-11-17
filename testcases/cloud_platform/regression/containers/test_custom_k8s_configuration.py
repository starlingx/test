from os.path import basename
from typing import List

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_none, validate_not_none
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.service.objects.system_service_parameter_list_object import SystemServiceParameterListObject
from keywords.cloud_platform.system.service.system_service_keywords import SystemServiceKeywords
from keywords.files.file_keywords import FileKeywords

VOLUME_FOR_KUBE_API_SERVER_LOCAL_FILE_PATH = "resources/cloud_platform/containers/k8s_configuration/admission-control-config-file.yaml"
VOLUME_FOR_KUBE_API_SERVER_REMOTE_FILE_PATH = "/etc/kubernetes/admission-control-config-file.yaml"
AUDIT_POLICY_LOGS_LOCAL_FILE_PATH = "resources/cloud_platform/containers/k8s_configuration/eventconfig.yaml"
AUDIT_POLICY_LOGS_REMOTE_FILE_PATH = "/etc/kubernetes/eventconfig.yaml"


def upload_file_with_sudo(ssh_connection: SSHConnection, local_file_path: str, remote_file_path: str):
    """Upload a file to a privileged location by uploading to /tmp first, then moving with sudo.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
        local_file_path (str): Local file path to upload.
        remote_file_path (str): Remote destination path (may require root).
    """
    tmp_path = f"/tmp/{basename(remote_file_path)}"
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(local_file_path=local_file_path, remote_file_path=tmp_path)
    file_keywords.move_file(tmp_path, remote_file_path, sudo=True)


def volume_for_kube_api_server_list() -> List[SystemServiceParameterListObject]:
    """Returns the list of SystemServiceParameterListObject for VolumeForKubeAPIServer.

    Returns:
        List[SystemServiceParameterListObject]: List of SystemServiceParameterListObject.
    """
    return [
        SystemServiceParameterListObject(
            service="kubernetes",
            section="kube_apiserver_volumes",
            name="eventconfig",
            value="hostPath:/etc/kubernetes/eventconfig.yaml",
        ),
        SystemServiceParameterListObject(
            service="kubernetes",
            section="kube_apiserver_volumes",
            name="admission-control-config",
            value="hostPath:/etc/kubernetes/admission-control-config-file.yaml",
        ),
        SystemServiceParameterListObject(
            service="kubernetes",
            section="kube_apiserver",
            name="admission-control-config-file",
            value="/etc/kubernetes/admission-control-config-file.yaml",
        ),
        SystemServiceParameterListObject(
            service="kubernetes",
            section="kube_apiserver",
            name="enable-admission-plugins",
            value="EventRateLimit",
        ),
    ]


def parameter_turn_on_audit_policy_logs_list() -> List[SystemServiceParameterListObject]:
    """Returns the list of SystemServiceParameterListObject for TurnOnAuditPolicyLogs.

    Returns:
        List[SystemServiceParameterListObject]: List of SystemServiceParameterListObject.
    """
    return [
        SystemServiceParameterListObject(
            service="kubernetes",
            section="kube_apiserver",
            name="audit-policy-file",
            value="/etc/kubernetes/eventconfig.yaml",
        ),
    ]


def verify_parameters_applied(ssh_connection: SSHConnection, parameters: List[SystemServiceParameterListObject]):
    """Verify if the service parameters were applied correctly.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
        parameters (List[SystemServiceParameterListObject]): List of expected parameters.
    """
    system_service_list = SystemServiceKeywords(ssh_connection).get_system_service_parameter_list()
    for system_service_parameter in parameters:
        get_logger().log_test_case_step(f"Asserting parameter {system_service_parameter.section} {system_service_parameter.name} is listed")
        parameter_found = next(
            (param for param in system_service_list.parameters if param.service == system_service_parameter.service and param.section == system_service_parameter.section and param.name == system_service_parameter.name and param.value == system_service_parameter.value),
            None,
        )
        validate_not_none(parameter_found, f"Parameter {system_service_parameter.section} {system_service_parameter.name} should be present")


def verify_parameters_deleted(ssh_connection: SSHConnection, parameters: List[SystemServiceParameterListObject]):
    """Verify if the service parameters were deleted correctly.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
        parameters (List[SystemServiceParameterListObject]): List of parameters to verify deletion.
    """
    system_service_list = SystemServiceKeywords(ssh_connection).get_system_service_parameter_list()
    for system_service_parameter in parameters:
        get_logger().log_test_case_step(f"Asserting parameter {system_service_parameter.section} {system_service_parameter.name} is deleted")
        parameter_found = next(
            (param for param in system_service_list.parameters if param.service == system_service_parameter.service and param.section == system_service_parameter.section and param.name == system_service_parameter.name and param.value == system_service_parameter.value),
            None,
        )
        validate_none(parameter_found, f"Parameter {system_service_parameter.section} {system_service_parameter.name} should be deleted")


def delete_parameters_and_files(ssh_connection: SSHConnection, parameters: List[SystemServiceParameterListObject], remote_file_path: str):
    """Delete service parameters and associated remote files.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
        parameters (List[SystemServiceParameterListObject]): List of parameters to delete.
        remote_file_path (str): Remote file path to delete.
    """
    get_logger().log_test_case_step("Deleting service parameters")
    SystemServiceKeywords(ssh_connection).delete_service_parameters(parameters)
    file_keywords = FileKeywords(ssh_connection)
    get_logger().log_test_case_step(f"Deleting remote file {remote_file_path}")
    file_keywords.delete_file(remote_file_path)
    validate_equals(file_keywords.file_exists(remote_file_path), False, f"File {remote_file_path} should be deleted")


def cleanup_parameters_and_files(ssh_connection: SSHConnection, parameters: List[SystemServiceParameterListObject], remote_file_path: str):
    """Clean up service parameters and associated remote files, ignoring already deleted ones.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
        parameters (List[SystemServiceParameterListObject]): List of parameters to clean up.
        remote_file_path (str): Remote file path to delete.
    """
    get_logger().log_test_case_step("Cleaning up service parameters")
    SystemServiceKeywords(ssh_connection).cleanup_service_parameters(parameters)
    file_keywords = FileKeywords(ssh_connection)
    get_logger().log_test_case_step(f"Deleting remote file {remote_file_path}")
    file_keywords.delete_file(remote_file_path)
    validate_equals(file_keywords.file_exists(remote_file_path), False, f"File {remote_file_path} should be deleted")


@mark.p2
@mark.lab_is_simplex
def test_add_valid_parameter_volume_for_kube_apiserver_to_k8s_simplex():
    """Verify adding, applying, and deleting kube_apiserver volume parameters on a simplex system.

    Test Steps:
        Clean up any existing parameters and prepare configuration files.
        Upload admission-control-config-file.yaml and eventconfig.yaml.
        Add kube_apiserver volume parameters and apply to Kubernetes.
        Assert out-of-date alarm is present at hosts.
        Apply Kubernetes service parameters and wait for stabilization.
        Verify the new configuration is applied.
        Delete parameters, configuration files, and verify deletion was successful.
        Apply Kubernetes service parameters after deletion.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleaning up existing parameters and preparing files")
    cleanup_parameters_and_files(ssh_connection, volume_for_kube_api_server_list(), VOLUME_FOR_KUBE_API_SERVER_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Uploading admission-control-config-file.yaml")
    upload_file_with_sudo(ssh_connection, get_stx_resource_path(VOLUME_FOR_KUBE_API_SERVER_LOCAL_FILE_PATH), VOLUME_FOR_KUBE_API_SERVER_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Uploading eventconfig.yaml")
    upload_file_with_sudo(ssh_connection, get_stx_resource_path(AUDIT_POLICY_LOGS_LOCAL_FILE_PATH), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Adding kube_apiserver volume parameters")
    for param in volume_for_kube_api_server_list():
        SystemServiceKeywords(ssh_connection).add_service_parameter(service=param.service, parameter=f"{param.section} {param.name}", value=param.value)

    get_logger().log_test_case_step("Asserting out-of-date alarm is present at hosts")
    validate_equals(AlarmListKeywords(ssh_connection).is_alarm_present("250.001"), True, "Out-of-date alarm 250.001 should be present")

    get_logger().log_test_case_step("Applying parameters for Kubernetes")
    SystemServiceKeywords(ssh_connection).apply_kubernetes_service_parameters()

    get_logger().log_test_case_step("Verifying the new configuration is applied")
    verify_parameters_applied(ssh_connection, volume_for_kube_api_server_list())

    get_logger().log_test_case_step("Deleting parameters")
    delete_parameters_and_files(ssh_connection, volume_for_kube_api_server_list(), VOLUME_FOR_KUBE_API_SERVER_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Deleting eventconfig.yaml")
    FileKeywords(ssh_connection).delete_file(AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Applying parameters for Kubernetes after deletion")
    SystemServiceKeywords(ssh_connection).apply_kubernetes_service_parameters()
    verify_parameters_deleted(ssh_connection, volume_for_kube_api_server_list())

    get_logger().log_info("Custom k8s configuration tests passed")


@mark.p2
@mark.lab_is_simplex
def test_add_valid_parameter_turn_on_audit_policy_logs_to_k8s_simplex():
    """Verify adding, applying, and deleting audit policy log parameters on a simplex system.

    Test Steps:
        Clean up any existing parameters and prepare configuration files.
        Add audit-policy-file parameter and apply to Kubernetes.
        Assert out-of-date alarm is present at hosts.
        Apply Kubernetes service parameters and wait for stabilization.
        Verify the new configuration is applied.
        Delete parameters and verify deletion was successful.
        Apply Kubernetes service parameters after deletion.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleaning up existing parameters and preparing files")
    cleanup_parameters_and_files(ssh_connection, parameter_turn_on_audit_policy_logs_list(), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Uploading eventconfig.yaml")
    upload_file_with_sudo(ssh_connection, get_stx_resource_path(AUDIT_POLICY_LOGS_LOCAL_FILE_PATH), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Adding audit-policy-file parameter")
    for param in parameter_turn_on_audit_policy_logs_list():
        SystemServiceKeywords(ssh_connection).add_service_parameter(service=param.service, parameter=f"{param.section} {param.name}", value=param.value)

    get_logger().log_test_case_step("Asserting out-of-date alarm is present at hosts")
    validate_equals(AlarmListKeywords(ssh_connection).is_alarm_present("250.001"), True, "Out-of-date alarm 250.001 should be present")

    get_logger().log_test_case_step("Applying parameters for Kubernetes")
    SystemServiceKeywords(ssh_connection).apply_kubernetes_service_parameters()

    get_logger().log_test_case_step("Verifying the new configuration is applied")
    verify_parameters_applied(ssh_connection, parameter_turn_on_audit_policy_logs_list())

    get_logger().log_test_case_step("Deleting parameters")
    delete_parameters_and_files(ssh_connection, parameter_turn_on_audit_policy_logs_list(), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Applying parameters for Kubernetes after deletion")
    SystemServiceKeywords(ssh_connection).apply_kubernetes_service_parameters()
    verify_parameters_deleted(ssh_connection, parameter_turn_on_audit_policy_logs_list())

    get_logger().log_info("Custom k8s configuration tests passed")


@mark.p2
@mark.lab_is_duplex
def test_add_valid_parameter_volume_for_kube_apiserver_to_k8s_duplex():
    """Verify adding, applying, swacting, and deleting kube_apiserver volume parameters on a duplex system.

    Test Steps:
        Clean up any existing parameters and prepare configuration files.
        Upload admission-control-config-file.yaml and eventconfig.yaml.
        Add kube_apiserver volume parameters and apply to Kubernetes.
        Assert out-of-date alarm is present at hosts.
        Apply Kubernetes service parameters and wait for stabilization.
        Verify the new configuration is applied.
        Apply host-swact between controllers.
        Verify the synced configuration between controllers.
        Delete parameters, configuration files, and verify deletion was successful.
        Apply Kubernetes service parameters after deletion.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleaning up existing parameters and preparing files")
    cleanup_parameters_and_files(ssh_connection, volume_for_kube_api_server_list(), VOLUME_FOR_KUBE_API_SERVER_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Uploading admission-control-config-file.yaml")
    upload_file_with_sudo(ssh_connection, get_stx_resource_path(VOLUME_FOR_KUBE_API_SERVER_LOCAL_FILE_PATH), VOLUME_FOR_KUBE_API_SERVER_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Uploading eventconfig.yaml")
    upload_file_with_sudo(ssh_connection, get_stx_resource_path(AUDIT_POLICY_LOGS_LOCAL_FILE_PATH), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Adding kube_apiserver volume parameters")
    for param in volume_for_kube_api_server_list():
        SystemServiceKeywords(ssh_connection).add_service_parameter(service=param.service, parameter=f"{param.section} {param.name}", value=param.value)

    get_logger().log_test_case_step("Asserting out-of-date alarm is present at hosts")
    validate_equals(AlarmListKeywords(ssh_connection).is_alarm_present("250.001"), True, "Out-of-date alarm 250.001 should be present")

    get_logger().log_test_case_step("Applying parameters for Kubernetes")
    SystemServiceKeywords(ssh_connection).apply_kubernetes_service_parameters()

    get_logger().log_test_case_step("Verifying the new configuration is applied")
    verify_parameters_applied(ssh_connection, volume_for_kube_api_server_list())

    get_logger().log_test_case_step("Applying host-swact between controllers")
    SystemHostSwactKeywords(ssh_connection).host_swact()

    get_logger().log_test_case_step("Verifying the synced configuration between controllers")
    verify_parameters_applied(ssh_connection, volume_for_kube_api_server_list())

    get_logger().log_test_case_step("Deleting parameters")
    delete_parameters_and_files(ssh_connection, volume_for_kube_api_server_list(), VOLUME_FOR_KUBE_API_SERVER_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Deleting eventconfig.yaml")
    FileKeywords(ssh_connection).delete_file(AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Applying parameters for Kubernetes after deletion")
    SystemServiceKeywords(ssh_connection).apply_kubernetes_service_parameters()
    verify_parameters_deleted(ssh_connection, volume_for_kube_api_server_list())

    get_logger().log_info("Custom k8s configuration tests passed")


@mark.p2
@mark.lab_is_duplex
def test_add_valid_parameter_turn_on_audit_policy_logs_to_k8s_duplex():
    """Verify adding, applying, swacting, and deleting audit policy log parameters on a duplex system.

    Test Steps:
        Clean up any existing parameters and prepare configuration files.
        Add audit-policy-file parameter and apply to Kubernetes.
        Assert out-of-date alarm is present at hosts.
        Apply Kubernetes service parameters and wait for stabilization.
        Verify the new configuration is applied.
        Apply host-swact between controllers.
        Verify the synced configuration between controllers.
        Delete parameters and verify deletion was successful.
        Apply Kubernetes service parameters after deletion.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Cleaning up existing parameters and preparing files")
    cleanup_parameters_and_files(ssh_connection, parameter_turn_on_audit_policy_logs_list(), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Uploading eventconfig.yaml")
    upload_file_with_sudo(ssh_connection, get_stx_resource_path(AUDIT_POLICY_LOGS_LOCAL_FILE_PATH), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Adding audit-policy-file parameter")
    for param in parameter_turn_on_audit_policy_logs_list():
        SystemServiceKeywords(ssh_connection).add_service_parameter(service=param.service, parameter=f"{param.section} {param.name}", value=param.value)

    get_logger().log_test_case_step("Asserting out-of-date alarm is present at hosts")
    validate_equals(AlarmListKeywords(ssh_connection).is_alarm_present("250.001"), True, "Out-of-date alarm 250.001 should be present")

    get_logger().log_test_case_step("Applying parameters for Kubernetes")
    SystemServiceKeywords(ssh_connection).apply_kubernetes_service_parameters()

    get_logger().log_test_case_step("Verifying the new configuration is applied")
    verify_parameters_applied(ssh_connection, parameter_turn_on_audit_policy_logs_list())

    get_logger().log_test_case_step("Applying host-swact between controllers")
    SystemHostSwactKeywords(ssh_connection).host_swact()

    get_logger().log_test_case_step("Verifying the synced configuration between controllers")
    verify_parameters_applied(ssh_connection, parameter_turn_on_audit_policy_logs_list())

    get_logger().log_test_case_step("Deleting parameters")
    delete_parameters_and_files(ssh_connection, parameter_turn_on_audit_policy_logs_list(), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Applying parameters for Kubernetes after deletion")
    SystemServiceKeywords(ssh_connection).apply_kubernetes_service_parameters()
    verify_parameters_deleted(ssh_connection, parameter_turn_on_audit_policy_logs_list())

    get_logger().log_info("Custom k8s configuration tests passed")
