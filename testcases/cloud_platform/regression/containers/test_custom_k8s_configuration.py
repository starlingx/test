from os.path import basename

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_none, validate_not_none
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.service.objects.system_service_parameter_list_output import SystemServiceParameterListOutput
from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
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


def volume_for_kube_api_server_list() -> list[SystemServiceParameterObject]:
    """Returns the list of SystemServiceParameterObject for VolumeForKubeAPIServer.

    Returns:
        list[SystemServiceParameterObject]: List of SystemServiceParameterObject.
    """
    return [
        SystemServiceParameterObject(
            service="kubernetes",
            section="kube_apiserver_volumes",
            name="eventconfig",
            value="hostPath:/etc/kubernetes/eventconfig.yaml",
        ),
        SystemServiceParameterObject(
            service="kubernetes",
            section="kube_apiserver_volumes",
            name="admission-control-config",
            value="hostPath:/etc/kubernetes/admission-control-config-file.yaml",
        ),
        SystemServiceParameterObject(
            service="kubernetes",
            section="kube_apiserver",
            name="admission-control-config-file",
            value="/etc/kubernetes/admission-control-config-file.yaml",
        ),
        SystemServiceParameterObject(
            service="kubernetes",
            section="kube_apiserver",
            name="enable-admission-plugins",
            value="EventRateLimit",
        ),
    ]


def parameter_turn_on_audit_policy_logs_list() -> list[SystemServiceParameterObject]:
    """Returns the list of SystemServiceParameterObject for TurnOnAuditPolicyLogs.

    Returns:
        list[SystemServiceParameterObject]: List of SystemServiceParameterObject.
    """
    return [
        SystemServiceParameterObject(
            service="kubernetes",
            section="kube_apiserver",
            name="audit-policy-file",
            value="/etc/kubernetes/eventconfig.yaml",
        ),
    ]


def verify_parameters_applied(ssh_connection: SSHConnection, parameters: list[SystemServiceParameterObject]):
    """Verify if the service parameters were applied correctly.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
        parameters (list[SystemServiceParameterObject]): List of expected parameters.
    """
    system_service_list: SystemServiceParameterListOutput = SystemServiceParameterKeywords(ssh_connection).list_service_parameters()
    for system_service_parameter in parameters:
        get_logger().log_test_case_step(f"Asserting parameter {system_service_parameter.get_section()} {system_service_parameter.get_name()} is listed")
        parameter_found = next(
            (param for param in system_service_list.get_parameters() if param.get_service() == system_service_parameter.get_service() and param.get_section() == system_service_parameter.get_section() and param.get_name() == system_service_parameter.get_name() and param.get_value() == system_service_parameter.get_value()),
            None,
        )
        validate_not_none(parameter_found, f"Parameter {system_service_parameter.get_section()} {system_service_parameter.get_name()} should be present")


def verify_parameters_deleted(ssh_connection: SSHConnection, parameters: list[SystemServiceParameterObject]):
    """Verify if the service parameters were deleted correctly.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
        parameters (list[SystemServiceParameterObject]): List of parameters to verify deletion.
    """
    system_service_list: SystemServiceParameterListOutput = SystemServiceParameterKeywords(ssh_connection).list_service_parameters()
    for system_service_parameter in parameters:
        get_logger().log_test_case_step(f"Asserting parameter {system_service_parameter.get_section()} {system_service_parameter.get_name()} is deleted")
        parameter_found = next(
            (param for param in system_service_list.get_parameters() if param.get_service() == system_service_parameter.get_service() and param.get_section() == system_service_parameter.get_section() and param.get_name() == system_service_parameter.get_name() and param.get_value() == system_service_parameter.get_value()),
            None,
        )
        validate_none(parameter_found, f"Parameter {system_service_parameter.get_section()} {system_service_parameter.get_name()} should be deleted")


def delete_parameters_and_files(ssh_connection: SSHConnection, parameters: list[SystemServiceParameterObject], remote_file_path: str):
    """Delete service parameters and associated remote files.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
        parameters (list[SystemServiceParameterObject]): List of parameters to delete.
        remote_file_path (str): Remote file path to delete.
    """
    get_logger().log_test_case_step("Deleting service parameters")
    service_param_keywords = SystemServiceParameterKeywords(ssh_connection)
    all_params: SystemServiceParameterListOutput = service_param_keywords.list_service_parameters()
    for param in parameters:
        match = next(
            (p for p in all_params.get_parameters() if p.get_service() == param.get_service() and p.get_section() == param.get_section() and p.get_name() == param.get_name()),
            None,
        )
        if match:
            service_param_keywords.delete_service_parameter(match.get_uuid())
    file_keywords = FileKeywords(ssh_connection)
    get_logger().log_test_case_step(f"Deleting remote file {remote_file_path}")
    file_keywords.delete_file(remote_file_path)
    validate_equals(file_keywords.file_exists(remote_file_path), False, f"File {remote_file_path} should be deleted")


