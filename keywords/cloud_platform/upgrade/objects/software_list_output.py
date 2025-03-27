"""Software List Output."""

from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.cloud_platform.upgrade.objects.software_list_object import SoftwareListObject


class SoftwareListOutput:
    """

    This class parses o/p 'software list' command into an object of
    type SoftwareListObject.

    """

    def __init__(self, software_list_output):
        """
        Constructor

        Args:
            software_list_output (str): output of 'software list' command
        """
        self.software_list: SoftwareListObject = []
        system_table_parser = SystemTableParser(software_list_output)
        self.output_values = system_table_parser.get_output_values_list()

        for value in self.output_values:
            software_list_object = SoftwareListObject(
                value["Release"],
                value["RR"],
                value["State"],
            )
            self.software_list.append(software_list_object)

    def get_software_lists(self) -> list[SoftwareListObject]:
        """
        Get all software list objects.

        Returns:
            the list of software list objects

        """
        return self.software_list

    def get_software_list_details(self):
        """
        Get software list details in a list of dictionaries.

        Returns:
            list of software list dict

        """
        return self.output_values

    def get_release_name_by_state(self, state):
        """
        Get Release name of a release based in its state.

        Args:
            state: State of the release.

        Returns:
            list of release name.

        """
        software_list_details = self.output_values
        release_name = []
        for j in range(len(software_list_details)):
            if software_list_details[j]["State"] == state:
                release_details = software_list_details[j]
                release_name.append(release_details["Release"])
        return release_name

    def get_release_state_by_release_name(self, release_name):
        """
        Get the Release State based on the release name.

        Args:
            release_name: name of the release.

        Returns:
            state of the release

        """
        software_list_details = self.output_values
        for j in range(len(software_list_details)):
            for i in software_list_details:
                if software_list_details[j]["Release"] == release_name:
                    release_details = software_list_details[j]
        return release_details["State"]
