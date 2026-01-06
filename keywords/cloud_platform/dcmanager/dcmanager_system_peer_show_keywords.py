from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_system_peer_show_output import DcManagerSystemPeerShowOutput


class DcManagerSystemPeerShowKeywords(BaseKeyword):
    """This class contains all the keywords related to the 'dcmanager system peer show' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_system_peer_show(self, peer_id: str) -> DcManagerSystemPeerShowOutput:
        """Gets the 'dcmanager system peer show' output.

        Args:
            peer_id (str): The peer ID to show details for

        Returns:
            DcManagerSystemPeerShowOutput: a DcManagerSystemPeerShowOutput object representing
            the output of the command 'dcmanager system peer show'.

        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager system-peer show {peer_id}"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_system_peer_show_output = DcManagerSystemPeerShowOutput(output)

        return dcmanager_system_peer_show_output
