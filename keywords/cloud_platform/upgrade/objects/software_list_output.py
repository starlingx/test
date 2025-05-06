"""Software List Output."""

from typing import List

from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.cloud_platform.upgrade.objects.software_list_object import SoftwareListObject


class SoftwareListOutput:
    """
    Parses the output of the 'software list' command into structured objects.

    This class uses SystemTableParser to convert the raw CLI output of
    'software list' into a list of SoftwareListObject entries.
    """

    def __init__(self, software_list_output: str):
        """
        Initialize and parse the software list output.

        Args:
            software_list_output (str): Raw output from 'software list' command.
        """
        self.software_list: List[SoftwareListObject] = []
        system_table_parser = SystemTableParser(software_list_output)
        self.output_values = system_table_parser.get_output_values_list()

        for value in self.output_values:
            software_list_object = SoftwareListObject(
                value["Release"],
                value["RR"],
                value["State"],
            )
            self.software_list.append(software_list_object)

    def get_software_lists(self) -> List[SoftwareListObject]:
        """
        Get all software list objects.

        Returns:
            List[SoftwareListObject]: Parsed software entries.
        """
        return self.software_list

    def get_software_list_details(self) -> List[dict]:
        """
        Get software list details in a list of dictionaries.

        Returns:
            List[dict]: Parsed release table rows.
        """
        return self.output_values

    def get_release_name_by_state(self, state: str) -> List[str]:
        """
        Get names of all releases with a given state.

        Args:
            state (str): Desired software release state (e.g., "deployed").

        Returns:
            List[str]: Matching release names.
        """
        return [entry["Release"] for entry in self.output_values if entry["State"] == state]

    def get_release_state_by_release_name(self, release_name: str) -> str:
        """
        Get the state of a release by its name.

        Args:
            release_name (str): Software release name.

        Returns:
            str: State of the release (e.g., "available", "deployed"). Empty string if not found.
        """
        for entry in self.output_values:
            if entry["Release"] == release_name:
                return entry["State"]
        return ""

    def __str__(self) -> str:
        """
        Return a human-readable string representation of the software list.

        Returns:
            str: Formatted software entries as strings.
        """
        return "\n".join([str(entry) for entry in self.software_list])

    def __repr__(self) -> str:
        """
        Return the developer-facing representation of the object.

        Returns:
            str: Class name and row count.
        """
        return f"{self.__class__.__name__}(rows={len(self.software_list)})"
