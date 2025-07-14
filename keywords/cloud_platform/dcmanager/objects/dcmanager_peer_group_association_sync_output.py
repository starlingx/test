from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_peer_group_association_sync_object import DcManagerPeerGroupAssociationSyncObject


class DcManagerPeerGroupAssociationSyncOutput:
    """Represents the output of 'dcmanager peer-group-association sync' command."""

    def __init__(self, dcmanager_peer_group_association_sync_output: list[str]) -> None:
        """
        Parses the output of 'dcmanager peer-group-association sync <association>' command and initializes

        Args:
            dcmanager_peer_group_association_sync_output (list[str]): the output of 'dcmanager peer-group-association sync' command
        """
        self.dcmanager_peer_group_association_sync_object: DcManagerPeerGroupAssociationSyncObject
        dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_peer_group_association_sync_output)
        output_values = dcmanager_vertical_table_parser.get_output_values_dict()

        if "id" not in output_values:
            raise KeywordException(f"The output {dcmanager_peer_group_association_sync_output} was not valid because it is missing an 'id'.")

        dcmanager_peer_group_association_sync_object = DcManagerPeerGroupAssociationSyncObject(output_values.get("id"))

        if "peer_group_id" in output_values:
            dcmanager_peer_group_association_sync_object.set_peer_group_id(output_values["peer_group_id"])

        if "system_peer_id" in output_values:
            dcmanager_peer_group_association_sync_object.set_system_peer_id(output_values["system_peer_id"])

        if "association_type" in output_values:
            dcmanager_peer_group_association_sync_object.set_association_type(output_values["association_type"])

        if "sync_status" in output_values:
            dcmanager_peer_group_association_sync_object.set_sync_status(output_values["sync_status"])

        if "peer_group_priority" in output_values:
            dcmanager_peer_group_association_sync_object.set_peer_group_priority(output_values["peer_group_priority"])

        if "sync_message" in output_values:
            dcmanager_peer_group_association_sync_object.set_sync_message(output_values["sync_message"])

        if "created_at" in output_values:
            dcmanager_peer_group_association_sync_object.set_created_at(output_values["created_at"])

        if "updated_at" in output_values:
            dcmanager_peer_group_association_sync_object.set_updated_at(output_values["updated_at"])

        self.dcmanager_peer_group_association_sync_object = dcmanager_peer_group_association_sync_object

    def get_dcmanager_peer_group_association_sync_object(self) -> DcManagerPeerGroupAssociationSyncObject:
        """
        DcManagerPeerGroupAssociationSyncObject.

        Returns:
            DcManagerPeerGroupAssociationSyncObject: the DcManagerPeerGroupAssociationSyncObject object representing the
            output of the command 'dcmanager peer-group-association sync <association>'.
        """
        return self.dcmanager_peer_group_association_sync_object
