import copy
from typing import List, Optional

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import DcManagerTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object import DcManagerSubcloudListObject
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object_filter import DcManagerSubcloudListObjectFilter


class DcManagerSubcloudListOutput:
    """
    Represents the output of 'dcmanager subcloud list' command as a list of DcManagerSubcloudListObject objects.
    """

    def __init__(self, dcmanager_subcloud_list_output):
        """
        Constructor

        Args:
            dcmanager_subcloud_list_output (list(str)): output of 'dcmanager subcloud list' command

        """
        self.dcmanager_subclouds: [DcManagerSubcloudListObject] = []
        dcmanager_table_parser = DcManagerTableParser(dcmanager_subcloud_list_output)
        output_values = dcmanager_table_parser.get_output_values_list()

        for value in output_values:

            if 'id' not in value:
                raise KeywordException(f"The output line {value} was not valid because it is missing an 'id'.")

            if value['id'] == "<none>":
                continue

            dcmanager_subcloud_object: DcManagerSubcloudListObject = DcManagerSubcloudListObject(value['id'])

            if 'name' in value:
                dcmanager_subcloud_object.set_name(value['name'])

            if 'management' in value:
                dcmanager_subcloud_object.set_management(value['management'])

            if 'availability' in value:
                dcmanager_subcloud_object.set_availability(value['availability'])

            if 'deploy status' in value:
                dcmanager_subcloud_object.set_deploy_status(value['deploy status'])

            if 'sync' in value:
                dcmanager_subcloud_object.set_sync(value['sync'])

            if 'backup status' in value:
                dcmanager_subcloud_object.set_backup_status(value['backup status'])

            if 'prestage status' in value:
                dcmanager_subcloud_object.set_prestage_status(value['prestage status'])

            self.dcmanager_subclouds.append(dcmanager_subcloud_object)

    def get_dcmanager_subcloud_list_objects(self) -> List[DcManagerSubcloudListObject]:
        """
        This function will return the list of DcManagerSubcloudObject objects.
        Args: None

        Returns: list (DcManagerSubcloudObject): list of DcManagerSubcloudListObject objects representing the output of
        the 'dcmanager subcloud list' command.

        """
        return self.get_dcmanager_subcloud_list_objects_filtered(None)

    def get_dcmanager_subcloud_list_objects_filtered(self, dcmanager_subcloud_list_object_filter: Optional[DcManagerSubcloudListObjectFilter]) -> Optional[List[DcManagerSubcloudListObject]]:
        """
        Looks for a DcManagerSubcloudListObject instance in 'dcmanager_subclouds' whose properties are equal to the
        respective properties in 'dcmanager_subcloud_list_input', if they are defined in it.
        Args:
            dcmanager_subcloud_list_object_filter (DcManagerSubcloudListObjectFilter): object with the properties values to filter the
            items in the 'dcmanager_subclouds'.

        Returns:
            List[DcManagerSubcloudListObject]: the filtered list of DcManagerSubcloudListObject instances we are looking for.

        """
        if dcmanager_subcloud_list_object_filter is None:
            return self.dcmanager_subclouds

        if not self.dcmanager_subclouds:
            return []

        dcmanager_subclouds_copy = copy.copy(self.dcmanager_subclouds)

        # Filters the copied list of DcManagerSubcloudListObject instances by id.
        if dcmanager_subcloud_list_object_filter.get_id() is not None:
            dcmanager_subclouds_copy = [subcloud for subcloud in dcmanager_subclouds_copy if subcloud.get_id() == dcmanager_subcloud_list_object_filter.get_id()]

        # Filters the copied list of DcManagerSubcloudListObject instances by name.
        if dcmanager_subcloud_list_object_filter.get_name() is not None:
            dcmanager_subclouds_copy = [subcloud for subcloud in dcmanager_subclouds_copy if subcloud.get_name() == dcmanager_subcloud_list_object_filter.get_name()]

        # Filters the copied list of DcManagerSubcloudListObject instances by management.
        if dcmanager_subcloud_list_object_filter.get_management() is not None:
            dcmanager_subclouds_copy = [subcloud for subcloud in dcmanager_subclouds_copy if subcloud.get_management() == dcmanager_subcloud_list_object_filter.get_management().value]

        # Filters the copied list of DcManagerSubcloudListObject instances by availability.
        if dcmanager_subcloud_list_object_filter.get_availability() is not None:
            dcmanager_subclouds_copy = [subcloud for subcloud in dcmanager_subclouds_copy if subcloud.get_availability() == dcmanager_subcloud_list_object_filter.get_availability().value]

        # Filters the copied list of DcManagerSubcloudListObject instances by backup status.
        if dcmanager_subcloud_list_object_filter.get_backup_status() is not None:
            dcmanager_subclouds_copy = [subcloud for subcloud in dcmanager_subclouds_copy if subcloud.get_backup_status() == dcmanager_subcloud_list_object_filter.get_backup_status().value]

        # Filters the copied list of DcManagerSubcloudListObject instances by deploy status.
        if dcmanager_subcloud_list_object_filter.get_deploy_status() is not None:
            dcmanager_subclouds_copy = [subcloud for subcloud in dcmanager_subclouds_copy if subcloud.get_deploy_status() == dcmanager_subcloud_list_object_filter.get_deploy_status().value]

        # Filters the copied list of DcManagerSubcloudListObject instances by prestage status.
        if dcmanager_subcloud_list_object_filter.get_prestage_status() is not None:
            dcmanager_subclouds_copy = [subcloud for subcloud in dcmanager_subclouds_copy if subcloud.get_prestage_status() == dcmanager_subcloud_list_object_filter.get_prestage_status().value]

        # Filters the copied list of DcManagerSubcloudListObject instances by sync.
        if dcmanager_subcloud_list_object_filter.get_sync() is not None:
            dcmanager_subclouds_copy = [subcloud for subcloud in dcmanager_subclouds_copy if subcloud.get_sync() == dcmanager_subcloud_list_object_filter.get_sync().value]

        return dcmanager_subclouds_copy

    def get_healthy_subcloud_with_lowest_id(self) -> DcManagerSubcloudListObject:
        """
        Gets the instance of DcManagerSubcloudListObject with the lowest ID and that satisfies the criteria:
            _ Managed;
            _ Online;
            _ Deploy completed;
            _ Synchronized.

        Returns:
            DcManagerSubcloudListObject: the instance of DcManagerSubcloudListObject with the lowest ID that satisfies
            the above criteria.

        """
        dcmanager_subcloud_list_object_filter = DcManagerSubcloudListObjectFilter.get_healthy_subcloud_filter()
        subclouds = self.get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_object_filter)

        if not subclouds:
            error_message = "In this DC system, there is no subcloud in a healthy state (managed, online, deploy completed, and synchronized)."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        lowest_subcloud = min(subclouds, key=lambda subcloud: int(subcloud.get_id()))
        return lowest_subcloud

    def get_subcloud_by_name(self, subcloud_name: str) -> DcManagerSubcloudListObject:
        dcmanager_subcloud_list_object_filter = DcManagerSubcloudListObjectFilter()
        dcmanager_subcloud_list_object_filter.set_name(subcloud_name)
        subclouds = self.get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_object_filter)

        if not subclouds:
            error_message = f"In this DC system, there is no subcloud named {subcloud_name}."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        return subclouds[0]