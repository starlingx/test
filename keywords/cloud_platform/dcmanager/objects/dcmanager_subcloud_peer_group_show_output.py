from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_peer_group_list_object import DcManagerSubcloudPeerGroupListObject


class DcManagerSubcloudPeerGroupShowOutput:
    """Parses the output of 'dcmanager subcloud-peer-group show' command."""

    def __init__(self, peer_group_list_output: str):
        """Initialize and parse the peer group list output.

        Args:
            peer_group_list_output (str): Raw output from command.
        """
        dc_vertical_table_parser = DcManagerVerticalTableParser(peer_group_list_output)
        output_values = dc_vertical_table_parser.get_output_values_dict()
        if not self.is_valid_output(output_values):
            raise KeywordException(f"The output line {output_values} was not valid")
        self.peer_group_object = DcManagerSubcloudPeerGroupListObject(
            output_values.get("id"),
            output_values.get("peer_group_name"),
            output_values.get("group_priority"),
            output_values.get("group_state"),
            output_values.get("system_leader_id"),
            output_values.get("system_leader_name"),
            output_values.get("max_subcloud_rehoming"),
        )

    def get_dcmanager_subcloud_peer_group_object(self) -> DcManagerSubcloudPeerGroupListObject:
        """Get the peer group object.

        Returns:
            DcManagerSubcloudPeerGroupListObject: Peer group object.
        """
        return self.peer_group_object

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """Checks if the output contains all the required fields.

        Args:
            value (dict): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["id", "peer_group_name", "group_priority", "group_state", "system_leader_id", "system_leader_name", "max_subcloud_rehoming"]
        return all(field in value for field in required_fields)

    def __str__(self) -> str:
        """String representation of the system peer object.

        Returns:
            str: String representation.
        """
        return f"{self.__class__.__name__}"

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            str: String representation.
        """
        return self.__str__()
