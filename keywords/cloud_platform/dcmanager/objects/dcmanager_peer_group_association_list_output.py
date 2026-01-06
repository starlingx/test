from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import DcManagerTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_peer_group_association_list_object import DcManagerPeerGroupAssociationListObject


class DcManagerPeerGroupAssociationListOutput:
    """
    Class representing the output of the 'dcmanager peer-group-association list' command.

    Parses tabular output and stores a list of DcManagerPeerGroupAssociationListObject.
    """

    def __init__(self, dcmanager_peer_group_association_list_output: List[str]):
        """
        Initializes the DcManagerPeerGroupAssociationListOutput with a list of associations.

        Args:
            dcmanager_peer_group_association_list_output (List[str]): The output of 'dcmanager peer-group-association list' command.
        """
        self.dcmanager_peer_group_association: List[DcManagerPeerGroupAssociationListObject] = []
        dcmanager_table_parser = DcManagerTableParser(dcmanager_peer_group_association_list_output)
        output_values = dcmanager_table_parser.get_output_values_list()

        for value in output_values:

            if "id" not in value:
                raise KeywordException(f"The output line {value} was not valid because it is missing an 'id'.")

            if value["id"] == "<none>":
                continue

            dcmanager_peer_group_association_object = DcManagerPeerGroupAssociationListObject(value["id"])

            if "peer_group_id" in value:
                dcmanager_peer_group_association_object.set_peer_group_id(value["peer_group_id"])

            if "system_peer_id" in value:
                dcmanager_peer_group_association_object.set_system_peer_id(value["system_peer_id"])

            if "type" in value:
                dcmanager_peer_group_association_object.set_type(value["type"])

            if "sync_status" in value:
                dcmanager_peer_group_association_object.set_sync_status(value["sync_status"])

            if "peer_group_priority" in value:
                dcmanager_peer_group_association_object.set_peer_group_priority(value["peer_group_priority"])

            self.dcmanager_peer_group_association.append(dcmanager_peer_group_association_object)

    def get_dcmanager_peer_group_association_list(self) -> List[DcManagerPeerGroupAssociationListObject]:
        """
        Returns the list of parsed peer group association objects.

        Returns:
            List[DcManagerPeerGroupAssociationListObject]: List of DcManagerPeerGroupAssociationListObject instances.
        """
        return self.dcmanager_peer_group_association

    def get_latest_peer_group_association_id(self) -> int:
        """Returns the ID of the latest peer group association.

        Returns:
            int: Latest peer group association ID.

        Raises:
            Exception: If no peer groups associations are available.
        """
        if not self.dcmanager_peer_group_association:
            raise Exception("No peer group associations are found.")
        return self.dcmanager_peer_group_association[-1].get_id()

    def is_valid_output(self, value: dict) -> bool:
        """
        Validates whether the required fields exist in the parsed row.

        Args:
            value (dict): Parsed row dictionary.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["id", "peer_group_id", "system_peer_id", "peer_group_priority", "sync_status"]
        missing_fields = set(required_fields) - set(value.keys())

        if missing_fields:
            get_logger().log_error(f"Missing fields in output: {', '.join(missing_fields)}")
            return False

        return True
