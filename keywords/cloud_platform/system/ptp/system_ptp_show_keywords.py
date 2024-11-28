from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ptp.objects.system_ptp_show_output import SystemPTPShowOutput


class SystemPTPShowKeywords(BaseKeyword):
    """
    Provides methods to interact with the system host filesystem
    using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the SystemPTPShowKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def system_ptp_show(self) -> SystemPTPShowOutput:
        """
        Retrieves information about a ptp on a host.

        Returns:
            SystemPTPShowOutput: Output object containing details about ptp.

        Raises:
            KeywordException: If the parsed output is invalid or missing required fields.
        """
        command = source_openrc(f'system ptp-show')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_output = SystemPTPShowOutput(output)
        return system_ptp_output
