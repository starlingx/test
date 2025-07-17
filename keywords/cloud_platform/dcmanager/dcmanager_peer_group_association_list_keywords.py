from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_peer_group_association_list_output import DcManagerPeerGroupAssociationListOutput


class DcManagerPeerGroupAssociationListKeywords(BaseKeyword):
    """This class contains all the keywords related to the 'dcmanager peer group association list' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_peer_group_association_list(self) -> DcManagerPeerGroupAssociationListOutput:
        """Gets the 'dcmanager peer group association list' output.

        Returns:
            DcManagerPeerGroupAssociationListOutput: a DcManagerPeerGroupAssociationListOutput object representing
            the output of the command 'dcmanager peer group association list'.
        """
        output = self.ssh_connection.send(source_openrc("dcmanager peer-group-association list"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_peer_group_association_list_output = DcManagerPeerGroupAssociationListOutput(output)

        return dcmanager_peer_group_association_list_output
