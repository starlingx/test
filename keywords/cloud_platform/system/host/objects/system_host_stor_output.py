from typing import Union

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.system_host_stor_object import SystemHostStorageObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostStorageOutput:
    """
    This class parses the output of 'system host-stor-list' commands into a list of SystemHostStorageObject.
    """

    def __init__(self, system_host_stor_output: Union[str, RestResponse]) -> None:
        """
        Constructor for SystemHostStorageOutput.

        Args:
            system_host_stor_output (Union[str, RestResponse]):
                Either:
                - A raw string output from the `system host-stor-list` command.
                - A `RestResponse` object containing the storage list in JSON/dict format.
        """
        self.system_host_storages: list[SystemHostStorageObject] = []

        if isinstance(system_host_stor_output, RestResponse):  # came from REST and is already in dict form
            json_object = system_host_stor_output.get_json_content()
            if "istors" in json_object:
                storages = json_object["istors"]
            else:
                storages = [json_object]
        else:
            system_table_parser = SystemTableParser(system_host_stor_output)
            storages = system_table_parser.get_output_values_list()

        for value in storages:

            system_host_stor_object = SystemHostStorageObject()

            if "uuid" in value:
                system_host_stor_object.set_uuid(value["uuid"])

            if "function" in value:
                system_host_stor_object.set_function(value["function"])

            if "osdid" in value and value["osdid"] not in (None, "None", ""):
                system_host_stor_object.set_osdid(int(value["osdid"]))
            else:
                system_host_stor_object.set_osdid(None)

            if "state" in value:
                system_host_stor_object.set_state(value["state"])

            if "idisk_uuid" in value:
                system_host_stor_object.set_idisk_uuid(value["idisk_uuid"])

            if "journal_path" in value:
                system_host_stor_object.set_journal_path(value["journal_path"])

            if "journal_node" in value:
                system_host_stor_object.set_journal_node(value["journal_node"])

            if "journal_size_gib" in value:
                system_host_stor_object.set_journal_size_gib(float(value["journal_size_gib"]))
            elif "journal_size_mib" in value:
                system_host_stor_object.set_journal_size_gib(float(value["journal_size_mib"]) / 1024)  # rest value is in mibs, setting to gibs

            if "tier_name" in value:
                system_host_stor_object.set_tier_name(value["tier_name"])

            self.system_host_storages.append(system_host_stor_object)

    def get_osd_storage_count(self) -> int:
        """
        This function counts the number of OSD storages on this host by counting the objects in the storage list where the 'function' is 'osd'.

        Returns: The number of OSD storages on this host.

        """
        return len([item for item in self.system_host_storages if item.function == "osd"])

    def has_minimum_number_physical_interface(self, min_num_osd_storage) -> bool:
        """
        This function verifies if this host has at least <min_num_osd_storage> OSD storages.

        Returns: True if this host has at least <min_num_osd_storage> OSD storage, False otherwise.

        """
        return self.get_osd_storage_count() >= min_num_osd_storage

    def get_state_osd(self) -> list[str]:
        """
        Returns the current state of all OSDs.

        Returns:
            list[str]: A list with the state of each OSD.
        """
        return [item.get_state() for item in self.system_host_storages]
