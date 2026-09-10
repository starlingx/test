from typing import List, Tuple

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_group_list_subcloud_output import (
    DcmanagerSubcloudGroupListSubcloudOutput,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_group_output import (
    DcmanagerSubcloudGroupOutput,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_group_show_output import (
    DcmanagerSubcloudGroupShowOutput,
)
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords, pick_subcloud_with_fallback

DEFAULT_GROUP_NAME = "Default"


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

    def dcmanager_subcloud_group_add_with_subclouds(self, group_name: str, subcloud_names: List[str]) -> None:
        """Add a subcloud group and assign the given subclouds to it.

        Args:
            group_name (str): Name of the group to create.
            subcloud_names (List[str]): Subclouds to assign to the group.
        """
        get_logger().log_info(f"Create subcloud group '{group_name}'")
        self.dcmanager_subcloud_group_add(group_name=group_name)

        for subcloud_name in subcloud_names:
            get_logger().log_info(f"Assign subcloud '{subcloud_name}' to group '{group_name}'")
            DcManagerSubcloudUpdateKeywords(self.ssh_connection).dcmanager_subcloud_update(subcloud_name=subcloud_name, update_attr="group", update_value=group_name)

        assigned = sorted([sc.get_name() for sc in self.get_dcmanager_subcloud_group_list_subclouds(group_name).get_dcmanager_subcloud_group_list_subclouds()])
        validate_equals(assigned, sorted(subcloud_names), f"Subclouds assigned to group '{group_name}'")

    def dcmanager_subcloud_group_delete_and_reset(self, group_name: str, subcloud_names: List[str]) -> None:
        """Reset subclouds to the Default group and delete the given group.

        Args:
            group_name (str): Name of the group to delete.
            subcloud_names (List[str]): Subclouds to move back to the Default group.
        """
        for subcloud_name in subcloud_names:
            get_logger().log_teardown_step(f"Reset subcloud '{subcloud_name}' to '{DEFAULT_GROUP_NAME}' group")
            DcManagerSubcloudUpdateKeywords(self.ssh_connection).dcmanager_subcloud_update(subcloud_name=subcloud_name, update_attr="group", update_value=DEFAULT_GROUP_NAME)

        get_logger().log_teardown_step(f"Delete subcloud group '{group_name}'")
        self.dcmanager_subcloud_group_delete(group_name)

    @staticmethod
    def dcmanager_subcloud_group_build_from_load(load: str, group_name: str) -> Tuple[SSHConnection, List[str]]:
        """Select online subclouds matching a load and create a group from them.

        Picks all online subclouds running the given load (with secondary system
        controller fallback), then creates the group and assigns those members.

        Args:
            load (str): Software version filter ("N", "N-1", "N-2").
            group_name (str): Name of the group to create.

        Returns:
            Tuple[SSHConnection, List[str]]: The system controller SSH connection
                owning the members and the sorted member subcloud names.
        """
        system_controller_ssh, _ = pick_subcloud_with_fallback(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load=load)
        members = sorted([result.get_name() for result in SubcloudPickerKeywords(system_controller_ssh).pick_all(availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, load=load)])
        DcmanagerSubcloudGroupKeywords(system_controller_ssh).dcmanager_subcloud_group_add_with_subclouds(group_name, members)
        return system_controller_ssh, members
