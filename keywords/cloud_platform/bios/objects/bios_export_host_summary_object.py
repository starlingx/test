class BiosExportHostSummaryObject:
    """Collection status of every BIOS settings source of one host."""

    STATUS_COLLECTED = "collected"
    STATUS_UNSUPPORTED = "unsupported"
    STATUS_FAILED = "failed"
    HOST_STATUS_EXPORTED = "exported"
    HOST_STATUS_PARTIAL = "partial"

    def __init__(self, hostname: str):
        """Constructor.

        Args:
            hostname (str): Lab configuration node name.
        """
        self.hostname = hostname
        self.sources: dict[str, dict] = {}

    def get_hostname(self) -> str:
        """Get the host name.

        Returns:
            str: Lab configuration node name.
        """
        return self.hostname

    def get_summary_file_path(self) -> str:
        """Get the manifest-relative path of this host's summary file.

        Returns:
            str: Path of ``collection_summary.json`` relative to the export folder.
        """
        return f"{self.hostname}/collection_summary.json"

    def add_collected_source(self, key: str, file_path: str | None = None) -> None:
        """Record a source that was collected.

        Args:
            key (str): Source key, ``<category>/<name>``.
            file_path (str | None): Host-relative artifact path, if the value was saved.
        """
        self.sources[key] = {"status": self.STATUS_COLLECTED}
        if file_path:
            self.sources[key]["file"] = file_path

    def add_unsupported_source(self, key: str, reason: str) -> None:
        """Record a source this host cannot provide.

        Args:
            key (str): Source key, ``<category>/<name>``.
            reason (str): Why the source is not available.
        """
        self.sources[key] = {"status": self.STATUS_UNSUPPORTED, "reason": reason}

    def add_failed_source(self, key: str, error: Exception) -> None:
        """Record a source whose collection failed.

        Args:
            key (str): Source key, ``<category>/<name>``.
            error (Exception): The failure, kept so the cause can be diagnosed.
        """
        self.sources[key] = {"status": self.STATUS_FAILED, "error_type": type(error).__name__, "error": str(error)}

    def has_source(self, key: str) -> bool:
        """Check whether a source was recorded.

        Args:
            key (str): Source key, ``<category>/<name>``.

        Returns:
            bool: True if the source was recorded, otherwise False.
        """
        return key in self.sources

    def get_source_status(self, key: str) -> str:
        """Get the status of one source.

        Args:
            key (str): Source key, ``<category>/<name>``.

        Returns:
            str: ``collected``, ``unsupported`` or ``failed``.

        Raises:
            KeyError: If the source was not recorded.
        """
        return self.sources[key]["status"]

    def get_failed_source_keys(self) -> list[str]:
        """Get the sources whose collection failed.

        Returns:
            list[str]: Keys of the failed sources.
        """
        return [key for key, source in self.sources.items() if source["status"] == self.STATUS_FAILED]

    def get_status(self) -> str:
        """Get the overall host status.

        Returns:
            str: ``exported`` when no source failed, otherwise ``partial``.
        """
        return self.HOST_STATUS_PARTIAL if self.get_failed_source_keys() else self.HOST_STATUS_EXPORTED

    def to_dictionary(self) -> dict:
        """Describe this summary as the JSON artifact content.

        Returns:
            dict: Host name, status and per-source results.
        """
        return {"hostname": self.hostname, "status": self.get_status(), "sources": self.sources}

    def __str__(self) -> str:
        """Describe the summary without any collected payload.

        Returns:
            str: Host name and status.
        """
        return f"BiosExportHostSummary({self.hostname}, {self.get_status()})"
