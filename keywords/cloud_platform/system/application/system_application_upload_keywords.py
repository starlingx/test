from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_list_status_tracking_input import SystemApplicationListStatusTrackingInput
from keywords.cloud_platform.system.application.object.system_application_output import SystemApplicationOutput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.python.string import String


class SystemApplicationUploadKeywords(BaseKeyword):
    """
    Class for System application keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:

        """
        self.ssh_connection = ssh_connection

    def system_application_upload(self, system_application_upload_input: SystemApplicationUploadInput) -> SystemApplicationOutput:
        """
        Executes the upload of an application file by executing the command 'system application-upload'. This method
        returns upon the completion of the 'system application-upload' command, that is, when the 'status' is 'uploaded'.
        Args:
            system_application_upload_input (SystemApplicationUploadInput): the object representing the parameters for
            executing the 'system application-upload' command.

        Returns:
            SystemApplicationOutput: an object representing status values related to the current uploading process of
            the application, as a result of the execution of the 'system application-upload' command.

        """
        # Gets the command 'system application-upload' with its parameters configured.
        cmd = self.get_command(system_application_upload_input)
        app_name = system_application_upload_input.get_app_name()

        # If the upload must be forced, checks if the applications is applied/apply-failed/uploaded/upload-failed and remove/delete it, if so.
        if system_application_upload_input.get_force():
            if SystemApplicationApplyKeywords(self.ssh_connection).is_applied_or_failed(app_name):
                system_application_remove_input = SystemApplicationRemoveInput()
                system_application_remove_input.set_force_removal(True)
                system_application_remove_input.set_app_name(app_name)
                SystemApplicationRemoveKeywords(self.ssh_connection).system_application_remove(system_application_remove_input)
            if self.is_already_uploaded(app_name):
                system_application_delete_input = SystemApplicationDeleteInput()
                system_application_delete_input.set_force_deletion(True)
                system_application_delete_input.set_app_name(app_name)
                SystemApplicationDeleteKeywords(self.ssh_connection).get_system_application_delete(system_application_delete_input)

        # Executes the command 'system application-upload'.
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        system_application_output = SystemApplicationOutput(output)

        # Tracks the execution of the command 'system application-upload' until its completion or a timeout.
        system_application_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
        system_application_list_keywords.validate_app_status(app_name, SystemApplicationStatusEnum.UPLOADED.value)

        # If the execution arrived here the status of the application is 'uploaded'.
        system_application_output.get_system_application_object().set_status(SystemApplicationStatusEnum.UPLOADED.value)

        return system_application_output

    def is_already_uploaded(self, app_name: str) -> bool:
        """
        Verifies if the application has already been uploaded.
        Args:
            app_name (str): a string representing the name of the application.

        Returns:
            bool: True if the application named 'app_name' has already been uploaded; False otherwise.

        Note:
            If the application in the host is in the 'applied' status, this method will also return True.

        """
        try:
            system_application_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
            if system_application_list_keywords.get_system_application_list().is_in_application_list(app_name):
                application = SystemApplicationListKeywords(self.ssh_connection).get_system_application_list().get_application(app_name)
                return (
                    application.get_status() == SystemApplicationStatusEnum.UPLOADED.value
                    or application.get_status() == SystemApplicationStatusEnum.UPLOAD_FAILED.value
                )
            return False
        except Exception as ex:
            get_logger().log_exception(f"An error occurred while verifying whether the application named {app_name} is already uploaded.")
            raise ex

    def get_command(self, system_application_upload_input: SystemApplicationUploadInput) -> str:
        """
        Generates a string representing the 'system application-upload' command with parameters based on the values in
        the 'system_application_upload_input' argument.
        Args:
            system_application_upload_input (SystemApplicationUploadInput): an instance of SystemApplicationUploadInput
            configured with the parameters needed to execute the 'system application-upload' command properly.

        Returns:
            str: a string representing the 'system application-upload' command, configured according to the parameters
            in the 'system_application_upload_input' argument.

        """
        # 'tar_file_path' property is required.
        tar_file_path = system_application_upload_input.get_tar_file_path()
        if String.is_empty(tar_file_path):
            error_message = "The tar_file_path property must be specified."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        # 'app_name' property is optional.
        app_name_as_param = ''
        if not String.is_empty(system_application_upload_input.get_app_name()):
            app_name_as_param = f'-n {system_application_upload_input.get_app_name()}'

        # 'app_version' property is optional.
        app_version_as_param = ''
        if system_application_upload_input.get_app_version() is not None:
            app_version_as_param = f'-v {system_application_upload_input.get_app_version()}'

        # 'automatic_installation' property is optional.
        automatic_installation_as_param = ''
        if system_application_upload_input.get_automatic_installation():
            automatic_installation_as_param = '-i'

        # Assembles the command.
        cmd = f'system application-upload {app_name_as_param} {app_version_as_param} {automatic_installation_as_param} {tar_file_path}'

        return cmd