def cleanup_parameters_and_files(ssh_connection: SSHConnection, parameters: list[SystemServiceParameterObject], remote_file_path: str):
    """Clean up service parameters and associated remote files, ignoring already deleted ones.

    Args:
        ssh_connection (SSHConnection): SSH connection object.
        parameters (list[SystemServiceParameterObject]): List of parameters to clean up.
        remote_file_path (str): Remote file path to delete.
    """
    get_logger().log_test_case_step("Cleaning up service parameters")
    service_param_keywords = SystemServiceParameterKeywords(ssh_connection)
    all_params: SystemServiceParameterListOutput = service_param_keywords.list_service_parameters()
    for param in parameters:
        match = next(
            (p for p in all_params.get_parameters() if p.get_service() == param.get_service() and p.get_section() == param.get_section() and p.get_name() == param.get_name()),
            None,
        )
        if match:
            service_param_keywords.delete_service_parameter(match.get_uuid())
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
        SystemServiceParameterKeywords(ssh_connection).add_service_parameter(service=param.get_service(), section=param.get_section(), parameter_name=param.get_name(), parameter_value=param.get_value())

    get_logger().log_test_case_step("Asserting out-of-date alarm is present at hosts")
    validate_equals(AlarmListKeywords(ssh_connection).is_alarm_present("250.001"), True, "Out-of-date alarm 250.001 should be present")

    get_logger().log_test_case_step("Applying parameters for Kubernetes")
    SystemServiceParameterKeywords(ssh_connection).apply_service_parameters("kubernetes")

    get_logger().log_test_case_step("Verifying the new configuration is applied")
    verify_parameters_applied(ssh_connection, volume_for_kube_api_server_list())

    get_logger().log_test_case_step("Deleting parameters")
    delete_parameters_and_files(ssh_connection, volume_for_kube_api_server_list(), VOLUME_FOR_KUBE_API_SERVER_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Deleting eventconfig.yaml")
    FileKeywords(ssh_connection).delete_file(AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Applying parameters for Kubernetes after deletion")
    SystemServiceParameterKeywords(ssh_connection).apply_service_parameters("kubernetes")
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
        SystemServiceParameterKeywords(ssh_connection).add_service_parameter(service=param.get_service(), section=param.get_section(), parameter_name=param.get_name(), parameter_value=param.get_value())

    get_logger().log_test_case_step("Asserting out-of-date alarm is present at hosts")
    validate_equals(AlarmListKeywords(ssh_connection).is_alarm_present("250.001"), True, "Out-of-date alarm 250.001 should be present")

    get_logger().log_test_case_step("Applying parameters for Kubernetes")
    SystemServiceParameterKeywords(ssh_connection).apply_service_parameters("kubernetes")

    get_logger().log_test_case_step("Verifying the new configuration is applied")
    verify_parameters_applied(ssh_connection, parameter_turn_on_audit_policy_logs_list())

    get_logger().log_test_case_step("Deleting parameters")
    delete_parameters_and_files(ssh_connection, parameter_turn_on_audit_policy_logs_list(), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Applying parameters for Kubernetes after deletion")
    SystemServiceParameterKeywords(ssh_connection).apply_service_parameters("kubernetes")
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
        SystemServiceParameterKeywords(ssh_connection).add_service_parameter(service=param.get_service(), section=param.get_section(), parameter_name=param.get_name(), parameter_value=param.get_value())

    get_logger().log_test_case_step("Asserting out-of-date alarm is present at hosts")
    validate_equals(AlarmListKeywords(ssh_connection).is_alarm_present("250.001"), True, "Out-of-date alarm 250.001 should be present")

    get_logger().log_test_case_step("Applying parameters for Kubernetes")
    SystemServiceParameterKeywords(ssh_connection).apply_service_parameters("kubernetes")

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
    SystemServiceParameterKeywords(ssh_connection).apply_service_parameters("kubernetes")
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
        SystemServiceParameterKeywords(ssh_connection).add_service_parameter(service=param.get_service(), section=param.get_section(), parameter_name=param.get_name(), parameter_value=param.get_value())

    get_logger().log_test_case_step("Asserting out-of-date alarm is present at hosts")
    validate_equals(AlarmListKeywords(ssh_connection).is_alarm_present("250.001"), True, "Out-of-date alarm 250.001 should be present")

    get_logger().log_test_case_step("Applying parameters for Kubernetes")
    SystemServiceParameterKeywords(ssh_connection).apply_service_parameters("kubernetes")

    get_logger().log_test_case_step("Verifying the new configuration is applied")
    verify_parameters_applied(ssh_connection, parameter_turn_on_audit_policy_logs_list())

    get_logger().log_test_case_step("Applying host-swact between controllers")
    SystemHostSwactKeywords(ssh_connection).host_swact()

    get_logger().log_test_case_step("Verifying the synced configuration between controllers")
    verify_parameters_applied(ssh_connection, parameter_turn_on_audit_policy_logs_list())

    get_logger().log_test_case_step("Deleting parameters")
    delete_parameters_and_files(ssh_connection, parameter_turn_on_audit_policy_logs_list(), AUDIT_POLICY_LOGS_REMOTE_FILE_PATH)

    get_logger().log_test_case_step("Applying parameters for Kubernetes after deletion")
    SystemServiceParameterKeywords(ssh_connection).apply_service_parameters("kubernetes")
    verify_parameters_deleted(ssh_connection, parameter_turn_on_audit_policy_logs_list())

    get_logger().log_info("Custom k8s configuration tests passed")
