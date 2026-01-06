from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_peer_group_status_object import DcManagerSubcloudPeerGroupStatusObject


class DcManagerSubcloudPeerGroupStatusOutput:
    """Parses the output of 'dcmanager subcloud-peer-group status' command."""

    def __init__(self, peer_group_status_output: str):
        """Initialize and parse the peer group status output.

        Args:
            peer_group_status_output (str): Raw output from command.
        """
        dc_vertical_table_parser = DcManagerVerticalTableParser(peer_group_status_output)
        output_values = dc_vertical_table_parser.get_output_values_dict()
        if not self.is_valid_output(output_values):
            raise KeywordException(f"The output line {output_values} was not valid")
        self.peer_group_status_object = DcManagerSubcloudPeerGroupStatusObject(
            output_values.get("peer_group_id"),
            output_values.get("peer_group_name"),
            output_values.get("total_subclouds"),
            output_values.get("complete"),
            output_values.get("waiting_for_migrate"),
            output_values.get("rehoming"),
            output_values.get("rehome_failed"),
            output_values.get("managed"),
            output_values.get("unmanaged"),
        )

    def get_dcmanager_subcloud_peer_group_status_object(self) -> DcManagerSubcloudPeerGroupStatusObject:
        """Get the peer group status object.

        Returns:
            DcManagerSubcloudPeerGroupStatusObject: Peer group status object.
        """
        return self.peer_group_status_object

    def __str__(self) -> str:
        """String representation of the peer group status output.

        Returns:
            str: String representation.
        """
        return f"{self.__class__.__name__}"

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """Checks if the output contains all the required fields.

        Args:
            value (dict): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["peer_group_id", "peer_group_name", "total_subclouds", "complete", "waiting_for_migrate", "rehoming", "rehome_failed", "managed", "unmanaged"]
        return all(field in value for field in required_fields)

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            str: String representation.
        """
        return self.__str__()
