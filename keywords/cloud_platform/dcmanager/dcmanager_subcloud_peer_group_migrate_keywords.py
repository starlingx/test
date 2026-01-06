from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_peer_group_list_subclouds_output import DcManagerSubcloudPeerGroupListSubcloudsOutput


class DcManagerSubcloudPeerGroupMigrateKeywords(BaseKeyword):
    """Keywords for 'dcmanager subcloud-peer-group migrate' command."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_peer_group_migrate(self, identifier: str, password: str) -> DcManagerSubcloudPeerGroupListSubcloudsOutput:
        """Migrate a subcloud peer group using subcloud peer group migrate

        Args:
            identifier (str): Subcloud peer group identifier (id).
            password (str): Password for authentication.

        Returns:
            DcManagerSubcloudPeerGroupListSubcloudsOutput: Output of subcloud peer group migrated
        """
        cmd = f"dcmanager subcloud-peer-group migrate {identifier} --sysadmin-password {password}"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return DcManagerSubcloudPeerGroupListSubcloudsOutput(output)
