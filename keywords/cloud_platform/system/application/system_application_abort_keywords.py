from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SystemApplicationAbortKeywords(BaseKeyword):
    """
    Class for System application abort keywords

    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSHConnection
        """
        self.ssh_connection = ssh_connection

    def system_application_apply_and_abort(self, app_name: str, force_abort: bool = False):
        """
        Abort an application.

        Args:
            app_name (str): application name
            force_abort (bool): whether to force the abort operation
        """
        # Some app apply very fast, so need to run apply && abort CMDs closely follow
        get_logger().log_info(f"Run system application apply && abort {app_name}")
        app_apply_cmd = f"system application-apply {app_name}"

        force_param = "-f" if force_abort else ""
        app_abort_cmd = f"system application-abort {force_param} {app_name}".strip()
        self.ssh_connection.send(source_openrc(f"{app_apply_cmd} && {app_abort_cmd}"))
        self.validate_success_return_code(self.ssh_connection)

    def system_application_abort(self, app_name: str, force_abort: bool = False):
        """
        Abort an application.

        Args:
            app_name (str): application name
            force_abort (bool): whether to force the abort operation
        """
        get_logger().log_info(f"Run system application abort {app_name}")
        force_param = "-f" if force_abort else ""
        app_abort_cmd = f"system application-abort {force_param} {app_name}".strip()
        self.ssh_connection.send(source_openrc(f"{app_abort_cmd}"))
        self.validate_success_return_code(self.ssh_connection)
