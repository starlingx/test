"""Software Show Output."""

import json
from typing import List

from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.cloud_platform.upgrade.objects.software_metapackage_list_object import SoftwareMetapackageListObject
from keywords.cloud_platform.upgrade.objects.software_show_object import SoftwareShowObject


class SoftwareShowOutput:
    """
    This class parses o/p 'software show' command into an object of
    type SoftwareShowObject.

    """

    def __init__(self, software_show_output):
        """
        Instance of the class.

        Args:
            software_show_output: output of 'software show' command as a list of strings.
        """
        self.software_show: SoftwareShowObject = []
        system_table_parser = SystemTableParser(software_show_output)
        self.output_values = system_table_parser.get_output_values_list()

        for value in self.output_values:
            software_show_object = SoftwareShowObject(
                value["Property"],
                value["Value"],
            )
            self.software_show.append(software_show_object)

    def get_software_show(self) -> SoftwareShowObject:
        """
        Get all software show objects.

        Returns:
            the list of software show objects

        """
        software_show = self.software_show
        return software_show

    def get_metapackages(self) -> List[SoftwareMetapackageListObject]:
        """
        Parse the 'metapackages' property from 'software show --metapackages' output.

        Returns:
            List[SoftwareMetapackageListObject]: Parsed metapackage entries with release name and state.
        """
        raw = self.get_property_value("metapackages")
        metapackages_dict = json.loads(raw)
        return [SoftwareMetapackageListObject(release, "", attrs["state"]) for release, attrs in metapackages_dict.items()]

    def get_property_value(self, property_name: str) -> str:
        """
        Return the value for a given software show property (e.g., "State").

        Args:
            property_name (str): Property key to look up.

        Returns:
            str: The corresponding value, or empty string if not found.
        """
        for entry in self.output_values:
            if entry["Property"] == property_name:
                return entry["Value"]
        return ""
