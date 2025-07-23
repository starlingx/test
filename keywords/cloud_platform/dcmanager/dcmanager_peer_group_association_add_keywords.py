from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class DcManagerPeerGroupAssociationAddKeywords(BaseKeyword):
    """Keywords for 'dcmanager peer-group-association add' command.

    In geo-redundancy, peer_group_priority is optional and helps indicate the preferred destination site during subcloud rehoming
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keyword class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_peer_group_association_add(
        self,
        peer_group_id: int,
        system_peer_id: int,
        peer_group_priority: Optional[int] = None,
    ) -> None:
        """Add a peer group association using 'dcmanager peer-group-association add' command.

        Args:
            peer_group_id (int): ID of the peer group to associate.
            system_peer_id (int): ID of the system peer to associate.
            peer_group_priority (Optional[int], optional): Priority of the peer group association.
                If None, the priority is not set.
        """
        cmd_parts = [
            "dcmanager peer-group-association add",
            f"--peer-group-id {peer_group_id}",
            f"--system-peer-id {system_peer_id}",
        ]

        if peer_group_priority is not None:
            cmd_parts.append(f"--peer-group-priority {peer_group_priority}")

        cmd = " ".join(cmd_parts)
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
