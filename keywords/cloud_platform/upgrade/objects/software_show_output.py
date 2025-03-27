"""Software Show Output."""

from keywords.cloud_platform.system.system_table_parser import SystemTableParser
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
