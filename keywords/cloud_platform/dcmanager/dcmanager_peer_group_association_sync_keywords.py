from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_peer_group_association_sync_output import DcManagerPeerGroupAssociationSyncOutput


class DcManagerPeerGroupAssociationSyncKeywords(BaseKeyword):
    """Keywords for 'dcmanager peer-group-association sync' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_peer_group_association_sync(self, association_id: int) -> DcManagerPeerGroupAssociationSyncOutput:
        """Synchronize peer group associations using 'dcmanager peer-group-association sync' command.

        Args:
            association_id (int): ID of the peer group association to synchronize.

        Returns:
            DcManagerPeerGroupAssociationSyncOutput: Output of the 'dcmanager peer-group-association sync' command.
        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager peer-group-association sync {association_id}"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_peer_group_association_sync_output = DcManagerPeerGroupAssociationSyncOutput(output)

        return dcmanager_peer_group_association_sync_output
