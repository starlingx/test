from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_peer_group_list_object import DcManagerSubcloudPeerGroupListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class DcManagerSubcloudPeerGroupListOutput:
    """Parses the output of 'dcmanager subcloud-peer-group list' command."""

    def __init__(self, peer_group_list_output: str):
        """Initialize and parse the peer group list output.

        Args:
            peer_group_list_output (str): Raw output from command.
        """
        self.peer_group_list: List[DcManagerSubcloudPeerGroupListObject] = []
        system_table_parser = SystemTableParser(peer_group_list_output)
        self.output_values = system_table_parser.get_output_values_list()
        for value in self.output_values:
            if not self.is_valid_output(value):
                raise KeywordException(f"The output line {value} was not valid")
            peer_group_object = DcManagerSubcloudPeerGroupListObject(
                value.get("id"),
                value.get("peer_group_name"),
                value.get("group_priority"),
                value.get("group_state"),
                value.get("system_leader_id"),
                value.get("system_leader_name"),
                value.get("max_subcloud_rehoming"),
            )
            self.peer_group_list.append(peer_group_object)

    def get_peer_group_list(self) -> List[DcManagerSubcloudPeerGroupListObject]:
        """Get all peer group objects.

        Returns:
            List[DcManagerSubcloudPeerGroupListObject]: List of peer group objects.
        """
        return self.peer_group_list

    def get_peer_group_by_name(self, group_name: str) -> DcManagerSubcloudPeerGroupListObject:
        """Get peer group by name.

        Args:
            group_name (str): Name of the peer group.

        Returns:
            DcManagerSubcloudPeerGroupListObject: Peer group object.
        """
        for peer_group in self.peer_group_list:
            if peer_group.get_group_name() == group_name:
                return peer_group
        raise ValueError(f"Peer group '{group_name}' not found")

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """Checks if the output contains all the required fields.

        Args:
            value (dict): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["peer_group_name", "group_priority", "group_state", "system_leader_id", "system_leader_name", "max_subcloud_rehoming"]
        missing_fields = set(required_fields) - set(value.keys())

        if missing_fields:
            get_logger().log_error(f"Missing fields in output: {', '.join(missing_fields)}")
            return False
        return True

    def __str__(self) -> str:
        """String representation of the peer group list."""
        return f"{self.__class__.__name__}(rows={len(self.peer_group_list)})"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return self.__str__()
