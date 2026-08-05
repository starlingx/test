"""Software Deploy Show Output."""

from typing import List, Optional

from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.cloud_platform.upgrade.objects.software_deploy_show_object import SoftwareDeployShowObject


class SoftwareDeployShowOutput:
    """
    Parses the output of the 'software deploy show' command into structured objects.

    This class uses SystemTableParser to convert the raw CLI output of
    'software deploy show' into a list of SoftwareDeployShowObject entries.
    """

    def __init__(self, software_deploy_show_output: str):
        """
        Initialize and parse the software deploy show output.

        Args:
            software_deploy_show_output (str): Raw output from 'software deploy show' command.
        """
        self.software_deploy_show: Optional[SoftwareDeployShowObject] = None
        system_table_parser = SystemTableParser(software_deploy_show_output)
        self.output_values = system_table_parser.get_output_values_list()

        if self.output_values:
            value = self.output_values[0]
            if "From Release" in value:
                self.software_deploy_show = SoftwareDeployShowObject(
                    rr=value["RR"],
                    state=value["State"],
                    from_release=value["From Release"],
                    to_release=value["To Release"],
                )
            else:
                self.software_deploy_show = SoftwareDeployShowObject(
                    rr=value["RR"],
                    state=value["State"],
                    releases=value["Releases"],
                )

    def get_software_deploy_show(self) -> Optional[SoftwareDeployShowObject]:
        """
        Get all software Deploy Show objects.

        Returns:
            Optional[SoftwareDeployShowObject]: Parsed software deploy show, or None if no deploy is in progress.
        """
        return self.software_deploy_show

    def get_software_deploy_show_details(self) -> List[dict]:
        """
        Get software deploy show details in a list of dictionaries.

        Returns:
            List[dict]: Parsed table rows.
        """
        return self.output_values

    def __str__(self) -> str:
        """
        Return a human-readable string representation of the software list.

        Returns:
            str: Formatted software entries as strings.
        """
        return "\n".join([str(entry) for entry in self.software_deploy_show])

    def __repr__(self) -> str:
        """
        Return the developer-facing representation of the object.

        Returns:
            str: Class name and row count.
        """
        return f"{self.__class__.__name__}(rows={len(self.software_deploy_show)})"
