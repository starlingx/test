from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_group_list_subcloud_output import (
    DcmanagerSubcloudGroupListSubcloudOutput,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_group_output import (
    DcmanagerSubcloudGroupOutput,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_group_show_output import (
    DcmanagerSubcloudGroupShowOutput,
)


class DcmanagerSubcloudGroupKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud-group' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initializes DcmanagerSubcloudGroupKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_group_list(self) -> DcmanagerSubcloudGroupOutput:
        """
        Gets the dcmanager subcloud-group list.

        Returns:
            DcmanagerSubcloudGroupOutput: An object containing the list of subcloud groups.
        """
        command = source_openrc("dcmanager subcloud-group list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerSubcloudGroupOutput(output)

    def get_dcmanager_subcloud_group_show(self, group_id: str) -> DcmanagerSubcloudGroupShowOutput:
        """
        Gets the dcmanager subcloud-group details for a specific group.

        Args:
            group_id (str): The identifier of the subcloud group.

        Returns:
            DcmanagerSubcloudGroupShowOutput: An object containing details of the subcloud group.
        """
        command = source_openrc(f"dcmanager subcloud-group show {group_id}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerSubcloudGroupShowOutput(output)

    def dcmanager_subcloud_group_add(self, group_name: str) -> DcmanagerSubcloudGroupShowOutput:
        """
        Creates a dcmanager subcloud-group with the name provided.

        Args:
            group_name (str): The identifier of the subcloud group.

        Returns:
            DcmanagerSubcloudGroupShowOutput: An object containing details of the newly created subcloud group.
        """
        command = source_openrc(f"dcmanager subcloud-group add --name {group_name}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerSubcloudGroupShowOutput(output)

    def dcmanager_subcloud_group_delete(self, group_name: str) -> None:
        """
        Deletes the dcmanager subcloud-group with the name provided.

        Args:
            group_name (str): The identifier of the subcloud group.

        Returns:
            None: This method does not return a value.
        """
        command = source_openrc(f"dcmanager subcloud-group delete {group_name}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def dcmanager_subcloud_group_update(self, group_name: str, update_attr: str, update_value: str) -> DcmanagerSubcloudGroupShowOutput:
        """
        Updates the subcloud-group attr using 'dcmanager subcloud-group update <subcloud-group name> --<update_attr> <update_value>' output.

        Args:
            group_name (str): a str representing a subcloud-group's name.
            update_attr (str): the attribute to update (ex. description)
            update_value (str): the value to update the attribute to (ex. this is a new description)

        Returns:
            DcmanagerSubcloudGroupShowOutput: An object containing details of the newly created subcloud group.
        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager subcloud-group update {group_name} --{update_attr} '{update_value}'"))
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerSubcloudGroupShowOutput(output)

    def get_dcmanager_subcloud_group_list_subclouds(self, group_id: str) -> DcmanagerSubcloudGroupListSubcloudOutput:
        """
        Gets the dcmanager subcloud-group list-subclouds.

        Args:
            group_id (str): a str representing a subcloud-group's id.

        Returns:
            DcmanagerSubcloudGroupListSubcloudOutput: An object containing the list of subcloud groups.
        """
        command = source_openrc(f"dcmanager subcloud-group list-subclouds {group_id}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerSubcloudGroupListSubcloudOutput(output)
