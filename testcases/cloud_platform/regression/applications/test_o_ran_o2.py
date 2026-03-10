from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import (
    SystemApplicationUploadKeywords,
)
from keywords.cloud_platform.system.application.system_application_remove_keywords import (
    SystemApplicationRemoveKeywords,
)
from keywords.cloud_platform.system.application.system_application_delete_keywords import (
    SystemApplicationDeleteKeywords,
)
from keywords.cloud_platform.system.application.object.system_application_upload_input import (
    SystemApplicationUploadInput,
)
from keywords.cloud_platform.system.application.object.system_application_remove_input import (
    SystemApplicationRemoveInput,
)
from keywords.cloud_platform.system.application.object.system_application_delete_input import (
    SystemApplicationDeleteInput,
)
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.linux.ls.ls_keywords import LsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.cloud_platform.applications.o_ran_o2_keywords import OranO2Keywords


def upload_o_ran(ssh_connection: SSHConnection):
    """Upload O-RAN O2 application.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    logger = get_logger()
    logger.log_info("Uploading oran-o2 application")
    ls_keywords = LsKeywords(ssh_connection)
    tar_file_path = ls_keywords.get_first_matching_file('/usr/local/share/applications/helm/*oran*')
    upload_keywords = SystemApplicationUploadKeywords(ssh_connection)
    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name("oran-o2")
    upload_input.set_tar_file_path(tar_file_path)
    upload_input.set_force(True)
    upload_keywords.system_application_upload(upload_input)
    logger.log_info('O-RAN app uploaded successfully')


def uninstall_o_ran(ssh_connection: SSHConnection):
    """Uninstall O-RAN O2 application.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    logger = get_logger()
    logger.log_info("Uninstalling oran-o2 application")
    remove_keywords = SystemApplicationRemoveKeywords(ssh_connection)
    remove_input = SystemApplicationRemoveInput()
    remove_input.set_app_name("oran-o2")
    remove_input.set_force_removal(True)
    remove_keywords.system_application_remove(remove_input)
    delete_keywords = SystemApplicationDeleteKeywords(ssh_connection)
    delete_input = SystemApplicationDeleteInput()
    delete_input.set_app_name("oran-o2")
    delete_input.set_force_deletion(True)
    delete_keywords.get_system_application_delete(delete_input)


def delete_o_ran_config_files(ssh_connection: SSHConnection):
    """Delete O-RAN O2 configuration files.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    logger = get_logger()
    logger.log_info("Deleting O-RAN O2 configuration files")
    kubectl_delete = KubectlFileDeleteKeywords(ssh_connection)
    kubectl_delete.delete_resources('/tmp/smo-secret.yaml', ignore_not_found=True)
    kubectl_delete.delete_resources('/tmp/smo-serviceaccount.yaml', ignore_not_found=True)
    logger.log_info("Delete all O-RAN O2 config files")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.delete_file("/tmp/app.conf")
    file_keywords.delete_file("/tmp/smo-serviceaccount.yaml")
    file_keywords.delete_file("/tmp/smo-secret.yaml")
    file_keywords.delete_file("/tmp/o2service-override.yaml")
    file_keywords.delete_directory("/tmp/cert")
    logger.log_info('Delete files successfully')


def create_smo_secret(
    ssh_connection: SSHConnection, smo_secret: str = 'smo1-secret', smo_service_account: str = 'smo1'
):
    """Create SMO secret.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        smo_secret (str): Name of the SMO secret. Defaults to 'smo1-secret'.
        smo_service_account (str): Name of the SMO service account. Defaults to 'smo1'.
    """
    logger = get_logger()
    logger.log_info("Creating SMO secret")
    OranO2Keywords(ssh_connection).create_smo_secret(smo_secret, smo_service_account)
    smo_token_data = KubectlGetSecretsKeywords(ssh_connection).get_secret_with_custom_output(
        smo_secret, "default", "jsonpath", "'{.data.token}'", base64=True
    )



@mark.p0
def test_o_ran_apply():
    """Test O-RAN O2 application deployment and configuration.

    Steps:
        - Upload O-RAN O2 application
        - Create SMO service account
        - Create SMO secret
        - Generate certificates for O2 service
        - Prepare O2 service application configuration file
        - Update overrides for oran-o2 application and apply
        - Uninstall O-RAN app
        - Delete O-RAN config files
    """
    logger = get_logger()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_test_case_step("Upload O-RAN O2 application")
    upload_o_ran(ssh_connection)

    logger.log_test_case_step("Create SMO service account and secret")
    OranO2Keywords(ssh_connection).create_smo_service_account()
    create_smo_secret(ssh_connection)

    logger.log_test_case_step("Generate certificates for O2 service")
    OranO2Keywords(ssh_connection).create_certificates()

    logger.log_test_case_step("Prepare O2 service application configuration file")
    OranO2Keywords(ssh_connection).create_app_config_file("http://127.0.0.1")

    logger.log_test_case_step("Update overrides for oran-o2 application and apply")
    OranO2Keywords(ssh_connection).apply_helm_override()

    logger.log_test_case_step("Uninstall O-RAN application")
    uninstall_o_ran(ssh_connection)

    logger.log_test_case_step("Delete O-RAN config files")
    delete_o_ran_config_files(ssh_connection)
