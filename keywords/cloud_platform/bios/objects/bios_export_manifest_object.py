from keywords.cloud_platform.bios.objects.bios_export_host_summary_object import BiosExportHostSummaryObject


class BiosExportManifestObject:
    """Index of the hosts captured by one BIOS settings export."""

    STATUS_COMPLETED = "completed"
    STATUS_PARTIAL = "partial"

    def __init__(self):
        """Constructor."""
        self.host_summaries: dict[str, BiosExportHostSummaryObject] = {}

    def add_host_summary(self, host_summary: BiosExportHostSummaryObject) -> None:
        """Add the result of one host.

        Args:
            host_summary (BiosExportHostSummaryObject): Collection result of the host.
        """
        self.host_summaries[host_summary.get_hostname()] = host_summary

    def get_host_summary(self, hostname: str) -> BiosExportHostSummaryObject:
        """Get the result of one host.

        Args:
            hostname (str): Lab configuration node name.

        Returns:
            BiosExportHostSummaryObject: Collection result of the host.

        Raises:
            KeyError: If the host was not exported.
        """
        return self.host_summaries[hostname]

    def get_status(self) -> str:
        """Get the overall export status.

        Returns:
            str: ``completed`` when every host was exported, otherwise ``partial``.
        """
        if all(summary.get_status() == BiosExportHostSummaryObject.HOST_STATUS_EXPORTED for summary in self.host_summaries.values()):
            return self.STATUS_COMPLETED
        return self.STATUS_PARTIAL

    def to_dictionary(self) -> dict:
        """Describe this manifest as the JSON artifact content.

        Returns:
            dict: Overall status and the status and summary file of each host.
        """
        hosts = {hostname: {"status": summary.get_status(), "summary": summary.get_summary_file_path()} for hostname, summary in self.host_summaries.items()}
        return {"status": self.get_status(), "hosts": hosts}

    def __str__(self) -> str:
        """Describe the manifest.

        Returns:
            str: Overall status and number of hosts.
        """
        return f"BiosExportManifest({self.get_status()}, {len(self.host_summaries)} hosts)"
