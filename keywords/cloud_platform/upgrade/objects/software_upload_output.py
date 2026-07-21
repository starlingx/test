"""Software Upload Output."""

from typing import Dict

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.cloud_platform.upgrade.objects.software_upload_object import SoftwareUploadObject
from keywords.cloud_platform.upgrade.objects.usm_metapackage_constants import METAPACKAGE_LIST


class SoftwareUploadOutput:
    """This class parses o/p 'software show' command into an object of type SoftwareUploadObject."""

    def __init__(self, software_upload_output: list[str]):
        """Instance of the class.

        Args:
            software_upload_output (list[str]): output of 'software show' command as a list of strings.
        """
        self.software_show: SoftwareUploadObject = []
        self.metapackage_releases: list[str] = [
            line.strip()
            for line in software_upload_output
            if any(prefix in line for prefix in METAPACKAGE_LIST)
        ]
        system_table_parser = SystemTableParser(software_upload_output)
        self.output_values = system_table_parser.get_output_values_list()

        for value in self.output_values:
            software_show_object = SoftwareUploadObject(
                value["Uploaded File"],
                value["Release"],
            )
            self.software_show.append(software_show_object)

    def get_software_uploaded(self) -> SoftwareUploadObject:
        """Get the uploaded data.

        Returns:
            SoftwareUploadObject: the list of software upload objects

        """
        return self.software_show

    def get_metapackage_releases(self) -> list[str]:
        """Get the list of metapackage release lines from the upload output.

        Returns:
            list[str]: Lines containing metapackage release info, or an empty list if none were present.
        """
        return self.metapackage_releases

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["Release", "Uploaded File"]
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                return False
        return True
