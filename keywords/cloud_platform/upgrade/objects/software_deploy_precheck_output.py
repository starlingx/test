from typing import Dict, List

from keywords.cloud_platform.upgrade.objects.software_deploy_precheck_object import SoftwareDeployPrecheckItemObject


class SoftwareDeployPrecheckOutput:
    """
    Parses the output of the 'software deploy precheck' command into structured objects.

    The raw output is expected to contain lines in the format:
        "<check name>: <status>"

    Example:
        "Ceph Storage Healthy: [OK]"
        "No alarms: [OK]"
        "System Health: [OK]"
    """

    def __init__(self, raw_output: List[str]):
        """
        Initialize and parse the precheck output.

        Args:
            raw_output (List[str]): Raw output lines from 'software deploy precheck'.
        """
        self._raw_output = raw_output
        self._items: List[SoftwareDeployPrecheckItemObject] = []
        self._status_by_name: Dict[str, str] = {}

        self._parse_output()

    def _parse_output(self) -> None:
        """
        Internal parsing of the raw output into objects and a name->status mapping.

        Only lines containing a status marker ([OK] or [Fail]) are collected.
        All other lines (headers, error messages, detail lines) are ignored.
        """
        for line in self._raw_output:
            if "[OK]" not in line and "[Fail]" not in line:
                continue

            key, value = line.split(":", 1)
            self._status_by_name[key.strip()] = value.strip()
            self._items.append(SoftwareDeployPrecheckItemObject(name=key.strip(), status=value.strip()))

    def get_items(self) -> List[SoftwareDeployPrecheckItemObject]:
        """
        Get all parsed precheck items.

        Returns:
            List[SoftwareDeployPrecheckItemObject]: Parsed items.
        """
        return self._items

    def get_status_dict(self) -> Dict[str, str]:
        """
        Get a mapping of check name -> status string.

        Returns:
            Dict[str, str]: Status by check name.
        """
        return self._status_by_name

    def get_status_by_name(self, name: str) -> str:
        """
        Get the status string for a specific check.

        Args:
            name (str): Check name.

        Returns:
            str: Status string or empty string if not found.
        """
        return self._status_by_name.get(name, "")

    def get_failed_items(self) -> List[SoftwareDeployPrecheckItemObject]:
        """
        Get all items that are not marked as OK.

        Returns:
            List[SoftwareDeployPrecheckItemObject]: Items where status does not contain "[OK]".
        """
        return [item for item in self._items if not item.is_ok()]

    def has_unhealthy_metapackages(self) -> bool:
        """
        Check if the output contains the unhealthy metapackages summary line.

        Returns:
            bool: True if any line contains 'unhealthy', False otherwise.
        """
        return any("unhealthy" in line for line in self._raw_output)

    def get_raw_output(self) -> List[str]:
        """
        Get the raw output lines.

        Returns:
            List[str]: Raw command output.
        """
        return self._raw_output

    def __str__(self) -> str:
        """
        Return a human-readable string representation of the precheck.

        Returns:
            str: Formatted precheck entries as strings.
        """
        return "\n".join([str(item) for item in self._items])

    def __repr__(self) -> str:
        """
        Return the developer-facing representation of the object.

        Returns:
            str: Class name and row count.
        """
        return f"{self.__class__.__name__}(items={len(self._items)})"
