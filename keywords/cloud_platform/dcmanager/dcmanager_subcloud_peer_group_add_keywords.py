from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class DcManagerSubcloudPeerGroupAddKeywords(BaseKeyword):
    """Keywords for 'dcmanager subcloud-peer-group add' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_peer_group_add(
        self,
        peer_group_name: str,
        group_priority: Optional[int] = None,
        group_description: Optional[str] = None,
        max_subclouds: Optional[int] = None,
    ) -> None:
        """Add a subcloud peer group using 'dcmanager subcloud-peer-group add' command.

        Args:
            peer_group_name (str): Name of the peer group.
            group_priority (Optional[int]): Priority level of the peer group.
            group_description (Optional[str]): Description of the peer group.
            max_subclouds (Optional[int]): Maximum number of subclouds per group.
        """
        cmd_parts = [
            "dcmanager subcloud-peer-group add",
            f"--peer-group-name {peer_group_name}",
        ]
        if group_description:
            cmd_parts.append(f"--group-priority '{group_priority}'")

        if group_description:
            cmd_parts.append(f"--group-description '{group_description}'")

        if max_subclouds is not None:
            cmd_parts.append(f"--max-subclouds {max_subclouds}")

        cmd = " ".join(cmd_parts)
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
