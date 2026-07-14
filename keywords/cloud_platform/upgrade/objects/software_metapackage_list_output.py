"""Software Metapackage List Output."""

from typing import List

from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.cloud_platform.upgrade.objects.software_metapackage_list_object import SoftwareMetapackageListObject


class SoftwareMetapackageListOutput:
    """Parses the output of 'software metapackage list' into structured objects."""

    def __init__(self, software_metapackage_list_output: str):
        """Initialize and parse the metapackage list output.

        Args:
            software_metapackage_list_output (str): Raw output from 'software metapackage list --a'.
        """
        self.metapackage_list: List[SoftwareMetapackageListObject] = []
        system_table_parser = SystemTableParser(software_metapackage_list_output)
        self.output_values = system_table_parser.get_output_values_list()

        for value in self.output_values:
            self.metapackage_list.append(
                SoftwareMetapackageListObject(
                    value["Release"],
                    value["RR"],
                    value["State"],
                )
            )

    def get_metapackage_list(self) -> List[SoftwareMetapackageListObject]:
        """Get all metapackage list objects.

        Returns:
            List[SoftwareMetapackageListObject]: Parsed metapackage entries.
        """
        return self.metapackage_list

    def get_metapackages_by_state(self, state: str) -> List[SoftwareMetapackageListObject]:
        """Get all metapackages with a given state.

        Args:
            state (str): Desired state (e.g., 'deployed', 'available').

        Returns:
            List[SoftwareMetapackageListObject]: Matching metapackage entries.
        """
        return [entry for entry in self.metapackage_list if entry.get_state() == state]

    def get_metapackage_by_release(self, release: str) -> SoftwareMetapackageListObject:
        """Get a metapackage entry by its release name.

        Args:
            release (str): Metapackage release name.

        Returns:
            SoftwareMetapackageListObject: Matching metapackage entry.

        Raises:
            ValueError: If no metapackage with the given release name is found.
        """
        for entry in self.metapackage_list:
            if entry.get_release() == release:
                return entry
        raise ValueError(f"Metapackage with release '{release}' not found")

    def get_metapackages_to_deploy(self, metapackages_config: str | list) -> list[str]:
        """Resolve which metapackage release names should be deployed based on config.

        Args:
            metapackages_config (str | list): Value from USMConfig.get_metapackages().
                - "None": returns an empty list (skip metapackage deployment).
                - "All": returns all metapackage release names in the 'available' state.
                - list[str]: validates each name exists in the output and returns the list.

        Returns:
            list[str]: Metapackage release names to deploy.

        Raises:
            ValueError: If a requested metapackage name is not found in the output.
        """
        if metapackages_config == "None":
            return []
        if metapackages_config == "All":
            return [entry.get_release() for entry in self.metapackage_list if entry.get_state() == "available"]
        available_names = {entry.get_release() for entry in self.metapackage_list if entry.get_state() == "available"}
        for name in metapackages_config:
            if name not in available_names:
                raise ValueError(f"Metapackage '{name}' is not in the available state or does not exist")
        return list(metapackages_config)

    def __str__(self) -> str:
        """Return a human-readable string representation.

        Returns:
            str: Formatted metapackage entries.
        """
        return "\n".join([str(entry) for entry in self.metapackage_list])

    def __repr__(self) -> str:
        """Return the developer-facing representation.

        Returns:
            str: Class name and row count.
        """
        return f"{self.__class__.__name__}(rows={len(self.metapackage_list)})"
