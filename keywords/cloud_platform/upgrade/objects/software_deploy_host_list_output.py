"""Software deploy host-list Output."""

from typing import List

from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.cloud_platform.upgrade.objects.software_deploy_host_list_object import SoftwareDeployHostListObject


class SoftwareDeployHostListOutput:
    """
    Parses the output of the 'software deploy host-list' command into structured objects.

    This class uses SystemTableParser to convert the raw CLI output of
    'software deploy host-list' into a list of SoftwareDeployHostListObject entries.
    """

    def __init__(self, software_deploy_host_list_output: str):
        """
        Initialize and parse the software deploy host-list output.

        Args:
            software_deploy_host_list_output (str): Raw output from
                'software deploy host-list' command.
        """
        self.host_list: List[SoftwareDeployHostListObject] = []
        system_table_parser = SystemTableParser(software_deploy_host_list_output)
        self.output_values = system_table_parser.get_output_values_list()

        for value in self.output_values:
            host_obj = SoftwareDeployHostListObject(
                value["Host"],
                value["From Release"],
                value["To Release"],
                value["RR"],
                value["State"],
            )
            self.host_list.append(host_obj)

    def get_host_list(self) -> List[SoftwareDeployHostListObject]:
        """
        Get all software deploy host-list objects.

        Returns:
            List[SoftwareDeployHostListObject]: Parsed host entries.
        """
        return self.host_list

    def get_host_list_details(self) -> List[dict]:
        """
        Get host-list details in a list of dictionaries.

        Returns:
            List[dict]: Parsed table rows as dictionaries.
        """
        return self.output_values

    def get_hosts_by_state(self, state: str) -> List[str]:
        """
        Get names of all hosts with a given state.

        Args:
            state (str): Desired state (e.g., "deploy-host-rollback-pending").

        Returns:
            List[str]: Matching host names.
        """
        return [entry["Host"] for entry in self.output_values if entry["State"] == state]

    def get_state_by_host(self, host: str) -> str:
        """
        Get the state for a given host.

        Args:
            host (str): Host name.

        Returns:
            str: State of the host, empty string if not found.
        """
        for entry in self.output_values:
            if entry["Host"] == host:
                return entry["State"]
        return ""

    def are_all_hosts_in_state(self, state: str) -> bool:
        """
        Check if all hosts are in a given state.

        Args:
            state (str): Desired state.

        Returns:
            bool: True if all hosts have the given state, False otherwise.
        """
        if not self.output_values:
            return False
        return all(entry["State"] == state for entry in self.output_values)

    def __str__(self) -> str:
        """
        Return a human-readable string representation of the host list.

        Returns:
            str: Formatted host entries as strings.
        """
        return "\n".join([str(entry) for entry in self.host_list])

    def __repr__(self) -> str:
        """
        Return the developer-facing representation of the object.

        Returns:
            str: Class name and row count.
        """
        return f"{self.__class__.__name__}(rows={len(self.host_list)})"
