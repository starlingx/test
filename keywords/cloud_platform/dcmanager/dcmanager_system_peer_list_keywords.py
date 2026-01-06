from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_system_peer_list_output import DcManagerSystemPeerListOutput


class DcManagerSystemPeerListKeywords(BaseKeyword):
    """This class contains all the keywords related to the 'dcmanager system peer list' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_system_peer_list(self) -> DcManagerSystemPeerListOutput:
        """Gets the 'dcmanager system peer list' output.

        Returns:
            DcManagerSystemPeerListOutput: a DcManagerSystemPeerListOutput object representing
            the output of the command 'dcmanager system peer list'.

        """
        output = self.ssh_connection.send(source_openrc("dcmanager system-peer list"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_system_peer_list_output = DcManagerSystemPeerListOutput(output)

        return dcmanager_system_peer_list_output
