import copy
from typing import List, Optional

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import DcManagerTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object import DcManagerSubcloudListObject
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object_filter import DcManagerSubcloudListObjectFilter


class DcManagerSubcloudListOutput:
    """
    Represents the output of 'dcmanager subcloud list' command as a list of DcManagerSubcloudListObject objects.
    """

    def __init__(self, dcmanager_subcloud_list_output: list[str]):
        """
        Constructor

        Args:
            dcmanager_subcloud_list_output (list[str]): output of 'dcmanager subcloud list' command

        """
        self.dcmanager_subclouds: [DcManagerSubcloudListObject] = []
        dcmanager_table_parser = DcManagerTableParser(dcmanager_subcloud_list_output)
        output_values = dcmanager_table_parser.get_output_values_list()

        for value in output_values:

            if "id" not in value:
                raise KeywordException(f"The output line {value} was not valid because it is missing an 'id'.")

            if value["id"] == "<none>":
                continue

            dcmanager_subcloud_object: DcManagerSubcloudListObject = DcManagerSubcloudListObject(value["id"])

            if "name" in value:
                dcmanager_subcloud_object.set_name(value["name"])

            if "management" in value:
                dcmanager_subcloud_object.set_management(value["management"])

            if "availability" in value:
                dcmanager_subcloud_object.set_availability(value["availability"])

            if "deploy status" in value:
                dcmanager_subcloud_object.set_deploy_status(value["deploy status"])

            if "sync" in value:
                dcmanager_subcloud_object.set_sync(value["sync"])

            if "backup status" in value:
                dcmanager_subcloud_object.set_backup_status(value["backup status"])

            if "prestage status" in value:
                dcmanager_subcloud_object.set_prestage_status(value["prestage status"])

            self.dcmanager_subclouds.append(dcmanager_subcloud_object)

    def get_dcmanager_subcloud_list_objects(self) -> List[DcManagerSubcloudListObject]:
        """This function will return the list of DcManagerSubcloudObject objects.

        Args: None

        Returns: list (DcManagerSubcloudObject): list of DcManagerSubcloudListObject objects representing the output of
        the 'dcmanager subcloud list' command.

        """
        return self.get_dcmanager_subcloud_list_objects_filtered(None)

    def get_dcmanager_subcloud_list_objects_filtered(self, dcmanager_subcloud_list_object_filter: Optional[DcManagerSubcloudListObjectFilter]) -> Optional[List[DcManagerSubcloudListObject]]:
        """Look for DcManagerSubcloudListObject instances in 'dcmanager_subclouds'

        whose properties match the respective properties in the provided filter object,
        if they are defined.

        Args:
            dcmanager_subcloud_list_object_filter (Optional[DcManagerSubcloudListObjectFilter]):
                An object containing property values to filter the items in 'dcmanager_subclouds'.

        Returns:
            Optional[List[DcManagerSubcloudListObject]]: A filtered list of matching DcManagerSubcloudListObject instances.
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
        """Gets an instance of DcManagerSubcloudListObject with the lowest ID and that satisfies the criteria:

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
        """
        Gets an instance of DcManagerSubcloudListObject whose name attribute is equal to the argument 'subcloud_name'.

        Args:
            subcloud_name (str): The name of the subcloud to be retrieved.

        Returns:
            DcManagerSubcloudListObject: An instance of DcManagerSubcloudListObject whose name attribute matches the
            argument 'subcloud_name'. This instance represents a row from the output of the command
            'dcmanager subcloud list' where the column 'name' matches the argument 'subcloud_name'.

        """
        dcmanager_subcloud_list_object_filter = DcManagerSubcloudListObjectFilter()
        dcmanager_subcloud_list_object_filter.set_name(subcloud_name)
        subclouds = self.get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_object_filter)

        if not subclouds:
            error_message = f"In this DC system, there is no subcloud named {subcloud_name}."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        return subclouds[0]

    def is_subcloud_in_output(self, subcloud_name: str) -> bool:
        """
        Checks if a subcloud is in the output of 'dcmanager subcloud list' command.

        Args:
            subcloud_name (str): The name of the subcloud to check.

        Returns:
            bool: True if the subcloud is in the output, False otherwise.

        """
        dcmanager_subcloud_list_object_filter = DcManagerSubcloudListObjectFilter()
        dcmanager_subcloud_list_object_filter.set_name(subcloud_name)
        subclouds = self.get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_object_filter)

        return bool(subclouds)

    def get_lower_id_async_subcloud(self) -> DcManagerSubcloudListObject:
        """Gets an instance of DcManagerSubcloudListObject with the lowest ID and that satisfies the criteria:

            _ Managed;
            _ Online;
            _ Deploy completed;
            _ out-of-sync

        Returns:
            DcManagerSubcloudListObject: the instance of DcManagerSubcloudListObject with the lowest ID that satisfies
            the above criteria.

        """
        dcmanager_subcloud_list_obj_filter = DcManagerSubcloudListObjectFilter.get_out_of_sync_subcloud_filter()
        subclouds = self.get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_obj_filter)

        if not subclouds:
            error_message = "In this DC system, there is no subcloud managed, online, deploy completed, and out-of-sync."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        return min(subclouds, key=lambda subcloud: int(subcloud.get_id()))

    def get_undeployed_subcloud_name(self, lab_type: str = None) -> str:
        """
        Fetch the name of the first subcloud that is not deployed.

        This method iterates through the subclouds in the lab configuration
        and returns the name of the first subcloud that is not deployed.
        This is used to determine the appropriate subcloud to check based
        on the lab type.

        Args:
            lab_type (str): The type of the lab (e.g., 'simplex', 'duplex').

        Returns:
            str: The name of the first subcloud that is not deployed or None.
        """
        # fetch all the subclouds from the system
        deployed_sc_names = [i.get_name() for i in self.dcmanager_subclouds]

        lab_config = ConfigurationManager.get_lab_config()
        # fetch all the subclouds from the lab config
        sc_names_from_config = lab_config.get_subclouds_name_by_type(lab_type)

        # return None if there is no subcloud in the config for the given type
        if not sc_names_from_config:
            return None

        all_free_sc = set(sc_names_from_config).difference(set(deployed_sc_names))

        if not all_free_sc:
            return None

        return all_free_sc.pop()

    def get_healthy_subcloud_by_type(self, lab_type: str) -> DcManagerSubcloudListObject:
        """Fetch the last healthy subcloud by type.

        Args:
            lab_type (str): The type of the lab (e.g., 'simplex', 'duplex').

        Returns:
            DcManagerSubcloudListObject: The first healthy subcloud object of the specified type.
        """
        dcmanager_subcloud_list_object_filter = DcManagerSubcloudListObjectFilter.get_healthy_subcloud_filter()
        subclouds = self.get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_object_filter)
        subclouds_by_type = []

        if not subclouds:
            error_message = "In this DC system, there is no subcloud managed, online, deploy completed, and out-of-sync."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        for sc in subclouds:
            lab_config = ConfigurationManager.get_lab_config()
            sc_config = lab_config.get_subcloud(sc.get_name())
            if sc_config.get_lab_type() == lab_type:
                subclouds_by_type.append(sc)

        if not subclouds_by_type:
            error_message = f"In this DC system, there is no healthy subcloud of type {lab_type}."
            get_logger().log_exception(error_message)
            raise ValueError(error_message)
        return max(subclouds_by_type, key=lambda subcloud: int(subcloud.get_id()))
