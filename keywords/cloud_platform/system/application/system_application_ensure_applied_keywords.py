"""Keywords for making sure a platform application is applied."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords

DEFAULT_APPLY_TIMEOUT_SECONDS = 600


class SystemApplicationEnsureAppliedKeywords(BaseKeyword):
    """Keywords that upload and apply a platform application only when it is not applied yet."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize the keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def ensure_application_applied(self, app_name: str, tar_file_path: str, timeout: int = DEFAULT_APPLY_TIMEOUT_SECONDS) -> None:
        """Make sure an application is applied, uploading and applying it when needed.

        An applied application is left untouched, an uploaded one is applied, and an absent
        one is uploaded from the tarball and applied. The apply keyword waits for the
        applied state and fails on apply-failed.

        Args:
            app_name (str): The application name (e.g. 'metrics-server').
            tar_file_path (str): The application tarball on the controller, used when it is not uploaded yet.
            timeout (int): Seconds to wait for the applied state.
        """
        apply_keywords = SystemApplicationApplyKeywords(self.ssh_connection)
        if apply_keywords.is_already_applied(app_name):
            get_logger().log_info(f"Application {app_name} is already applied")
            return

        if not SystemApplicationListKeywords(self.ssh_connection).is_app_present(app_name):
            get_logger().log_info(f"Uploading application {app_name} from {tar_file_path}")
            upload_input = SystemApplicationUploadInput()
            upload_input.set_app_name(app_name)
            upload_input.set_tar_file_path(tar_file_path)
            SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload(upload_input)

        get_logger().log_info(f"Applying application {app_name}")
        apply_keywords.system_application_apply(app_name, timeout=timeout)
